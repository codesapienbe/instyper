.PHONY: build run clean deploy

build:
	@echo "Detecting OS and installing PortAudio prerequisites..."
	@if [ "$(uname)" = "Darwin" ]; then \
		brew install portaudio || true; \
	elif [ -f /etc/debian_version ]; then \
		sudo apt update && sudo apt install -y portaudio19-dev libportaudio2 || true; \
	elif [ -f /etc/fedora-release ] || [ -f /etc/redhat-release ]; then \
		sudo dnf install -y portaudio-devel || true; \
	elif [ -f /etc/arch-release ]; then \
		sudo pacman -S --noconfirm portaudio || true; \
	else \
		echo "OS not recognized. Please install PortAudio system dependencies manually."; \
	fi
	uv sync

run:
	uv run instyper

clean:
	@echo "Removing virtualenv (.venv)..."
	@if [ -n "$$VIRTUAL_ENV" ]; then \
		deactivate || true; \
	fi
	rm -rf .venv

deploy:
	uv build


