# Use Python base image
FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install fiber
RUN pip install --no-cache-dir git+https://github.com/5u6r054/fiber.git@fix/remove-bittensor-commit-reveal-dependency

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ROLE=miner

# Default command (can be overridden by docker-compose)
CMD ["sh", "-c", "if [ \"$ROLE\" = \"validator\" ]; then python -m neurons.validator; else python -m neurons.miner; fi"] 