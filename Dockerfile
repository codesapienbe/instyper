FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl build-essential python3 python3-pip python3-venv git pkg-config libssl-dev mingw-w64 && \
    rm -rf /var/lib/apt/lists/*

# Install Rust and add Windows target
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup target add x86_64-pc-windows-gnu

# Install PyOxidizer
RUN pip3 install pyoxidizer

# Set workdir and copy project
WORKDIR /app
COPY . .

# Build both Linux and Windows binaries
CMD pyoxidizer build && pyoxidizer build --target x86_64-pc-windows-gnu