# Orchestrix: Telegram bot by default; override the command for the API or CLI.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ORCHESTRIX_DATA_DIR=/app/data \
    LOG_DIR=/app/logs \
    GOOGLE_CREDENTIALS_DIR=/app/credentials

WORKDIR /app

# CPU-only torch first, so sentence-transformers doesn't pull CUDA wheels.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home orchestrix && mkdir -p data logs credentials \
    && chown -R orchestrix:orchestrix /app
USER orchestrix

EXPOSE 8000
CMD ["python", "telegram_bot.py"]
