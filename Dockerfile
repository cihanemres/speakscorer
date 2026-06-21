FROM python:3.10-slim

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend source files
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY KULLANIM_KILAVUZU.md /app/

# Set working directory to backend
WORKDIR /app/backend

# Ensure upload folders exist
RUN mkdir -p uploads/audio uploads/avatars uploads/paragraphs

# Expose the default port for Hugging Face Spaces (7860)
EXPOSE 7860

# Run uvicorn. Shell formu, platformun verdiği $PORT'u kullanır (Render gibi);
# PORT yoksa 7860'a düşer (Hugging Face Spaces ve yerel/VM compose için).
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}
