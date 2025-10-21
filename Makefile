IMAGE_NAME := instyper:latest
DOCKERFILE := docker/Dockerfile

.PHONY: build run clean deploy

build:
	@echo "Preparing project and building docker image..."
	@echo "Note: Python virtualenv (.venv) is created inside the Docker builder stage; skipping local uv sync"
	@echo "Building docker image $(IMAGE_NAME) as final step..."
	@docker build -t $(IMAGE_NAME) -f $(DOCKERFILE) .


run: build
	@echo "Running Instyper on Docker..."
	# Minimal docker run: only mount per-user config by default; host integrations are optional
	@echo "To run: docker run -v $$HOME/.instyper:/root/.instyper $(IMAGE_NAME)";
	# Run container with only required per-user config mount; users can add more flags if needed
	docker run --rm -e HOME=/tmp -v $$HOME/.instyper:/root/.instyper $(IMAGE_NAME)


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
