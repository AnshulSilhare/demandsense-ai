# ═══════════════════════════════════════════════
# DemandSense AI — Docker (Render.com / portable)
# ═══════════════════════════════════════════════
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Render injects PORT at runtime; fallback to 7860 for local dev
EXPOSE 7860

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}
