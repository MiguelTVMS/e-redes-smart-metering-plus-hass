.PHONY: bootstrap validate test ha-up ha-down ha-restart ha-logs webhook

bootstrap:
	./scripts/bootstrap-local

validate:
	./scripts/validate

test:
	.venv/bin/pytest tests/ -q --tb=short

ha-up:
	docker compose up -d

ha-down:
	docker compose down

ha-restart:
	docker compose restart homeassistant

ha-logs:
	docker compose logs -f homeassistant

webhook:
	./scripts/send-test-webhook
