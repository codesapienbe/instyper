# Instyper Docker Image
# Voice typing application with GUI and speech recognition capabilities
# Multi-stage build: builder stage for compilation, runtime stage for execution

# =============================================================================
# Builder Stage: Install dependencies and build virtual environment
# =============================================================================
FROM ghcr.io/astral-sh/uv:debian AS builder
ENV DEBIAN_FRONTEND=noninteractive

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools and compilers (needed for Python packages with native extensions)
    build-essential \
    gcc \
    pkg-config \
    # Version control (needed for some Python packages)
    git \
    # Audio libraries and development headers
    libsndfile1-dev \
    libasound2-dev \
    portaudio19-dev \
    libpulse-dev \
    # Multimedia libraries for audio/video processing
    libavcodec-dev \
    libavformat-dev \
    libavdevice-dev \
    libavutil-dev \
    # Network and certificates (needed for downloading packages)
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/instyper

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Configure uv Python installation directory
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python

# Install Python dependencies using uv (creates .venv directory)
RUN uv sync --frozen --no-install-project

# Copy source code
COPY . /opt/instyper

# =============================================================================
# Runtime Stage: Minimal image with only runtime dependencies
# =============================================================================
FROM ghcr.io/astral-sh/uv:debian AS runtime
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime system dependencies (no build tools needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # GUI and display server dependencies
    xvfb \
    x11vnc \
    fluxbox \
    x11-utils \
    python3-tk \
    libgtk-3-0 \
    dbus \
    # Audio libraries (runtime only)
    libsndfile1 \
    libasound2 \
    libportaudio2 \
    libportaudiocpp0 \
    libpulse0 \
    # Multimedia libraries (install ffmpeg for all runtime codecs)
    ffmpeg \
    # Audio server
    pulseaudio \
    pulseaudio-utils \
    # Network tools
    curl \
    wget \
    ca-certificates \
    # Process monitoring
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/instyper

# Copy Python virtual environment from builder stage
COPY --from=builder /opt/instyper/.venv /opt/instyper/.venv

# Copy uv Python installation from builder stage
COPY --from=builder /opt/uv-python /opt/uv-python

# Copy source code (needed for the application to run)
COPY --from=builder /opt/instyper/src /opt/instyper/src
COPY --from=builder /opt/instyper/pyproject.toml /opt/instyper/

# Make virtual environment writable for non-root users
RUN chmod -R 777 /opt/instyper/.venv

# Expose VNC port for GUI access
EXPOSE 5900

# Default command to run the application
CMD pulseaudio --start || true && uv run instyper

