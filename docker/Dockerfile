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
RUN if ! command -v python3 >/dev/null 2>&1 || ! python3 -m pip --version >/dev/null 2>&1; then \
    apt-get update && apt-get install -y --no-install-recommends python3 python3-distutils python3-venv python3-pip && \
    ln -sf /usr/bin/python3 /usr/local/bin/python3 || true && \
    python3 -m pip install --upgrade pip setuptools wheel || true; \
    fi

WORKDIR /opt/instyper
COPY . /opt/instyper

ENV UV_PYTHON=/usr/bin/python3
RUN uv sync || true

# Ensure the virtualenv created by uv is usable by a non-root process when the container
# is started with a host UID via "--user $(id -u):$(id -g)". Make venv files world-readable
# and directories world-executable so the interpreter can be resolved by numeric UIDs.
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


