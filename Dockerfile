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

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Copy just pyproject.toml first and install dependencies
COPY pyproject.toml .
RUN . "$HOME/.cargo/env" && pip install --prefer-binary .

# Now copy application code (these layers will change frequently)
COPY interfaces interfaces/
COPY scripts scripts/
COPY neurons neurons/
COPY miner miner/
COPY validator validator/

# Copy entrypoint script last since it changes most frequently
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Default command (can be overridden by docker-compose)
CMD ["sh", "-c", "if [ \"$ROLE\" = \"validator\" ]; then python scripts/run_validator.py; else python scripts/run_miner.py; fi"] 