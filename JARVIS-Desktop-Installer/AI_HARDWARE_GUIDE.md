# 🧠 Průvodce: Jak nainstalovat a vybrat ideální lokální AI pro tvůj PC

Tento návod ti pomůže rozběhat lokální umělou inteligenci, která poběží **100% soukromě a offline přímo na tvém hardwaru**.

---

## 1. Krok: Instalace Ollama (AI Engine)

Jarvis ke svému běhu využívá **Ollama** – nejrychlejší a nejsnadnější způsob, jak provozovat lokální LLM modely na Linuxu i dalších systémech.

Otevři terminál a zadej:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```
Po instalaci Ollama automaticky běží jako systémová služba na pozadí.

---

## 2. Krok: Jaký model vybrat podle tvého hardwaru?

Vyber si model podle toho, kolik má tvůj počítač **operační paměti (RAM)** a jakou máš **grafickou kartu (VRAM)**:

| Tvůj Hardware (RAM / GPU) | Doporučený model | Příkaz pro stažení | Vlastnosti a rychlost |
| :--- | :--- | :--- | :--- |
| **Základní PC / Notebook**<br>(8 GB RAM, integrovaná grafika) | **Qwen 2.5 3B / Qwen 3 4B** | `ollama run qwen2.5:3b` | ⚡ Extrémně rychlý, nenáročný na RAM (~2.5 GB), perfektní pro starší stroje a notebooky. |
| **Běžné PC / Herní střední třída** *(Doporučeno)*<br>(16 GB RAM, GPU 6–8 GB VRAM – např. RTX 3060, RX 6600/6650 XT) | **Qwen 2.5 7B** nebo **Qwen 3 8B** | `ollama run qwen2.5:7b` | 🎯 Nejlepší poměr inteligence a rychlosti. Skvěle zvládá češtinu, programování i vtipný sarkasmus. |
| **Výkonné PC**<br>(16–32 GB RAM, GPU 8–12 GB VRAM) | **Gemma 4 12B** | `ollama run gemma4:12b-it-qat` | 🧠 Špičková Google inteligence, velmi hluboké odpovědi a vysoká přesnost. |
| **High-End PC / Pracovní stanice**<br>(32 GB+ RAM, GPU 12–16 GB+ VRAM – např. RTX 4070 Ti, 4080/4090) | **Llama 3.1 8B** nebo **Qwen 2.5 14B** | `ollama run qwen2.5:14b` | 🚀 Pokročilé logické uvažování a komplexní systémové analýzy. |

---

## 3. Krok: Stažení modelu jedním příkazem

Stačí v terminálu spustit příkaz pro tebou zvolený model. Například pro doporučený model **Qwen 2.5 7B**:
```bash
ollama run qwen2.5:7b
```
Model se automaticky stáhne. Můžeš si stáhnout i více modelů najednou – Jarvis je **automaticky detekuje a zobrazí v roletce v okně na ploše**, takže mezi nimi můžeš přepínat jedním klikem.

---

## 💡 Tip: Chceš ověřit, jaké modely máš stažené?
V terminálu zadej:
```bash
ollama list
```
Všechny stažené modely se ihned načtou do Jarvise!
