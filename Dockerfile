# Use the requested Python version
FROM python:3.14-slim

# Set the working directory container-side
WORKDIR /code

# Install system dependencies required for asyncpg and other Python C-extensions
# gcc, libffi-dev, and python3-dev are often needed for compiling
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
# Ensure you have a requirements.txt in your root
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Install Playwright browsers (Required for your 'verifier.py' / 'VibeVerifier')
RUN playwright install chromium
RUN playwright install-deps

# Copy the actual application code
COPY ./app ./app

# Expose port 8080 (Cloud Run default)
ENV PORT=8080

# Command to run the application
# We listen on 0.0.0.0 to accept external requests within the container
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]