#!/usr/bin/env bash
# CineQueue APK build script
# Usage: bash build.sh [clean]
#   clean — wipe previous build artifacts before building

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$HOME/kivy-env"

# ── Activate virtualenv ───────────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    echo "[setup] Creating virtualenv at $VENV"
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    echo "[setup] Installing buildozer + cython"
    pip install --upgrade pip
    pip install buildozer cython==0.29.37
else
    source "$VENV/bin/activate"
fi

# ── Java (JDK 17) ────────────────────────────────────────────────────────────
if [ -d "/usr/lib/jvm/java-17-openjdk-amd64" ]; then
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    export PATH=$JAVA_HOME/bin:$PATH
fi

echo "[info] Python: $(python3 --version)"
echo "[info] Buildozer: $(buildozer version 2>&1 | head -1)"
echo "[info] Java: $(java -version 2>&1 | head -1)"

# ── Clean (optional) ─────────────────────────────────────────────────────────
if [[ "$1" == "clean" ]]; then
    echo "[clean] Wiping previous build..."
    buildozer android clean
fi

# ── Build ─────────────────────────────────────────────────────────────────────
echo "[build] Starting buildozer android debug..."
buildozer android debug

# ── Result ───────────────────────────────────────────────────────────────────
APK=$(ls bin/*.apk 2>/dev/null | tail -1)
if [ -n "$APK" ]; then
    echo ""
    echo "[done] APK ready: $APK"
    echo "[tip]  Install with: adb install $APK"
else
    echo "[error] No APK found in bin/ — check build output above"
    exit 1
fi
