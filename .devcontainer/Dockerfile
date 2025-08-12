# Devcontainer for Home Assistant custom component development
# Base on mcr.microsoft.com/devcontainers/python for tooling + run HA in compose
FROM mcr.microsoft.com/devcontainers/python:3.13

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl git jq tini \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /workspaces/e-redes-smart-metering-plus-hass

# Copy project files (used for initial pip install)
COPY requirements_dev.txt ./

# Pre-install dev deps into container venv
RUN pip install --upgrade pip && pip install -r requirements_dev.txt

# Default shell
SHELL ["/bin/bash", "-lc"]

# Use non-root user from devcontainers base
USER vscode

# Entrypoint: nothing; VS Code will attach and we can use docker-compose to run HA
CMD ["sleep", "infinity"]
