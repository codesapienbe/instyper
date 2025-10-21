FROM ghcr.io/astral-sh/uv:alpine AS builder

WORKDIR /opt/instyper
COPY . /opt/instyper

FROM ghcr.io/astral-sh/uv:alpine AS runtime

WORKDIR /opt/instyper
COPY --from=builder /opt/instyper /opt/instyper
COPY docker/entrypoint.sh /opt/instyper/docker/entrypoint.sh
RUN chmod +x /opt/instyper/docker/entrypoint.sh || true

EXPOSE 5900

ENTRYPOINT ["/opt/instyper/docker/entrypoint.sh"]

