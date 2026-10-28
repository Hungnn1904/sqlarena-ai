FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY ai ./ai
COPY backend ./backend
COPY postgre ./postgre

EXPOSE 8000

CMD ["sh", "-c", "cd backend && python -m app.cli migrate && python -m app.cli seed-demo && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
