# Makefile for full environment setup and building (Windows, Linux, macOS)

.PHONY: help venv setup-all setup-windows setup-linux setup-macos setup-python setup-whisper build-all build-linux build-windows build-macos run clean-venv

# Force PowerShell as the shell for all commands on Windows
ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
endif

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
ifeq ($(OS),Windows_NT)
	if (!(Test-Path '.venv/Scripts/Activate')) { Write-Host 'Creating venv...'; uv venv --python 3.10 .venv; & .venv/Scripts/python.exe -m ensurepip --upgrade; & .venv/Scripts/python.exe -m pip install --upgrade pip; & .venv/Scripts/python.exe -m pip install uv; } else { Write-Host '.venv already exists, skipping creation.'; }
else
	@if [ ! -d .venv ]; then \
		echo "Creating venv..." ; \
		uv venv --python 3.10 .venv ; \
		.venv/bin/python -m ensurepip --upgrade ; \
		.venv/bin/python -m pip install --upgrade pip ; \
		.venv/bin/python -m pip install uv ; \
	else \
		echo ".venv already exists, skipping creation." ; \
	fi
endif

setup-all: clean-venv venv
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
	if (!(Test-Path 'C:/ProgramData/chocolatey/bin/choco.exe')) { Write-Host 'Chocolatey not found. Installing Chocolatey...'; try { iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')); } catch { Write-Error 'Chocolatey installation failed.'; exit 1; } } else { Write-Host 'Chocolatey already installed.'; }; if (-not (choco list --local-only | Select-String 'visualcpp-build-tools')) { Write-Host 'Installing C++ Build Tools...'; choco install -y visualcpp-build-tools; } else { Write-Host 'C++ Build Tools already installed.'; }; if (-not (choco list --local-only | Select-String 'ffmpeg')) { Write-Host 'Installing ffmpeg...'; choco install -y ffmpeg; } else { Write-Host 'ffmpeg already installed.'; }

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
	uv pip install --prerelease=allow -r pyproject.toml
ifeq ($(OS),Windows_NT)
	if (Test-Path '.venv/Scripts/tensorflow_io_gcs_filesystem-*.dist-info') { .venv/Scripts/pip.exe uninstall -y tensorflow-io-gcs-filesystem }
endif

setup-whisper: venv
	uv pip install --prerelease=allow --upgrade git+https://github.com/openai/whisper.git
ifeq ($(OS),Windows_NT)
	if (Test-Path '.venv/Scripts/tensorflow_io_gcs_filesystem-*.dist-info') { .venv/Scripts/pip.exe uninstall -y tensorflow-io-gcs-filesystem }
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

# Clean up venv: deactivate (if active) and remove .venv directory
clean-venv:
ifeq ($(OS),Windows_NT)
	if (Test-Path '.venv') { Write-Host 'Removing .venv...'; Remove-Item -Recurse -Force .venv }
else
	@if [ -d .venv ]; then \
		echo "Removing .venv..." ; \
		rm -rf .venv ; \
	fi
endif 