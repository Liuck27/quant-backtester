# ==========================================
# Stage 1: Builder (Compiling C++ & Installing Deps)
# ==========================================
FROM python:3.11-slim as builder

# Install system dependencies required for C++ compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency definition
COPY pyproject.toml .

# Install build tools
RUN pip install --no-cache-dir setuptools wheel pybind11

# Copy source code
COPY src/ src/
COPY setup.py .
COPY README.md .

# Build and install the package (compiles C++ extensions)
RUN pip install .

# ==========================================
# Stage 2: Runtime (Minimal Image)
# ==========================================
FROM python:3.11-slim

# Install minimal runtime deps (libstdc++ needed for C++ ext)
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (for reloading/running)
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://postgres:postgres@db:5432/quant_backtester

# Expose API port
EXPOSE 8000

# Default command: Run database migrations then start the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]
