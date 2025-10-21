UV := uv

.PHONY: build run clean deploy release

# Create or sync the local virtualenv using uv
build:
	@echo "Preparing project and ensuring virtualenv with uv..."
	@$(UV) sync --no-install-project || true


# Run the application via uv. Assumes user has a working X server and optional audio devices on host.
run: build
	@echo "Running Instyper via uv..."
	@$(UV) run instyper


clean:
	@echo "Removing virtualenv (.venv)..."
	@if [ -n "$$VIRTUAL_ENV" ]; then \
		deactivate || true; \
	fi
	rm -rf .venv


deploy: build
	@echo "Deploy step complete."


release:
	@echo "Creating git tag for release..."
	@if [ ! -f VERSION ]; then \
		echo "Error: VERSION file not found"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION | tr -d '\n'); \
	if [ -z "$$VERSION" ]; then \
		echo "Error: VERSION file is empty"; \
		exit 1; \
	fi; \
	echo "Tagging version: v$$VERSION"; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	git push origin "v$$VERSION"
