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


# Start Streamlit app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
