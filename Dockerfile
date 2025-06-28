FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for audio, etc.)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy the global requirements.txt
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy all code (backend, frontend, start.sh, etc)
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY start.sh ./
COPY backend/.env ./backend/.env

EXPOSE 8000 8501

# Only make start.sh executable (not .env!)
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
