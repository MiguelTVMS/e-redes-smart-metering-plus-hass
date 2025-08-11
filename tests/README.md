# Tests for E-Redes Smart Metering Plus

- Run: `pytest -q`
- We rely on `pytest-homeassistant-custom-component` and Home Assistant core test fixtures.
- Cloud is mocked out to avoid network calls; webhook uses local URL.
