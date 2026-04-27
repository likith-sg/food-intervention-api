FROM python:3.11-slim

WORKDIR /app_root

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data && echo "[]" > data/user_history.json

ENV PORT=8080

EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
