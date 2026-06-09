# Install stage
FROM python:3.13-slim

COPY . /app
WORKDIR /app

# Install ai-assistant
RUN pip install .
# Install dependencies for default storage
RUN pip install --no-cache-dir nano-vectordb networkx
# Install Java and required build dependencies
RUN apt-get update && apt-get install -y openjdk-21-jre

# Create persistent data directories AFTER package installation
RUN mkdir -p /app/data/rag_storage

ENV WORKING_DIR=/app/data/rag_storage
ENV NO_AUTH=True

# Expose the default port
EXPOSE 8200

# Set entrypoint
ENTRYPOINT ["ai_assistant", "server", "run", "-b", "0.0.0.0"]

