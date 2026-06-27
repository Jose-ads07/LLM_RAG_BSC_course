FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY rag_files /app/rag_files

EXPOSE 6661

CMD sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-6661}"
