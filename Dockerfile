FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone camply repository at a specific version
RUN git clone https://github.com/juftin/camply.git /app/camply
WORKDIR /app/camply
RUN git checkout v0.32.9  # Using latest stable version

# Install camply and its dependencies
RUN pip install -e .

# Create directory for custom code
WORKDIR /app/custom
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy your package
COPY . /app/custom/

# Install your package in editable mode
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/custom/logs /app/custom/output

# Set environment variables
ENV PYTHONPATH=/app/custom:/app/camply:$PYTHONPATH

# Set working directory to custom code
WORKDIR /app/custom

# Default command (can be overridden)
CMD ["python", "-m", "favorites.californias_best"]
