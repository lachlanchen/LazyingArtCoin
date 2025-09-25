FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY README.md ./

# Create data dir for SQLite
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8080
CMD ["python", "-m", "app.server"]
