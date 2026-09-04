"""Tests for the local E-Redes webhook simulator."""

from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "simulate-webhook.py"
SPEC = importlib.util.spec_from_file_location("webhook_simulator", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
webhook_simulator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = webhook_simulator
SPEC.loader.exec_module(webhook_simulator)


def test_household_payload_advances_energy_and_maximum() -> None:
    """Successive payloads should contain ordered, cumulative measurements."""
    simulator = webhook_simulator.MeterSimulator(
        webhook_simulator.SimulationConfig(
            cpe=" pt000test ", scenario="household", interval=2
        )
    )
    first = simulator.next_payload(datetime(2026, 9, 1, 12, 0, tzinfo=UTC))
    second = simulator.next_payload(datetime(2026, 9, 1, 12, 0, 2, tzinfo=UTC))

    assert first["cpe"] == "PT000TEST"
    assert first["SourceTimestamp"] == "2026-09-01 12:00:00"
    assert second["SourceTimestamp"] == "2026-09-01 12:00:02"
    assert first["activeEnergyImport"] == 14_817_930
    assert second["activeEnergyImport"] == pytest.approx(
        14_817_930 + 320 * 2 / 3600, abs=0.001
    )
    assert first["maxActivePowerImport"] == 320
    assert second["maxActivePowerImport"] == 780
    assert second["maxActivePowerImportTime"] == "2026-09-01 12:00:02"


def test_three_phase_payload_preserves_total_power() -> None:
    """Three-phase measurements should add up to their corresponding totals."""
    simulator = webhook_simulator.MeterSimulator(
        webhook_simulator.SimulationConfig(cpe="TEST", phases=3)
    )
    payload = simulator.next_payload(datetime(2026, 9, 1, tzinfo=UTC))

    assert payload["voltageL2"] == pytest.approx(payload["voltageL1"] + 0.7)
    assert payload["voltageL3"] == pytest.approx(payload["voltageL1"] - 0.5)
    assert (
        sum(payload[f"instantaneousActivePowerImportL{phase}"] for phase in (1, 2, 3))
        == payload["instantaneousActivePowerImport"]
    )
    assert (
        sum(payload[f"instantaneousActivePowerExportL{phase}"] for phase in (1, 2, 3))
        == payload["instantaneousActivePowerExport"]
    )


@pytest.mark.parametrize("phases", (1, 3))
def test_contracted_power_scenario_crosses_alert_thresholds(phases: int) -> None:
    """Samples should exercise normal, warning, critical, and exceeded usage."""
    simulator = webhook_simulator.MeterSimulator(
        webhook_simulator.SimulationConfig(
            cpe="TEST",
            scenario="contracted-power",
            phases=phases,
            nominal_current_amps=20,
        )
    )
    ratios = []
    for sample in range(5):
        payload = simulator.next_payload(
            datetime(2026, 9, 1, 12, 0, sample, tzinfo=UTC)
        )
        if phases == 1:
            ratios.append(
                payload["instantaneousActivePowerImport"] / (payload["voltageL1"] * 20)
            )
        else:
            ratios.append(
                max(
                    payload[f"instantaneousActivePowerImportL{phase}"]
                    / (payload[f"voltageL{phase}"] * 20)
                    for phase in (1, 2, 3)
                )
            )

    assert ratios == pytest.approx(
        webhook_simulator.CONTRACTED_POWER_USAGE_RATIOS, abs=0.001
    )


def test_post_payload_sends_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sender should post JSON to the requested webhook URL."""
    response = Mock()
    response.status = 200
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    urlopen = Mock(return_value=response)
    monkeypatch.setattr(webhook_simulator, "urlopen", urlopen)

    payload = {"cpe": "TEST", "voltageL1": 230.0}
    assert (
        webhook_simulator.post_payload(
            "http://localhost/webhook", payload, 5, "configured-token"
        )
        == 200
    )

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost/webhook"
    assert request.method == "POST"
    assert json.loads(request.data) == payload
    assert request.headers["Authorization"] == "Bearer configured-token"
    assert urlopen.call_args.kwargs["timeout"] == 5


def test_forbidden_response_explains_cpe_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rejected CPE should produce an actionable simulator error."""
    error = HTTPError(
        "http://localhost/webhook",
        403,
        "Forbidden",
        {},
        Mock(read=Mock(return_value=b"CPE not configured")),
    )
    monkeypatch.setattr(webhook_simulator, "urlopen", Mock(side_effect=error))

    with pytest.raises(webhook_simulator.WebhookRequestError) as exc_info:
        webhook_simulator.post_payload("http://localhost/webhook", {"cpe": "TEST"}, 5)

    assert "HTTP 403" in str(exc_info.value)
    assert "Add CPE TEST" in str(exc_info.value)
