# Makefile for full environment setup and building (Windows, Linux, macOS)

.PHONY: help venv setup-all setup-windows setup-linux setup-macos setup-python setup-whisper build-all build-linux build-windows build-macos run

help:
	@echo "make venv          # Create a Python 3.9 virtual environment using uv"
	@echo "make setup-all      # Install system and Python dependencies (auto-detects OS, uses venv)"
	@echo "make setup-windows  # Install Windows system dependencies (Chocolatey required)"
	@echo "make setup-linux    # Install Linux system dependencies (apt required)"
	@echo "make setup-macos    # Install macOS system dependencies (brew required)"
	@echo "make setup-python   # Install Python dependencies (in venv)"
	@echo "make setup-whisper  # Install Whisper backend from GitHub (in venv)"
	@echo "make build-all      # Build binaries for all supported OSes"
	@echo "make build-linux    # Build Linux binary with PyInstaller"
	@echo "make build-windows  # Build Windows binary with PyInstaller"
	@echo "make build-macos    # Build macOS binary with PyInstaller"
	@echo "make run            # Run the built binary for the current OS"
	@echo "\nTo activate the virtual environment, use:"
	@echo "  On Windows: .venv\\Scripts\\activate"
	@echo "  On Linux/macOS: source .venv/bin/activate"

venv:
	uv venv --python 3.9 .venv

setup-all: venv
ifeq ($(OS),Windows_NT)
	$(MAKE) setup-windows
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		$(MAKE) setup-linux
	else ifeq ($(UNAME_S),Darwin)
		$(MAKE) setup-macos
	else
		@echo "Unsupported OS: $(UNAME_S)" && exit 1
	endif
endif
	$(MAKE) setup-python
	$(MAKE) setup-whisper

setup-windows:
	@echo "Installing C++ Build Tools and ffmpeg with Chocolatey..."
	@if [ ! -f /c/ProgramData/chocolatey/bin/choco.exe ]; then \
		echo "Chocolatey not found. Installing Chocolatey..." ; \
		powershell.exe -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" ; \
	fi
	choco install -y visualcpp-build-tools
	choco install -y ffmpeg

setup-linux:
	@echo "Installing build-essential and ffmpeg with apt..."
	sudo apt-get update
	sudo apt-get install -y build-essential ffmpeg

setup-macos:
	@echo "Installing ffmpeg with Homebrew..."
	@if ! command -v brew > /dev/null; then \
		echo "Homebrew not found. Please install Homebrew first: https://brew.sh/" && exit 1; \
	fi
	brew install ffmpeg

setup-python: venv
ifeq ($(OS),Windows_NT)
	.venv\Scripts\uv pip install -r pyproject.toml
else
	.venv/bin/uv pip install -r pyproject.toml
endif

setup-whisper: venv
ifeq ($(OS),Windows_NT)
	.venv\Scripts\uv pip install --upgrade git+https://github.com/openai/whisper.git
else
	.venv/bin/uv pip install --upgrade git+https://github.com/openai/whisper.git
endif

# Build targets
build-all:
ifeq ($(OS),Windows_NT)
	$(MAKE) build-windows
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		$(MAKE) build-linux
	else ifeq ($(UNAME_S),Darwin)
		$(MAKE) build-macos
	else
		@echo "Unsupported OS: $(UNAME_S)" && exit 1
	endif
endif

build-linux:
	@echo "Building Linux binary (native) ..."
	pyinstaller --onefile --windowed install.py --name instyper \
		--collect-all vosk \
		--collect-all numpy \
		--collect-all pandas \
		--collect-all beautifulsoup4 \
		--collect-all pyautogui \
		--collect-all plyer \
		--collect-all pystray \
		--collect-all PIL \
		--collect-all pyttsx3 \
		--collect-all pyaudio \
		--collect-all pyperclip \
		--add-data "ml/vosk-model-small-en-us-0.15;ml/vosk-model-small-en-us-0.15" \
		--add-data "ml/vosk-model-small-tr-0.3;ml/vosk-model-small-tr-0.3" \
		--log-level=INFO
	@echo "Linux binary built: dist/instyper"

build-windows:
	@echo "Building Windows binary (cross) ..."
	pyinstaller --onefile --windowed install.py --name instyper.exe \
		--collect-all vosk \
		--collect-all numpy \
		--collect-all pandas \
		--collect-all beautifulsoup4 \
		--collect-all pyautogui \
		--collect-all plyer \
		--collect-all pystray \
		--collect-all PIL \
		--collect-all pyttsx3 \
		--collect-all pyaudio \
		--collect-all pyperclip \
		--add-data "ml/vosk-model-small-en-us-0.15;ml/vosk-model-small-en-us-0.15" \
		--add-data "ml/vosk-model-small-tr-0.3;ml/vosk-model-small-tr-0.3" \
		--log-level=INFO
	@echo "Windows binary built: dist/instyper.exe"

build-macos:
	@echo "Building macOS binary (native) ..."
	pyinstaller --onefile --windowed install.py --name instyper \
		--collect-all vosk \
		--collect-all numpy \
		--collect-all pandas \
		--collect-all beautifulsoup4 \
		--collect-all pyautogui \
		--collect-all plyer \
		--collect-all pystray \
		--collect-all PIL \
		--collect-all pyttsx3 \
		--collect-all pyaudio \
		--collect-all pyperclip \
		--add-data "ml/vosk-model-small-en-us-0.15;ml/vosk-model-small-en-us-0.15" \
		--add-data "ml/vosk-model-small-tr-0.3;ml/vosk-model-small-tr-0.3" \
		--log-level=INFO
	@echo "macOS binary built: dist/instyper"

run:
ifeq ($(OS),Windows_NT)
	@echo "Running Windows binary..."
	./dist/instyper.exe
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		@echo "Running Linux binary..."
		./dist/instyper
	else ifeq ($(UNAME_S),Darwin)
		@echo "Running macOS binary..."
		./dist/instyper
	else
		@echo "Unsupported OS: $(UNAME_S)" && exit 1
	endif
endif 