FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY . .
RUN python -m compileall -q /app/agent /app/api
RUN pip install --no-cache-dir -e .
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8002}"]
