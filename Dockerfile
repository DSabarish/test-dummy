# Minimal Cloud Run: FastAPI inference + frontend
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app/ML-code

COPY ML-code/requirements.txt ML-code/
RUN pip install --no-cache-dir -r ML-code/requirements.txt

COPY ML-code/ ML-code/
COPY frontend/ frontend/
COPY config.yaml .

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn inference:app --host 0.0.0.0 --port ${PORT:-8080}"]
