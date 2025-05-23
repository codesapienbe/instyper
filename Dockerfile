# Dockerfile for Instyper PyOxidizer build
FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl build-essential python3 python3-pip python3-venv git pkg-config libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install PyOxidizer
RUN pip3 install pyoxidizer

# Set workdir and copy project
WORKDIR /app
COPY . .

# Build the binary
CMD ["pyoxidizer", "build"]