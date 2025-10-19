FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
   build-essential gcc git pkg-config libsndfile1-dev libasound2-dev portaudio19-dev \
   libpulse-dev libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev \
   xvfb x11vnc fluxbox x11-utils python3-tk pulseaudio pulseaudio-utils \
   libgtk-3-0 dbus ca-certificates \
   curl wget git procps \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /opt/instyper
COPY . /opt/instyper

RUN pip install --upgrade pip setuptools wheel && \
    # Install uv using Astral's official installer
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    # Use uv to sync/build the project (best-effort); fall back to editable install if build artifacts are missing
    uv sync || true && \
    uv build || true && \
    if [ -d "dist" ] && ls dist/*.whl >/dev/null 2>&1; then \
        pip install dist/*.whl; \
    else \
        pip install -e .; \
    fi

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5900

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]


