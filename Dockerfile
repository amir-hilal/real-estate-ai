# Stage 1: build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools needed by LightGBM / scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# libgomp1 is required at runtime by LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ app/
COPY prompts/ prompts/
COPY ml/artifacts/ ml/artifacts/

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Environment defaults (overridden via docker-compose or env vars)
ENV MODEL_PATH=ml/artifacts/model.joblib \
    TRAINING_STATS_PATH=ml/artifacts/training_stats.json \
    PROMPTS_DIR=prompts \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host $HOST --port $PORT"]
