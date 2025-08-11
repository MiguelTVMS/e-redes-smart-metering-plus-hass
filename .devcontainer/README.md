# Dev Containers

This repository includes a VS Code Dev Container for developing and testing this Home Assistant custom integration.

What you get:

- Python 3.13 toolchain with Black, Ruff, Pytest installed
- Home Assistant 2025.6.0 running in a sibling container
- Live-mounted config folder and the custom component to iterate quickly

How to use:

1. Open this repo in VS Code.
2. Install the "Dev Containers" extension.
3. Reopen in container when prompted.
4. From the container, start Home Assistant using the embedded compose:

   docker compose -f .devcontainer/docker-compose.yml up -d homeassistant

5. Open <http://localhost:8123> and complete onboarding.

Run tests:

   pytest -q

Stop services:

   docker compose -f .devcontainer/docker-compose.yml down
