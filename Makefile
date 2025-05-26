# Makefile for full environment setup and building (Windows, Linux, macOS)

.PHONY: help venv install setup-windows setup-linux setup-macos setup-python setup-whisper deploy build-linux build-windows build-macos run clean validate

# Detect OS and architecture
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    SHELL := powershell.exe
    .SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
    PYTHON := python
    VENV_ACTIVATE := .venv\Scripts\activate
    VENV_PYTHON := .venv\Scripts\python.exe
    VENV_PIP := .venv\Scripts\pip.exe
    PATH_SEP := ;
else
    DETECTED_OS := $(shell uname -s)
    ARCH := $(shell uname -m)
    ifeq ($(DETECTED_OS),Darwin)
        ifeq ($(ARCH),arm64)
            PYTHON := arch -arm64 /opt/homebrew/opt/python@3.10/bin/python3.10
        else
            PYTHON := python3
        endif
    else
        PYTHON := python3
    endif
    VENV_ACTIVATE := .venv/bin/activate
    VENV_PYTHON := .venv/bin/python
    VENV_PIP := .venv/bin/pip
    PATH_SEP := :
endif

# Python version requirements
PYTHON_MIN_VERSION := 3.10
PYTHON_MAX_VERSION := 3.10

help:
	@echo "Instyper Makefile Help"
	@echo "====================="
	@echo "Environment Setup:"
	@echo "  make validate            # Check system requirements"
	@echo "  make venv                # Create Python virtual environment"
	@echo "  make install            # Full setup (auto-detects OS)"
	@echo "  make setup-windows      # Windows-specific setup"
	@echo "  make setup-linux        # Linux-specific setup"
	@echo "  make setup-macos        # macOS-specific setup"
	@echo "  make setup-python       # Install Python dependencies"
	@echo "  make setup-whisper      # Install Whisper backend"
	@echo "\nBuild Targets:"
	@echo "  make deploy             # Build for current platform"
	@echo "  make build-linux        # Build Linux binary"
	@echo "  make build-windows      # Build Windows binary"
	@echo "  make build-macos        # Build macOS binary"
	@echo "\nOther:"
	@echo "  make run                # Run the built binary"
	@echo "  make clean              # Clean all build artifacts and virtual environment"
	@echo "\nTo activate the virtual environment:"
	@echo "  Windows: .venv\\Scripts\\activate"
	@echo "  Unix:    source .venv/bin/activate"

validate:
ifeq ($(DETECTED_OS),Windows)
	@echo "Checking Windows prerequisites..."
	@if (!(Test-Path 'C:/ProgramData/chocolatey/bin/choco.exe')) { \
		echo "Chocolatey not found. Please install it first: https://chocolatey.org/install"; \
		exit 1; \
	}
else ifeq ($(DETECTED_OS),Darwin)
	@echo "Checking macOS prerequisites..."
	@if ! command -v brew > /dev/null; then \
		echo "Homebrew not found. Please install it first: https://brew.sh/"; \
		exit 1; \
	fi
	@if [ "$(ARCH)" = "arm64" ]; then \
		echo "Detected Apple Silicon (arm64) architecture"; \
	fi
else ifeq ($(DETECTED_OS),Linux)
	@echo "Checking Linux prerequisites..."
	@if ! command -v apt-get > /dev/null; then \
		echo "apt-get not found. This script requires a Debian-based distribution."; \
		exit 1; \
	fi
endif
	@echo "Checking Python version..."
	@$(PYTHON) -c 'import sys; v=sys.version_info; ver=f"{v.major}.{v.minor}"; print(f"Found Python {ver}") if "$(PYTHON_MIN_VERSION)" <= ver <= "$(PYTHON_MAX_VERSION)" else (print(f"Error: Python {ver} not supported. Required: $(PYTHON_MIN_VERSION)-$(PYTHON_MAX_VERSION)"), sys.exit(1))'

venv: validate
ifeq ($(DETECTED_OS),Windows)
	if (!(Test-Path '.venv/Scripts/Activate')) { \
		echo "Creating venv..."; \
		$(PYTHON) -m venv .venv; \
		$(VENV_PYTHON) -m ensurepip --upgrade; \
		$(VENV_PYTHON) -m pip install --upgrade pip; \
		$(VENV_PYTHON) -m pip install uv; \
	} else { \
		echo ".venv already exists, skipping creation."; \
	}
else ifeq ($(DETECTED_OS),Darwin)
	@if [ ! -d .venv ]; then \
		echo "Creating venv..."; \
		arch -arm64 /opt/homebrew/opt/python@3.10/bin/python3.10 -m venv .venv; \
		$(VENV_PYTHON) -m ensurepip --upgrade; \
		$(VENV_PYTHON) -m pip install --upgrade pip; \
		$(VENV_PYTHON) -m pip install uv; \
	else \
		echo ".venv already exists, skipping creation."; \
	fi
