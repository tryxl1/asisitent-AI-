#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "============================================="
echo "   Instalátor J.A.R.V.I.S. Desktop Core      "
echo "============================================="
echo ""

# Kontrola Python3
if ! command -v python3 &>/dev/null; then
    echo "❌ Chyba: python3 není nainstalován. Nainstalujte prosím Python 3."
    exit 1
fi

# 1. Detekce a instalace Ollamy
if ! command -v ollama &>/dev/null; then
    echo "⚠️  Ollama (lokální AI engine) nebyla nalezena."
    read -p "Chcete nyní automaticky nainstalovat Ollamu? (A/n): " install_ollama
    if [[ "$install_ollama" =~ ^[AaYy]$ ]] || [[ -z "$install_ollama" ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Pokračuji bez instalace Ollamy. Modely můžete nainstalovat později."
    fi
fi

# 2. Hardwarová detekce a doporučení AI modelu
echo ""
echo "🔍 Analyzuji váš hardware..."
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_GB=$(( TOTAL_RAM_KB / 1024 / 1024 ))

echo "💻 Celková RAM: ${TOTAL_RAM_GB} GB"

SUGGESTED_MODEL="qwen2.5:3b"
if [ "$TOTAL_RAM_GB" -ge 24 ]; then
    SUGGESTED_MODEL="gemma4:12b-it-qat"
elif [ "$TOTAL_RAM_GB" -ge 12 ]; then
    SUGGESTED_MODEL="qwen2.5:7b"
fi

echo "🎯 Doporučený AI model pro váš hardware: [ $SUGGESTED_MODEL ]"
echo ""

if command -v ollama &>/dev/null; then
    # Zkontrolujeme, zda už uživatel nějaký model nemá
    EXISTING_MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' || true)
    if [ -n "$EXISTING_MODELS" ]; then
        echo "✅ Nalezeny již stažené modely v Ollamě:"
        echo "$EXISTING_MODELS"
    else
        echo "Nemáte zatím stažený žádný lokální AI model."
        read -p "Chcete nyní stáhnout doporučený model ($SUGGESTED_MODEL)? (A/n): " download_ai
        if [[ "$download_ai" =~ ^[AaYy]$ ]] || [[ -z "$download_ai" ]]; then
            echo "⬇️  Stahuji model $SUGGESTED_MODEL (může chvíli trvat)..."
            ollama pull "$SUGGESTED_MODEL"
        fi
    fi
fi

echo ""
echo "📦 Vytvářím virtuální prostředí Pythonu (venv)..."
python3 -m venv venv

echo "⬇️  Instaluji potřebné knihovny..."
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet

# Vytvoření desktopového zástupce
DESKTOP_ENTRY_DIR="${HOME}/.local/share/applications"
mkdir -p "$DESKTOP_ENTRY_DIR"

cat <<EOF > "${DESKTOP_ENTRY_DIR}/jarvis-hud.desktop"
[Desktop Entry]
Name=J.A.R.V.I.S. Desktop
Comment=Desktop AI Hologram HUD Assistant with Ollama & Voice
Exec=${DIR}/run.sh
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Utility;AI;
StartupNotify=false
EOF

chmod +x "${DESKTOP_ENTRY_DIR}/jarvis-hud.desktop"
chmod +x "${DIR}/run.sh"
chmod +x "${DIR}/jarvis.py"

echo ""
echo "============================================="
echo "✅ Instalace byla úspěšně dokončena!"
echo "🚀 Nyní můžete Jarvise spustit buď ze systémového menu (J.A.R.V.I.S. Desktop),"
echo "   nebo spuštěním skriptu: ./run.sh"
echo "📄 Podrobný průvodce modely najdete v souboru: AI_HARDWARE_GUIDE.md"
echo "============================================="
echo ""
read -p "Chcete nyní Jarvise spustit? (A/n): " odpoved
if [[ "$odpoved" =~ ^[AaYy]$ ]] || [[ -z "$odpoved" ]]; then
    "${DIR}/run.sh" &
fi
