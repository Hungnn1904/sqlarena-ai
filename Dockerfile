FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY ai ./ai
COPY backend ./backend
COPY postgre ./postgre
COPY question_create ./question_create

RUN mkdir -p /workspace/.runtime && chown -R appuser:appuser /workspace

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=6 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["sh", "-c", "cd backend && python -m app.cli migrate && python -m app.cli seed-demo && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