else
	@if [ ! -d .venv ]; then \
		echo "Creating venv..."; \
		$(PYTHON) -m venv .venv; \
		$(VENV_PYTHON) -m ensurepip --upgrade; \
		$(VENV_PYTHON) -m pip install --upgrade pip; \
		$(VENV_PYTHON) -m pip install uv; \
	else \
		echo ".venv already exists, skipping creation."; \
	fi
endif

install: venv
ifeq ($(DETECTED_OS),Windows)
	$(MAKE) setup-windows
else ifeq ($(DETECTED_OS),Darwin)
	$(MAKE) setup-macos
else ifeq ($(DETECTED_OS),Linux)
	$(MAKE) setup-linux
else
	@echo "Unsupported OS: $(DETECTED_OS)" && exit 1
endif
	$(MAKE) setup-python
	$(MAKE) setup-whisper

setup-windows:
	@echo "Installing Windows dependencies..."
	choco install -y visualcpp-build-tools ffmpeg

setup-linux:
	@echo "Installing Linux dependencies..."
	sudo apt-get update
	sudo apt-get install -y build-essential ffmpeg portaudio19-dev python3-pyaudio

setup-macos:
	@echo "Installing macOS dependencies..."
	brew install ffmpeg portaudio python-tk@3.10
ifeq ($(ARCH),arm64)
	@echo "Installing Apple Silicon specific dependencies..."
	arch -arm64 brew install python@3.10
endif

setup-python: venv
	@echo "Installing Python dependencies..."
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e .
ifeq ($(DETECTED_OS),Windows)
	if (Test-Path '.venv/Scripts/tensorflow_io_gcs_filesystem-*.dist-info') { \
		$(VENV_PIP) uninstall -y tensorflow-io-gcs-filesystem \
	}
endif

setup-whisper: venv
	@echo "Installing Whisper backend..."
	$(VENV_PIP) install --upgrade git+https://github.com/openai/whisper.git
ifeq ($(DETECTED_OS),Windows)
	if (Test-Path '.venv/Scripts/tensorflow_io_gcs_filesystem-*.dist-info') { \
		$(VENV_PIP) uninstall -y tensorflow-io-gcs-filesystem \
	}
endif

# Build targets
deploy:
ifeq ($(DETECTED_OS),Windows)
	$(MAKE) build-windows
else ifeq ($(DETECTED_OS),Darwin)
	$(MAKE) build-macos
else ifeq ($(DETECTED_OS),Linux)
	$(MAKE) build-linux
else
	@echo "Unsupported OS: $(DETECTED_OS)" && exit 1
endif

build-linux:
	@echo "Building Linux binary..."
	pyinstaller --windowed src/instyper/__main__.py --name instyper \
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
		--collect-all speechbrain \
		--collect-all huggingface_hub \
		--collect-all stt \
		--hidden-import=speechbrain \
		--hidden-import=huggingface_hub \
		--hidden-import=stt \
		--hidden-import=bs4 \
		--hidden-import=soupsieve \
		--hidden-import=torch \
		--hidden-import=torch.nn \
		--hidden-import=torch.nn.functional \
		--exclude-module=pytest \
		--exclude-module=spacy \
		--exclude-module=paddle \
		--exclude-module=paddlespeech \
		--exclude-module=jnius \
		--exclude-module=pandas.tests \
		--exclude-module=numpy.array_api \
		--exclude-module=torch.utils.tensorboard \
		--exclude-module=torch.distributed \
		--log-level=INFO
	@chmod +x ./dist/instyper
	@echo "Linux binary built: dist/instyper"

build-windows:
	@echo "Building Windows binary..."
	pyinstaller --windowed src/instyper/__main__.py --name instyper.exe \
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
		--collect-all speechbrain \
		--collect-all huggingface_hub \
		--collect-all stt \
		--hidden-import=speechbrain \
		--hidden-import=huggingface_hub \
		--hidden-import=stt \
		--hidden-import=bs4 \
		--hidden-import=soupsieve \
		--hidden-import=torch \
		--hidden-import=torch.nn \
		--hidden-import=torch.nn.functional \
		--exclude-module=pytest \
		--exclude-module=spacy \
		--exclude-module=paddle \
		--exclude-module=paddlespeech \
		--exclude-module=jnius \
		--exclude-module=pandas.tests \
		--exclude-module=numpy.array_api \
		--exclude-module=torch.utils.tensorboard \
		--exclude-module=torch.distributed \
		--log-level=INFO
	@echo "Windows binary built: dist/instyper.exe"

build-macos:
	@echo "Building macOS binary..."
