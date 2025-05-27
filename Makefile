# Simplified Makefile: clean, install, deploy only
.PHONY: clean install deploy

ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
endif

clean:
ifeq ($(OS),Windows_NT)
	if (Test-Path '.venv') { Remove-Item -Recurse -Force .venv }
	if (Test-Path 'dist') { Remove-Item -Recurse -Force dist }
else
	@if [ -d .venv ]; then rm -rf .venv; fi
	@if [ -d dist ]; then rm -rf dist; fi
endif

install: clean
ifeq ($(OS),Windows_NT)
	if (!(Test-Path '.venv/Scripts/Activate')) { uv venv --python 3.10 .venv; & .venv/Scripts/python.exe -m ensurepip --upgrade; & .venv/Scripts/python.exe -m pip install --upgrade pip; & .venv/Scripts/python.exe -m pip install uv; }
	if (!(Test-Path 'C:/ProgramData/chocolatey/bin/choco.exe')) { try { iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')); } catch { exit 1; } }
	if (-not (choco list --local-only | Select-String 'visualcpp-build-tools')) { choco install -y visualcpp-build-tools; }
	if (-not (choco list --local-only | Select-String 'ffmpeg')) { choco install -y ffmpeg; }
	uv pip install --prerelease=allow -r pyproject.toml
	uv pip install --prerelease=allow --upgrade git+https://github.com/openai/whisper.git
	if (Test-Path '.venv/Scripts/tensorflow_io_gcs_filesystem-*.dist-info') { .venv/Scripts/pip.exe uninstall -y tensorflow-io-gcs-filesystem }
else
	@if [ ! -d .venv ]; then uv venv --python 3.10 .venv; fi
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		sudo apt-get update
		sudo apt-get install -y build-essential ffmpeg
	else ifeq ($(UNAME_S),Darwin)
		@if ! command -v brew > /dev/null; then echo "Homebrew not found. Please install Homebrew first: https://brew.sh/" && exit 1; fi
		brew install ffmpeg
	else
		@echo "Unsupported OS: $(UNAME_S)" && exit 1
	endif
	uv pip install --prerelease=allow -r pyproject.toml
	uv pip install --prerelease=allow --upgrade git+https://github.com/openai/whisper.git
endif

deploy:
ifeq ($(OS),Windows_NT)
	pyinstaller --onefile --windowed install.py --name instyper.exe \
		--collect-all plyer \
		--collect-all pyaudio \
		--collect-all pyautogui \
		--collect-all pynput \
		--collect-all speechrecognition \
		--collect-all pystray \
		--collect-all PIL \
		--collect-all pyttsx3 \
		--collect-all vosk \
		--collect-all pyperclip \
		--collect-all pywin32 \
		--collect-all requests \
		--collect-all beautifulsoup4 \
		--collect-all numpy \
		--log-level=INFO
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		pyinstaller --onefile --windowed install.py --name instyper \
			--collect-all plyer \
			--collect-all pyaudio \
			--collect-all pyautogui \
			--collect-all pynput \
			--collect-all speechrecognition \
			--collect-all pystray \
			--collect-all PIL \
			--collect-all pyttsx3 \
			--collect-all vosk \
			--collect-all pyperclip \
			--collect-all requests \
			--collect-all beautifulsoup4 \
			--collect-all numpy \
			--log-level=INFO
	else ifeq ($(UNAME_S),Darwin)
		pyinstaller --onefile --windowed install.py --name instyper \
			--collect-all plyer \
			--collect-all pyaudio \
			--collect-all pyautogui \
			--collect-all pynput \
			--collect-all speechrecognition \
			--collect-all pystray \
			--collect-all PIL \
			--collect-all pyttsx3 \
			--collect-all vosk \
			--collect-all pyperclip \
			--collect-all requests \
			--collect-all beautifulsoup4 \
			--collect-all numpy \
			--log-level=INFO
	else
		@echo "Unsupported OS: $(UNAME_S)" && exit 1
	endif
endif 