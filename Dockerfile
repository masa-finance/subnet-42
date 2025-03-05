# Use Python base image
FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
RUN . "$HOME/.cargo/env"

# Set working directory
WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN . "$HOME/.cargo/env" && pip install --prefer-binary .

# Copy application code
COPY neurons neurons/
COPY miner miner/
COPY validator validator/
COPY interfaces interfaces/
COPY scripts scripts/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden by docker-compose)
CMD ["sh", "-c", "if [ \"$ROLE\" = \"validator\" ]; then python scripts/run_validator.py; else python scripts/run_miner.py; fi"] 