"""Tests for the supported Home Assistant development baselines."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_HOME_ASSISTANT = "2026.9.0"
MINIMUM_HOME_ASSISTANT = "2026.1.0"


def _read(path: str) -> str:
    """Read one tracked development file."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_current_home_assistant_baseline_is_consistent() -> None:
    """Primary tooling and containers must use the current HA baseline."""
    assert f"homeassistant=={CURRENT_HOME_ASSISTANT}" in _read("requirements_dev.txt")
    image = f"ghcr.io/home-assistant/home-assistant:{CURRENT_HOME_ASSISTANT}"
    assert _read("Dockerfile.tests").startswith(f"FROM {image}\n")
    assert "!requirements_dev_base.txt" in _read(".dockerignore")
    assert _read("docker-compose.yml").count(f"image: {image}") == 3
    assert "python-version: '3.14'" in _read(".github/workflows/tests.yml")
    assert "python-version: '3.14'" in _read(".github/workflows/lint.yml")


def test_minimum_home_assistant_baseline_is_explicit() -> None:
    """HACS and minimum CI must agree on the oldest supported HA release."""
    hacs = json.loads(_read("hacs.json"))
    assert hacs["homeassistant"] == MINIMUM_HOME_ASSISTANT
    assert f"homeassistant=={MINIMUM_HOME_ASSISTANT}" in _read(
        "requirements_dev_minimum.txt"
    )
    tests_workflow = _read(".github/workflows/tests.yml")
    assert "Pytest (Home Assistant 2026.1 minimum)" in tests_workflow
    assert "python-version: '3.13'" in tests_workflow
