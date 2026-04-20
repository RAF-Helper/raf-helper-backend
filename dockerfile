FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY alembic/ ./alembic/

# Install uv and dependencies
RUN pip install uv
RUN uv sync

RUN mkdir -p /app/storage

EXPOSE 10000

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
