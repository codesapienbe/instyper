FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc fluxbox x11-utils python3-tk pulseaudio pulseaudio-utils \
    libgtk-3-0 dbus ca-certificates \
    wget git procps \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/instyper
COPY . /opt/instyper

RUN pip install --upgrade pip setuptools wheel && pip install -e .

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5900

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]


