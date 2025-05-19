FROM python:3.13-alpine

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    curl \
    git

COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start Streamlit app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
