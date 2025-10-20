FROM ghcr.io/astral-sh/uv:debian
ENV DEBIAN_FRONTEND=noninteractive

# Ensure a minimal build toolchain and python/pip are available when falling back to a plain debian image
RUN apt-get update && apt-get install -y --no-install-recommends \
   build-essential gcc git pkg-config libsndfile1-dev libasound2-dev portaudio19-dev \
   libpulse-dev libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev \
   xvfb x11vnc fluxbox x11-utils python3-tk pulseaudio pulseaudio-utils \
   libgtk-3-0 dbus ca-certificates \
   curl wget git procps apt-transport-https ca-certificates gnupg2 \
|| true && rm -rf /var/lib/apt/lists/*

# If python3 or pip are missing (e.g. when BASE_IMAGE is a plain debian), install them
RUN if ! command -v python3.10 >/dev/null 2>&1; then \
    apt-get update && apt-get install -y --no-install-recommends python3.10 python3.10-venv python3.10-pip python3.10-distutils && \
    ln -sf /usr/bin/python3.10 /usr/local/bin/python3 || true && \
    python3.10 -m pip install --upgrade pip setuptools wheel || true; \
    fi

WORKDIR /opt/instyper
COPY . /opt/instyper

ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN mkdir -p /opt/uv-python && chmod -R 755 /opt/uv-python
RUN uv sync || true

# Ensure the virtualenv created by uv and the Python installation are usable by a non-root process
# when the container is started with a host UID via "--user $(id -u):$(id -g)".
RUN chmod -R 755 /opt/uv-python || true
RUN if [ -d /opt/instyper/.venv ]; then \
    chmod -R 755 /opt/instyper/.venv || true; \
    find /opt/instyper/.venv -type f -exec chmod 644 {} \; || true; \
    if [ -d /opt/instyper/.venv/bin ]; then \
        chmod 755 /opt/instyper/.venv/bin/* || true; \
    fi; \
    fi

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5900

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]


