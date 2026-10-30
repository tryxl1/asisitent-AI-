#!/usr/bin/env python3
import sys
import os
import json
import asyncio
import threading
import tempfile
import subprocess
import requests
import sounddevice as sd
import numpy as np
import websockets
import edge_tts
import speech_recognition as sr
from PyQt6.QtCore import Qt, QUrl, QPoint
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView

CONFIG_FILE = os.path.expanduser("~/.config/jarvis-hud.json")
OLLAMA_API = "http://localhost:11434"

DEFAULT_CONFIG = {
    "model": "gemma4:12b-it-qat",
    "voice": "cs-CZ-VlastaNeural", # Natural smooth female Czech voice
    "context": "Jsi J.A.R.V.I.S., vysoce inteligentní osobní asistent. Odpovídej vždy v češtině, stručně, věcně, přirozeně a srozumitelně. Vyhýbej se zbytečně dlouhým odstavcům.",
    "temperature": 0.7
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

class JarvisBackend:
    def __init__(self):
        self.config = load_config()
        self.active_connections = set()
        self.is_listening = False
        self.is_speaking = False
        self.recognizer = sr.Recognizer()
        self.current_proc = None
        self.loop = None

    async def broadcast(self, data):
        if not self.active_connections:
            return
        msg = json.dumps(data)
        to_remove = set()
        for conn in list(self.active_connections):
            try:
                await conn.send(msg)
            except Exception:
                to_remove.add(conn)
        self.active_connections -= to_remove

    def get_available_models(self):
        try:
            r = requests.get(f"{OLLAMA_API}/api/tags", timeout=3)
            if r.status_code == 200:
                data = r.json()
                models = [m["name"] for m in data.get("models", [])]
                if self.config["model"] not in models and models:
                    self.config["model"] = models[0]
                return models
        except Exception as e:
            print(f"[Ollama Error] {e}")
        return [self.config["model"]]

    async def speak_text(self, text):
        self.is_speaking = True
        await self.broadcast({"type": "state_change", "state": "speaking", "message": "MLUVÍM..."})

        # Clean markdown characters for voice
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace(">", "").strip()
        if len(clean_text) > 450:
            clean_text = clean_text[:450] + "..."

        temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        try:
            # Generate female voice via edge_tts
            voice = self.config.get("voice", "cs-CZ-VlastaNeural")
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(temp_mp3)

            # Convert to uncompressed WAV for ultra-smooth playback without pipe buffering
            subprocess.run(
                ["ffmpeg", "-y", "-i", temp_mp3, "-ar", "24000", "-ac", "1", temp_wav],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            if os.path.exists(temp_wav):
                # Start PipeWire native playback asynchronously
                proc = subprocess.Popen(["pw-play", temp_wav])
                self.current_proc = proc

                # Fake visualizer pulsation while audio plays
                pulsing_steps = 0
                while proc.poll() is None and self.is_speaking:
                    pulsing_steps += 1
                    # Dynamic wave
                    energy = 0.4 + 0.4 * (0.5 + 0.5 * np.sin(pulsing_steps * 0.4))
                    await self.broadcast({"type": "audio_energy", "energy": energy})
                    await asyncio.sleep(0.08)

                if proc.poll() is None:
                    proc.terminate()

        except Exception as e:
            print(f"[TTS Error] {e}")
        finally:
            if os.path.exists(temp_mp3): os.remove(temp_mp3)
            if os.path.exists(temp_wav): os.remove(temp_wav)
            self.is_speaking = False
            self.current_proc = None
            await self.broadcast({"type": "state_change", "state": "idle", "message": "PŘIPRAVEN K PŘÍKAZU"})

    async def query_ollama(self, prompt, model=None, use_voice=True):
        import re
        from system_tools import execute_pc_action

        model_name = model or self.config["model"]
        await self.broadcast({"type": "state_change", "state": "processing", "message": "PŘEMÝŠLÍM..."})

        system_instruction = self.config.get(
            "context",
            "Jsi J.A.R.V.I.S., osobní asistent."
        ) + (
            "\n\nMáš přímé pravomoci ovládat uživatelův Linux PC i internet přes systémové příkazy. "
            "Když uživatel požádá o systémovou akci, vyhledávání nebo stažení, VŽDY v odpovědi použij příslušný tag:\n"
            "- [[TOOL:search:konkrétní hledaný text]] - nahraď 'konkrétní hledaný text' přesným tématem, které uživatel chce najít na internetu (např. [[TOOL:search:grafické karty AMD novinky]]). Otevře se v prohlížeči.\n"
            "- [[TOOL:download:konkrétní název nebo URL]] - pro stažení souboru či média.\n"
            "- [[TOOL:volume:up]] / [[TOOL:volume:down]] / [[TOOL:volume:X%]] / [[TOOL:volume:mute]] pro hlasitost\n"
            "- [[TOOL:open:brave]] / [[TOOL:open:firefox]] / [[TOOL:open:steam]] / [[TOOL:open:dolphin]] / [[TOOL:open:konsole]] pro spuštění aplikací\n"
            "- [[TOOL:status]] pro vytížení procesoru a RAM\n"
            "- [[TOOL:notify:text notifikace]] pro zobrazení notifikace na ploše\n"
            "DŮLEŽITÉ: Do tagu za dvojtečku VŽDY vlož reálné parametry (např. skutečný název toho, co hledáš, nikdy nepoužívej slovo 'dotaz' doslova). "
            "Zachovej svůj typický lehce sarkastický a pohotový tón a okomentuj to pro uživatele."
        )

        full_response = ""
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "options": {
                    "temperature": float(self.config.get("temperature", 0.7))
                },
                "stream": True
            }
            res = requests.post(f"{OLLAMA_API}/api/chat", json=payload, stream=True, timeout=60)
            is_first = True
            for line in res.iter_lines():
                if line:
                    chunk_json = json.loads(line.decode('utf-8'))
                    chunk_text = chunk_json.get("message", {}).get("content", "")
                    full_response += chunk_text
                    await self.broadcast({
                        "type": "chunk",
                        "text": chunk_text,
                        "isFirst": is_first
                    })
                    is_first = False

            # Check if any TOOL tag was invoked in the response
            tool_matches = re.findall(r"\[\[TOOL:([^:]+?)(?::(.*?))?\]\]", full_response)
            clean_display_text = full_response
            for tool_action, tool_param in tool_matches:
                # If model mistakenly passed literal placeholder 'dotaz' or empty query, use the actual user prompt
                if tool_action == "search" and (not tool_param or tool_param.strip().lower() in ["dotaz", "hledaný text"]):
                    # Clean user prompt from "vyhledej", "najdi"
                    p_clean = re.sub(r"^(vyhledej|najdi|zjisti|vyhledej mi|najdi mi)\s*", "", prompt, flags=re.I).strip()
                    tool_param = p_clean or prompt

                print(f"[PC Control Tool]: {tool_action} -> {tool_param}")
                tool_result = execute_pc_action(tool_action, tool_param)
                # Remove tag from speech/display and append execution feedback
                tag_str = f"[[TOOL:{tool_action}:{tool_param}]]" if tool_param else f"[[TOOL:{tool_action}]]"
                clean_display_text = clean_display_text.replace(tag_str, f"\n⚡ [Systém: {tool_result}]")


            if tool_matches:
                await self.broadcast({
                    "type": "chunk",
                    "text": clean_display_text,
                    "isFirst": True
                })

            if use_voice and clean_display_text:
                # Remove system status log brackets for speech
                speech_clean = re.sub(r"\[\[.*?\]\]", "", clean_display_text)
                speech_clean = re.sub(r"⚡ \[.*?\]", "", speech_clean)
                await self.speak_text(speech_clean)
            else:
                await self.broadcast({"type": "state_change", "state": "idle", "message": "PŘIPRAVEN K PŘÍKAZU"})

        except Exception as e:
            err_msg = f"Chyba Ollama: {e}"
            await self.broadcast({"type": "chunk", "text": err_msg, "isFirst": True})
            await self.broadcast({"type": "state_change", "state": "idle", "message": "CHYBA"})


    def listen_microphone_worker(self, model, voice):
        try:
            samplerate = 16000
            max_seconds = 8
            threshold = 550

            asyncio.run_coroutine_threadsafe(
                self.broadcast({"type": "state_change", "state": "listening", "message": "MLUVTE..."}),
                self.loop
            )

            print("[Mic] Recording started...")
            audio_frames = []
            silent_chunks = 0
            has_spoken = False

            chunk_duration = 0.2
            chunk_samples = int(samplerate * chunk_duration)

            with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
                for _ in range(int(max_seconds / chunk_duration)):
                    if not self.is_listening:
                        break
                    data, _ = stream.read(chunk_samples)
                    audio_frames.append(data.copy())
                    peak = np.max(np.abs(data))
                    energy = min(1.0, float(peak) / 10000.0)
                    asyncio.run_coroutine_threadsafe(
                        self.broadcast({"type": "audio_energy", "energy": max(0.2, energy)}),
                        self.loop
                    )

                    if peak > threshold:
                        has_spoken = True
                        silent_chunks = 0
                    else:
                        if has_spoken:
                            silent_chunks += 1
                            if silent_chunks > 6: # ~1.2s silence
                                break

            if not audio_frames or not has_spoken:
                asyncio.run_coroutine_threadsafe(
                    self.broadcast({"type": "state_change", "state": "idle", "message": "NESLYŠEL JSEM NIC"}),
                    self.loop
                )
                self.is_listening = False
                return

            full_audio = np.concatenate(audio_frames, axis=0)
            audio_bytes = full_audio.tobytes()

            asyncio.run_coroutine_threadsafe(
                self.broadcast({"type": "state_change", "state": "processing", "message": "PŘEPISUJI HLAS..."}),
                self.loop
            )

            audio_data = sr.AudioData(audio_bytes, samplerate, 2)
            try:
                text = self.recognizer.recognize_google(audio_data, language="cs-CZ")
                print(f"[User Voice Recognized]: {text}")
                asyncio.run_coroutine_threadsafe(
                    self.broadcast({"type": "chunk", "text": f"Vy: {text}\n\nJarvis: ", "isFirst": True}),
                    self.loop
                )
                asyncio.run_coroutine_threadsafe(
                    self.query_ollama(text, model=model, use_voice=voice),
                    self.loop
                )
            except sr.UnknownValueError:
                asyncio.run_coroutine_threadsafe(
                    self.broadcast({"type": "state_change", "state": "idle", "message": "NEREROZUMĚL JSEM"}),
                    self.loop
                )
            except Exception as e:
                print(f"[STT Error]: {e}")
                asyncio.run_coroutine_threadsafe(
                    self.broadcast({"type": "state_change", "state": "idle", "message": "CHYBA PŘEPISU"}),
                    self.loop
                )
        except Exception as e:
            print(f"[Mic Worker Error]: {e}")
            asyncio.run_coroutine_threadsafe(
                self.broadcast({"type": "state_change", "state": "idle", "message": "CHYBA MIKROFONU"}),
                self.loop
            )
        finally:
            self.is_listening = False

    async def handle_client(self, websocket):
        self.active_connections.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                action = data.get("action")

                if action == "get_config":
                    models = self.get_available_models()
                    await websocket.send(json.dumps({
                        "type": "config_data",
                        "models": models,
                        "current_model": self.config["model"],
                        "avatar": self.config.get("avatar", "reactor"),
                        "voice": self.config.get("voice", "cs-CZ-VlastaNeural"),
                        "context": self.config.get("context", ""),
                        "temperature": self.config.get("temperature", 0.7)
                    }))

                elif action == "get_avatars":
                    avatars_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")
                    files = []
                    if os.path.exists(avatars_dir):
                        files = [f for f in os.listdir(avatars_dir) if f.lower().endswith(('.glb', '.gltf'))]
                    await websocket.send(json.dumps({
                        "type": "avatars_list",
                        "avatars": files,
                        "current": self.config.get("avatar", "reactor")
                    }))

                elif action == "open_avatar_folder":
                    avatars_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")
                    subprocess.Popen(["xdg-open", avatars_dir])

                elif action == "open_market":
                    url = data.get("url", "")
                    if url:
                        subprocess.Popen(["xdg-open", url])

                elif action == "save_config":
                    if "avatar" in data: self.config["avatar"] = data["avatar"]
                    if "voice" in data: self.config["voice"] = data["voice"]
                    if "context" in data: self.config["context"] = data["context"]
                    if "temperature" in data: self.config["temperature"] = data["temperature"]
                    save_config(self.config)
                    print(f"[Config Saved] Avatar: {self.config.get('avatar')}, Voice: {self.config.get('voice')}")


                elif action == "set_model":
                    self.config["model"] = data.get("model", self.config["model"])
                    save_config(self.config)
                    # Abort any ongoing speech, listening or playback
                    self.is_speaking = False
                    self.is_listening = False
                    if self.current_proc:
                        try:
                            self.current_proc.kill()
                        except Exception:
                            pass
                        self.current_proc = None
                    await self.broadcast({"type": "state_change", "state": "idle", "message": "MODEL PŘEPNUT"})
                    print(f"Switched model to: {self.config['model']} and reset state")

                elif action == "query":
                    text = data.get("text", "")
                    model = data.get("model", self.config["model"])
                    voice = data.get("voice", True)
                    asyncio.create_task(self.query_ollama(text, model, voice))

                elif action == "start_listen":
                    if not self.is_listening:
                        self.is_listening = True
                        model = data.get("model", self.config["model"])
                        voice = data.get("voice", True)
                        threading.Thread(target=self.listen_microphone_worker, args=(model, voice), daemon=True).start()

                elif action == "stop_listen":
                    self.is_listening = False
                    if self.current_proc:
                        try: self.current_proc.kill()
                        except: pass
                        self.current_proc = None
                    self.is_speaking = False
                    await self.broadcast({"type": "state_change", "state": "idle", "message": "PŘIPRAVEN K PŘÍKAZU"})

                elif action == "stop_all":
                    print("[Jarvis] Stop requested by user.")
                    self.is_listening = False
                    self.is_speaking = False
                    if self.current_proc:
                        try: self.current_proc.kill()
                        except: pass
                        self.current_proc = None
                    await self.broadcast({"type": "state_change", "state": "idle", "message": "ZASTAVENO"})

                elif action == "toggle_maximize":

                    if window_instance:
                        if window_instance.isMaximized():
                            window_instance.showNormal()
                        else:
                            window_instance.showMaximized()

                elif action == "quit_app":
                    print("[Jarvis] Instant quit requested.")
                    if self.current_proc:
                        try: self.current_proc.kill()
                        except: pass
                    os._exit(0)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.active_connections.discard(websocket)

backend = JarvisBackend()
window_instance = None

async def ws_main():
    backend.loop = asyncio.get_running_loop()
    async with websockets.serve(backend.handle_client, "127.0.0.1", 8765):
        await asyncio.Future()

def run_ws_server():
    asyncio.run(ws_main())

class JarvisWallpaperWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        global window_instance
        window_instance = self
        self.drag_position = QPoint()

        # Frameless but fully resizable window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Responsive default & minimum sizes
        self.setMinimumSize(380, 500)
        self.resize(520, 720)

        screen = QApplication.primaryScreen().geometry()
        # Initial position: bottom right, leaving taskbar clearance
        self.move(screen.width() - 560, max(20, screen.height() - 780))

        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.setCentralWidget(self.web_view)

        # Load via local http server to allow 3D model GLTF fetching
        self.web_view.setUrl(QUrl("http://127.0.0.1:8766/hud.html"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull() and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


def run_static_server():
    import http.server
    import socketserver
    base_dir = os.path.dirname(os.path.abspath(__file__))
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=base_dir, **kwargs)
        def log_message(self, format, *args):
            pass # Silent

    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("127.0.0.1", 8766), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print(f"[HTTP Server] {e}")

def main():
    # Start static file server
    http_thread = threading.Thread(target=run_static_server, daemon=True)
    http_thread.start()

    # Start WebSocket server thread
    ws_thread = threading.Thread(target=run_ws_server, daemon=True)
    ws_thread.start()


    app = QApplication(sys.argv)
    window = JarvisWallpaperWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
