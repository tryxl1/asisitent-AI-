#!/usr/bin/env python3
"""
System Command Execution Tools for J.A.R.V.I.S.
Allows Jarvis to control audio, applications, system info, notifications, web search, downloads, and browser opening.
"""
import subprocess
import os
import re
import urllib.parse
import psutil

# Safe import of search
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

DOWNLOADS_DIR = os.path.expanduser("~/Stažené") if os.path.exists(os.path.expanduser("~/Stažené")) else os.path.expanduser("~/Downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def get_system_status():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return f"Využití CPU: {cpu}%, RAM: {mem}%, Disk: {disk}%."

def change_volume(action):
    try:
        if action == "up":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"])
            return "Hlasitost zvýšena o 5%."
        elif action == "down":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])
            return "Hlasitost snížena o 5%."
        elif action == "mute":
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
            return "Ztlumení zvuku přepnuto."
        else:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", action])
            return f"Hlasitost nastavena na {action}."
    except Exception as e:
        return f"Chyba při změně hlasitosti: {e}"

def open_url_in_browser(url):
    """Open URL in Brave/Firefox or default system browser"""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    try:
        # Try opening via xdg-open
        subprocess.Popen(["xdg-open", url])
        return f"Otevírám odkaz v prohlížeči: {url}"
    except Exception:
        try:
            # Fallback to Flatpak Brave
            subprocess.Popen(["flatpak", "run", "com.brave.Browser", url])
            return f"Otevírám v prohlížeči Brave: {url}"
        except Exception as e:
            return f"Nepodařilo se otevřít prohlížeč: {e}"

def open_application(app_name):
    app_lower = app_name.lower().strip()
    if app_lower.startswith("http://") or app_lower.startswith("https://") or "www." in app_lower:
        return open_url_in_browser(app_lower)

    try:
        if "brave" in app_lower or "prohlížeč" in app_lower or "web" in app_lower:
            subprocess.Popen(["flatpak", "run", "com.brave.Browser"])
            return "Spouštím prohlížeč Brave."
        elif "firefox" in app_lower:
            subprocess.Popen(["flatpak", "run", "org.mozilla.firefox"])
            return "Spouštím Firefox."
        elif "steam" in app_lower:
            subprocess.Popen(["steam"])
            return "Spouštím Steam."
        elif "heroic" in app_lower:
            subprocess.Popen(["flatpak", "run", "com.heroicgameslauncher.hgl"])
            return "Spouštím Heroic Games Launcher."
        elif "kalkulačk" in app_lower or "calc" in app_lower:
            subprocess.Popen(["kcalc"])
            return "Spouštím kalkulačku."
        elif "správce souborů" in app_lower or "dolphin" in app_lower or "soubory" in app_lower:
            subprocess.Popen(["dolphin"])
            return "Otevírám správce souborů Dolphin."
        elif "terminál" in app_lower or "konsole" in app_lower:
            subprocess.Popen(["konsole"])
            return "Otevírám terminál Konsole."
        else:
            subprocess.Popen(["xdg-open", app_name])
            return f"Otevírám {app_name}."
    except Exception as e:
        return f"Nepodařilo se spustit {app_name}: {e}"

def send_notification(title, message):
    try:
        subprocess.run(["notify-send", title, message])
        return "Notifikace odeslána."
    except Exception as e:
        return f"Chyba notifikace: {e}"

def search_web(query, open_browser=True):
    """Search web using DDGS and optionally open top result in browser"""
    query = query.strip()
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            # Fallback search query directly in browser
            search_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
            if open_browser:
                open_url_in_browser(search_url)
            return f"Vyhledávám v prohlížeči: {search_url}"
        
        top = results[0]
        title = top.get("title", "")
        url = top.get("href", "")
        snippet = top.get("body", "")

        # Always open the top URL directly in browser so user sees it in external window
        if open_browser and url:
            open_url_in_browser(url)

        return f"Nalezeno: {title}\nOdkaz: {url}\nShrnutí: {snippet}\n(Stránka byla otevřena v prohlížeči)"
    except Exception as e:
        # Fallback to direct web search in browser if API fails
        search_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
        open_url_in_browser(search_url)
        return f"Otevírám vyhledávání v prohlížeči pro '{query}'."

def inspect_and_download(url_or_query):
    target = url_or_query.strip()
    try:
        # If it's a search term rather than direct link
        if not target.startswith("http://") and not target.startswith("https://"):
            results = DDGS().text(f"download {target}", max_results=1)
            if results:
                target = results[0].get("href", "")
            else:
                return f"Nepodařilo se nalézt přímý odkaz pro: {target}"

        # If it's video/audio streaming URL
        if any(d in target for d in ["youtube.com", "youtu.be", "soundcloud.com", "vimeo.com"]):
            subprocess.Popen(["yt-dlp", "-P", DOWNLOADS_DIR, target])
            return f"Zahájeno stahování média\nZdroj: {target}\nUkládám do: {DOWNLOADS_DIR}"

        # Direct file download
        filename = os.path.basename(urllib.parse.urlparse(target).path) or "downloaded_file"
        dest_path = os.path.join(DOWNLOADS_DIR, filename)

        subprocess.Popen(["curl", "-sL", target, "-o", dest_path])
        return f"Stahuji soubor: {filename}\nOdkaz: {target}\nCíl: {dest_path}"
    except Exception as e:
        return f"Chyba při stahování: {e}"

def run_bash_cmd(cmd):
    forbidden = ["rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:"]
    for f in forbidden:
        if f in cmd:
            return "Tento příkaz byl z bezpečnostních důvodů zablokován."
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        output = res.stdout.strip() or res.stderr.strip()
        if len(output) > 500:
            output = output[:500] + "... [zkráceno]"
        return output or "Příkaz byl úspěšně proveden bez výstupu."
    except Exception as e:
        return f"Chyba při spuštění příkazu: {e}"

def execute_pc_action(action_type, param=""):
    action_type = action_type.lower()
    if action_type == "status":
        return get_system_status()
    elif action_type == "volume":
        return change_volume(param)
    elif action_type == "open":
        return open_application(param)
    elif action_type == "browse":
        return open_url_in_browser(param)
    elif action_type == "notify":
        return send_notification("J.A.R.V.I.S.", param)
    elif action_type == "search":
        return search_web(param, open_browser=True)
    elif action_type == "download":
        return inspect_and_download(param)
    elif action_type == "bash":
        return run_bash_cmd(param)
    return "Neznámá systémová akce."
