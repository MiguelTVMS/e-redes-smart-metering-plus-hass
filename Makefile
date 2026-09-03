ifeq ($(OS),Windows_NT)
BOOTSTRAP_COMMAND := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap-local.ps1
VALIDATE_COMMAND := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate.ps1
PYTHON := .venv\Scripts\python.exe
TEST_COMMAND := docker compose --profile tools run --rm --build tests
WEBHOOK_COMMAND := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/send-test-webhook.ps1
else
BOOTSTRAP_COMMAND := ./scripts/bootstrap-local
VALIDATE_COMMAND := ./scripts/validate
PYTHON := .venv/bin/python
TEST_COMMAND := $(PYTHON) -m pytest tests/ -q --tb=short
WEBHOOK_COMMAND := ./scripts/send-test-webhook
endif

SIMULATOR_ARGS ?=
SIMULATOR_COMMAND := $(PYTHON) scripts/simulate-webhook.py $(SIMULATOR_ARGS)

.PHONY: bootstrap validate test doctor sync-integration ha-up ha-down ha-restart ha-logs ha-onboard ha-credentials webhook simulate

bootstrap:
	$(BOOTSTRAP_COMMAND)

validate:
	$(VALIDATE_COMMAND)

test:
	$(TEST_COMMAND)

doctor:
	uv --version
	$(PYTHON) --version
	docker compose version
	docker info --format "Docker Engine {{.ServerVersion}} ({{.OSType}})"
	docker compose config --quiet

sync-integration:
	@echo "No copy required: Docker Compose mounts the integration source directly."

ha-up:
	docker compose up -d

ha-down:
	docker compose down

ha-restart:
	docker compose restart homeassistant

ha-logs:
	docker compose logs -f homeassistant

ha-onboard:
	docker compose run --rm homeassistant-onboarding

ha-credentials:
	$(PYTHON) scripts/onboard-home-assistant.py --show-credentials --credentials-file config/.dev-onboarding.json

webhook:
	$(WEBHOOK_COMMAND)

simulate:
	$(SIMULATOR_COMMAND)
