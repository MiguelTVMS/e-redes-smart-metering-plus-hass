.PHONY: bootstrap validate test sync-integration ha-up ha-down ha-restart ha-logs webhook

bootstrap:
	./scripts/bootstrap-local

validate:
	./scripts/validate

test:
	.venv/bin/pytest tests/ -q --tb=short

sync-integration:
	mkdir -p config/custom_components/e_redes_smart_metering_plus
	rsync -a --delete --exclude '__pycache__/' custom_components/e_redes_smart_metering_plus/ config/custom_components/e_redes_smart_metering_plus/

ha-up: sync-integration
	docker compose up -d

ha-down:
	docker compose down

ha-restart: sync-integration
	docker compose restart homeassistant

ha-logs:
	docker compose logs -f homeassistant

webhook:
	./scripts/send-test-webhook
