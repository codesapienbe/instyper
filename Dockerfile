FROM python:3.11-slim-bullseye

RUN apt-get update && apt-get install -y \
    xauth \
    libgl1-mesa-glx \
    libx11-xcb1 \
    libxkbcommon-x11-0 \
    libportaudio2 \
    pulseaudio \
    dbus-x11 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN ./build.sh

ENV DISPLAY=:0
ENV PULSE_SERVER=unix:/tmp/pulseaudio.socket

RUN mkdir -p /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix && \
    mkdir -p /tmp/pulseaudio && \
    chmod 755 /tmp/pulseaudio

RUN useradd -m appuser
USER appuser

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
