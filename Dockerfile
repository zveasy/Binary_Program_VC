# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for building Capstone
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libcapstone-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy all files from the current directory to the container
COPY . .

# Install required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the default command to run the disassembler script
CMD ["python", "rda_disassembler_enhanced.py"]
