FROM python:3.11-slim

WORKDIR /app

# Install uv directly from the official Astral Docker image (best practice)
# This places uv and uvx directly into /bin so they are on the PATH
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run the server. WORKDIR is /app, so backend.server:app correctly resolves to /app/backend/server.py
CMD ["python3", "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
