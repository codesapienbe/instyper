IMAGE_NAME := instyper:local
DOCKERFILE := docker/Dockerfile

.PHONY: build run clean deploy

build:
	@echo "Preparing project and building docker image..."
	@uv sync || true

	@echo "Building docker image $(IMAGE_NAME) as final step..."
	@docker build -t $(IMAGE_NAME) -f $(DOCKERFILE) .

run:
	@# If Docker image exists, run it with X11 forwarding and sound device; otherwise run locally
	@if docker image inspect $(IMAGE_NAME) >/dev/null 2>&1; then \
		echo "Found docker image $(IMAGE_NAME) - running container..."; \
		XAUTH="$${XAUTHORITY:-}"; \
		if [ -n "$$XAUTH" ]; then \
			XAUTH_VOL="-v $$XAUTH:/root/.Xauthority:ro -e XAUTHORITY=/root/.Xauthority"; \
		else \
			XAUTH_VOL=""; \
		fi; \
		docker run --rm -it $$XAUTH_VOL -e DISPLAY=$$DISPLAY -e ENABLE_GLOBAL_HOTKEY=0 -e ENABLE_AUTO_PASTE=0 -v $$HOME/.instyper:/root/.instyper -v /tmp/.X11-unix:/tmp/.X11-unix --device /dev/snd $(IMAGE_NAME); \
	else \
		echo "Docker image $(IMAGE_NAME) not found - running locally"; \
		uv run instyper; \
	fi

clean:
	@echo "Removing virtualenv (.venv)..."
	@if [ -n "$$VIRTUAL_ENV" ]; then \
		deactivate || true; \
	fi
	rm -rf .venv

deploy:
	uv build
