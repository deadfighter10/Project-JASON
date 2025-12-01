# Use a lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY server.py .

# Create a directory for the database volume
RUN mkdir -p /mnt/nas

# Expose the default FastAPI port
EXPOSE 3333

# Run the server
# host 0.0.0.0 is crucial for Docker networking
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3333"]