FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libc6-dev \
    make \
    python3-dev \
    libcapstone-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the application files
COPY . .

# Install Python dependencies, ensuring python-multipart is included
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install fastapi uvicorn python-multipart  # ✅ Explicitly install python-multipart

# Expose API port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
