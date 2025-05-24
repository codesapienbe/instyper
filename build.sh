#!/usr/bin/env bash
set -e

# Detect OS
OS="$(uname -s)"

# Helper to print status
function status() {
  echo -e "\033[1;34m[build.sh]\033[0m $1"
}

status "Detected OS: $OS"

# Build for Linux (native)
build_linux() {
  status "Building Linux binary (native) ..."
  pyinstaller --onefile --windowed install.py --name instyper \
    --collect-all vosk \
    --collect-all numpy \
    --collect-all pandas \
    --collect-all beautifulsoup4 \
    --add-data "ml/vosk-model-small-en-us-0.15;ml/vosk-model-small-en-us-0.15" \
    --add-data "ml/vosk-model-small-tr-0.3;ml/vosk-model-small-tr-0.3" \
    --log-level=INFO
  status "Linux binary built: dist/instyper"
}

# Build for Windows (cross)
build_windows() {
  status "Building Windows binary (cross) ..."
  pyinstaller --onefile --windowed install.py --name instyper.exe \
    --collect-all vosk \
    --collect-all numpy \
    --collect-all pandas \
    --collect-all beautifulsoup4 \
    --add-data "ml/vosk-model-small-en-us-0.15;ml/vosk-model-small-en-us-0.15" \
    --add-data "ml/vosk-model-small-tr-0.3;ml/vosk-model-small-tr-0.3" \
    --log-level=INFO
  status "Windows binary built: dist/instyper.exe"
}

# Build for macOS (native)
build_macos() {
  status "Building macOS binary (native) ..."
  pyinstaller --onefile --windowed install.py --name instyper \
    --collect-all vosk \
    --collect-all numpy \
    --collect-all pandas \
    --collect-all beautifulsoup4 \
    --add-data "ml/vosk-model-small-en-us-0.15;ml/vosk-model-small-en-us-0.15" \
    --add-data "ml/vosk-model-small-tr-0.3;ml/vosk-model-small-tr-0.3" \
    --log-level=INFO
  status "macOS binary built: dist/instyper"
}

if [[ "$OS" == "Darwin" ]]; then
  build_macos
  build_linux
  build_windows
elif [[ "$OS" == "Linux" ]]; then
  build_linux
  build_windows
elif [[ "$OS" =~ MINGW|MSYS|CYGWIN|NT* ]]; then
  build_windows
  build_linux
else
  status "Unsupported OS: $OS"
  exit 1
fi

status "All requested builds complete. Check the dist/ directory for outputs." 