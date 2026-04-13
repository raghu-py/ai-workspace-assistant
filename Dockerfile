FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY .env.example ./.env.example
COPY data.mcp_servers.example.json ./data.mcp_servers.example.json

RUN pip install --no-cache-dir .

RUN mkdir -p /app/data /app/data/uploads
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
