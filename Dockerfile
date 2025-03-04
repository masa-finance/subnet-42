# Build stage for compiling dependencies
FROM --platform=linux/amd64 python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Final stage
FROM --platform=linux/amd64 python:3.10-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create directories for mounted volumes
RUN mkdir -p /app/keys /app/config

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    USE_TORCH=1

# Default command (can be overridden in docker-compose)
CMD ["python", "scripts/run_miner.py"] 