ifeq ($(ARCH),arm64)
	@echo "Building for Apple Silicon (arm64)..."
	arch -arm64 pyinstaller --windowed src/instyper/__main__.py --name instyper \
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
		--collect-all speechbrain \
		--collect-all huggingface_hub \
		--collect-all stt \
		--hidden-import=speechbrain \
		--hidden-import=huggingface_hub \
		--hidden-import=stt \
		--hidden-import=bs4 \
		--hidden-import=soupsieve \
		--hidden-import=torch \
		--hidden-import=torch.nn \
		--hidden-import=torch.nn.functional \
		--exclude-module=pytest \
		--exclude-module=spacy \
		--exclude-module=paddle \
		--exclude-module=paddlespeech \
		--exclude-module=jnius \
		--exclude-module=pandas.tests \
		--exclude-module=numpy.array_api \
		--exclude-module=torch.utils.tensorboard \
		--exclude-module=torch.distributed \
		--log-level=INFO \
		--codesign-identity=- \
		--osx-bundle-identifier=com.instyper.app \
		--target-architecture=arm64
else
	pyinstaller --windowed src/instyper/__main__.py --name instyper \
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
		--collect-all speechbrain \
		--collect-all huggingface_hub \
		--collect-all stt \
		--hidden-import=speechbrain \
		--hidden-import=huggingface_hub \
		--hidden-import=stt \
		--hidden-import=bs4 \
		--hidden-import=soupsieve \
		--hidden-import=torch \
		--hidden-import=torch.nn \
		--hidden-import=torch.nn.functional \
		--exclude-module=pytest \
		--exclude-module=spacy \
		--exclude-module=paddle \
		--exclude-module=paddlespeech \
		--exclude-module=jnius \
		--exclude-module=pandas.tests \
		--exclude-module=numpy.array_api \
		--exclude-module=torch.utils.tensorboard \
		--exclude-module=torch.distributed \
		--log-level=INFO \
		--codesign-identity=- \
		--osx-bundle-identifier=com.instyper.app \
		--target-architecture=x86_64
endif
	@echo "Setting macOS permissions..."
	@chmod 755 ./dist/instyper
	@xattr -dr com.apple.quarantine ./dist/instyper 2>/dev/null || true
	@echo "macOS binary built: dist/instyper"

run:
ifeq ($(DETECTED_OS),Windows)
	@echo "Running Windows binary..."
	./dist/instyper.exe
else
	@echo "Running $(DETECTED_OS) binary..."
	@echo "Verifying permissions..."
	@chmod 755 ./dist/instyper
	@xattr -dr com.apple.quarantine ./dist/instyper 2>/dev/null || true
	@if [ ! -x ./dist/instyper ]; then \
		echo "Error: Binary still not executable. Manual fix required."; \
		echo "Please follow these steps:"; \
		echo "1. Open System Settings → Privacy & Security"; \
		echo "2. Click 'Allow Anyway' under Security for instyper"; \
		echo "3. Try running 'make run' again"; \
		exit 1; \
	fi
	@echo "Launching..."
	./dist/instyper
endif

# Cleanup target
clean:
	@echo "Cleaning build artifacts and virtual environment..."
ifeq ($(DETECTED_OS),Windows)
	if (Test-Path 'build') { \
		echo "Removing build directory..."; \
		Remove-Item -Recurse -Force build; \
	}
	if (Test-Path 'dist') { \
		echo "Removing dist directory..."; \
		Remove-Item -Recurse -Force dist; \
	}
	if (Test-Path '*.spec') { \
		echo "Removing spec files..."; \
		Get-ChildItem -Path . -Filter "*.spec" | ForEach-Object { Remove-Item -Force $_.FullName }; \
	}
	if (Test-Path '__pycache__') { \
		echo "Removing __pycache__ directory..."; \
		Remove-Item -Recurse -Force __pycache__; \
	}
	if (Test-Path 'src/__pycache__') { \
		echo "Removing src/__pycache__ directory..."; \
		Remove-Item -Recurse -Force src/__pycache__; \
	}
	if (Test-Path 'src/instyper/__pycache__') { \
		echo "Removing src/instyper/__pycache__ directory..."; \
		Remove-Item -Recurse -Force src/instyper/__pycache__; \
	}
	if (Test-Path '.venv') { \
		echo "Removing virtual environment..."; \
		Remove-Item -Recurse -Force .venv; \
	}
else
	@if [ -d build ]; then \
		echo "Removing build directory..."; \
		rm -rf build; \
	fi
	@if [ -d dist ]; then \
		echo "Removing dist directory..."; \
		rm -rf dist; \
	fi
	@if ls *.spec 1> /dev/null 2>&1; then \
		echo "Removing spec files..."; \
		rm -f *.spec; \
	fi
	@if [ -d __pycache__ ]; then \
		echo "Removing __pycache__ directory..."; \
		rm -rf __pycache__; \
	fi
	@if [ -d src/__pycache__ ]; then \
		echo "Removing src/__pycache__ directory..."; \
		rm -rf src/__pycache__; \
	fi
	@if [ -d src/instyper/__pycache__ ]; then \
		echo "Removing src/instyper/__pycache__ directory..."; \
		rm -rf src/instyper/__pycache__; \
	fi
	@if [ -d .venv ]; then \
		echo "Removing virtual environment..."; \
		rm -rf .venv; \
	fi
endif
	@echo "Cleanup complete." 