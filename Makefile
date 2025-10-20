IMAGE_NAME := instyper:local
DOCKERFILE := docker/Dockerfile

.PHONY: build run clean deploy

build:
	@echo "Preparing project and building docker image..."
	@uv sync || true

	@echo "Building docker image $(IMAGE_NAME) as final step..."
	@docker build -t $(IMAGE_NAME) -f $(DOCKERFILE) .

run:
	@echo "Running Instyper on Docker..."
	# Run the application in Docker with X11, XAUTH, audio and GPU mounts
	@echo "Starting app in Docker (ensure X is forwarded):";
	# Validate DISPLAY
	if [ -z "${DISPLAY}" ]; then \
		echo "ERROR: DISPLAY is not set on the host. You need an X server available to run the GUI inside Docker."; \
		echo "If you want to run locally use 'make run' (without DOCKER=1). To run in docker ensure DISPLAY is exported, e.g. export DISPLAY=":0""; \
		exit 1; \
	fi; \

	# Allow override of XAUTH path via environment variable; default to ${HOME}/.Xauthority
	# Use $$ to defer expansion to the shell (make recipes need $$ for literal $)
	XAUTH_PATH="$${XAUTH:-$${HOME}/.Xauthority}"; \
	XAUTH_ARGS=""; \
	if [ -f "$$XAUTH_PATH" ]; then \
		echo "Using XAUTH: $$XAUTH_PATH"; \
		XAUTH_ARGS="-e XAUTHORITY=$$XAUTH_PATH -v $$XAUTH_PATH:$$XAUTH_PATH:ro"; \
	else \
		echo "No XAUTH file found at $$XAUTH_PATH; you can either run 'xhost +local:root' before running or set XAUTH env to point to your .Xauthority file."; \
		XAUTH_ARGS=""; \
	fi; \

	# Pulse audio socket (per-user)
	PULSE_SOCKET="/run/user/$$(id -u)/pulse/native"; \
	PULSE_ARGS=""; \
	if [ -S "$$PULSE_SOCKET" ]; then \
		PULSE_ARGS="-v $$PULSE_SOCKET:$$PULSE_SOCKET:ro -e PULSE_SERVER=unix:$$PULSE_SOCKET"; \
	fi; \

	# DBus socket (optional)
	DBUS_ARGS=""; \
	if [ -S "/run/dbus/system_bus_socket" ]; then \
		DBUS_ARGS="-v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:ro"; \
	fi; \

	docker run --rm $${XAUTH_ARGS} -e DISPLAY=$$DISPLAY -e HOME=/tmp -v /tmp/.X11-unix:/tmp/.X11-unix $${PULSE_ARGS} $${DBUS_ARGS} \
			--device /dev/snd --device /dev/dri --shm-size=1g --network host \
			-e ENABLE_GLOBAL_HOTKEY=0 -e ENABLE_AUTO_PASTE=0 \
			-v $$HOME/.instyper:/root/.instyper \
			$(IMAGE_NAME);


clean:
	@echo "Removing virtualenv (.venv)..."
	@if [ -n "$$VIRTUAL_ENV" ]; then \
		deactivate || true; \
	fi
	rm -rf .venv

deploy:
	@echo "Deploy: use local image 'instyper:latest' if present; otherwise build"
	$(MAKE) build;
	@echo "Deploy step complete."
