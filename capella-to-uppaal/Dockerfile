# Use Python slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
#COPY requirements.txt .

# Install Python dependencies
#RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY capella_to_uppaal.py capella_to_uppaal.py 
COPY src/ ./src/

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Set the entrypoint
ENTRYPOINT ["python", "capella_to_uppaal.py"]

# Default command shows help
CMD ["--help"]