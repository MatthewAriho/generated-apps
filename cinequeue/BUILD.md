# CineQueue v3.0 — APK Build Guide

## Environment Setup (Ubuntu/Debian — do this once)

```bash
# 1. System dependencies
sudo apt update && sudo apt install -y \
    python3 python3-pip python3-venv \
    git zip unzip openjdk-17-jdk \
    libffi-dev libssl-dev \
    autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev \
    libncursesw5-dev libtinfo5 \
    cmake build-essential \
    libltdl-dev

# 2. Set JAVA_HOME (for JDK 17)
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# 3. Create and activate a virtualenv
python3 -m venv ~/kivy-env
source ~/kivy-env/bin/activate

# 4. Install buildozer and Cython
pip install --upgrade pip
pip install buildozer cython==0.29.37

# 5. Android SDK/NDK are downloaded automatically by buildozer on first build
#    Optionally pre-accept licenses if sdkmanager is already installed:
#    yes | sdkmanager --licenses
```

---

## Build Commands

```bash
# Navigate to project
cd /generated_apps/cinequeue

# Activate virtualenv (if not already active)
source ~/kivy-env/bin/activate

# Clean previous build artifacts (recommended before version bump)
buildozer android clean

# Build debug APK (outputs to bin/)
buildozer android debug
```

APK output:
```
bin/cinequeue-3.0-arm64-v8a-debug.apk
```

Or just run the build script:
```bash
bash build.sh
```

---

## Install to Device (adb)

```bash
# Enable USB debugging on device, then:
adb install bin/cinequeue-3.0-arm64-v8a-debug.apk

# Watch logcat while testing
adb logcat | grep -E "python|cinequeue"
```

---

## Key buildozer.spec Settings

| Setting           | Value          |
|-------------------|----------------|
| `version`         | `3.0`          |
| `requirements`    | `python3,kivy,kivymd` |
| `android.api`     | `34`           |
| `android.minapi`  | `26`           |
| `android.ndk`     | `25b`          |
| `android.archs`   | `arm64-v8a`    |

---

## Troubleshooting

- **Build fails on first run** — normal, buildozer downloads ~2 GB of Android SDK/NDK. Re-run after it finishes.
- **Cython version errors** — stick with `cython==0.29.37`, newer versions break python-for-android.
- **`kivymd` not found** — buildozer resolves it from PyPI automatically; no manual install needed.
- **Java version issues** — requires JDK 11 or 17; avoid JDK 21+.
