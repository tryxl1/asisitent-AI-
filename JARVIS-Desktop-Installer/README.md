# J.A.R.V.I.S. Desktop Core

Inteligentní sci-fi asistent pro Linux s průhledným holografickým rozhraním na plochu, podporou 3D avatarů, ovládáním počítače a lokálním modelem Ollama.

## 🌟 Funkce
- **3D / Holografický avatar:** Arc Reactor nebo 3D modely postav (.glb / .gltf) - např. Gordon Freeman z Half-Life.
- **Hlasový i textový vstup:** Mluvte do mikrofonu nebo pište text.
- **Přirozený český hlas (TTS):** Plynulý ženský hlas Vlasta bez sekání (PipeWire).
- **Ovládání PC:** Hlasitost, spouštění aplikací (Brave, Steam, Dolphin...), kontrola využití CPU a RAM.
- **Práce s internetem:** Hledání na webu, otevírání výsledků v prohlížeči, stahování médií a souborů.
- **Lokální AI:** Přepínání mezi staženými modely v Ollamě (Gemma, Qwen...).

---

## 🚀 Instalace na novém PC

1. **Předpoklady:**
   - Linux s Pythonem 3 (testováno na Fedora / Bazzite / Ubuntu / Arch)
   - Spuštěná Ollama (`ollama serve`)

2. **Spuštění instalace jedním příkazem:**
   Otevřete terminál v této složce a spusťte:
   ```bash
   ./install.sh
   ```
   Instalátor automaticky vytvoří virtuální prostředí, nainstaluje všechny knihovny a přidá spouštěč do systémového menu aplikací.

3. **Spuštění:**
   - Ze systémového menu aplikací: **J.A.R.V.I.S. Desktop**
   - Nebo ručně: `./run.sh`
