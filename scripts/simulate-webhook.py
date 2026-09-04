#!/usr/bin/env python3
# ruff: noqa: T201
"""Continuously simulate E-Redes meter webhook data for local development."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_WEBHOOK_URL = "http://localhost:8123/api/webhook/e_redes_smart_metering_plus"
DEFAULT_CPE = "PT000000000000000000"

HOUSEHOLD_POWER = (
    (320, 0),
    (780, 0),
    (1650, 0),
    (3420, 0),
    (4580, 0),
    (2240, 0),
    (650, 0),
    (0, 420),
    (0, 1350),
    (410, 0),
)
SOLAR_POWER = (
    (720, 0),
    (280, 0),
    (0, 450),
    (0, 1650),
    (0, 3200),
    (0, 1450),
    (180, 0),
)
CONTRACTED_POWER_USAGE_RATIOS = (0.50, 0.82, 0.96, 1.05, 0.70)
VOLTAGE_PATTERN = (230.0, 229.6, 230.4, 231.1, 229.8, 230.2)


class WebhookRequestError(RuntimeError):
    """Represent a failed simulated webhook request."""


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Configure one deterministic meter simulation."""

    cpe: str
    scenario: str = "household"
    interval: float = 2.0
    phases: int = 1
    nominal_current_amps: float = 20.0
    initial_energy_import_wh: float = 14_817_930.0
    initial_energy_export_wh: float = 0.0


class MeterSimulator:
    """Generate an ordered stream of realistic E-Redes payloads."""

    def __init__(self, config: SimulationConfig) -> None:
        """Initialize simulation state."""
        self.config = config
        self.sample_index = 0
        self.energy_import_wh = config.initial_energy_import_wh
        self.energy_export_wh = config.initial_energy_export_wh
        self.max_import_w = 0
        self.max_export_w = 0
        self.max_import_time = "0000-00-00 00:00:00"
        self.max_export_time = "0000-00-00 00:00:00"

    def next_payload(self, timestamp: datetime) -> dict[str, Any]:
        """Return the next payload and advance cumulative energy counters."""
        formatted_timestamp = _format_timestamp(timestamp)
        voltage_l1 = VOLTAGE_PATTERN[self.sample_index % len(VOLTAGE_PATTERN)]
        voltage_l2 = round(voltage_l1 + 0.7, 1)
        voltage_l3 = round(voltage_l1 - 0.5, 1)
        import_w, export_w = self._power_values(voltage_l1)
        phase_import_w: tuple[int, int, int] | None = None
        if self.config.phases == 3 and self.config.scenario == "contracted-power":
            ratio = self._contracted_power_usage_ratio()
            phase_import_w = tuple(
                round(voltage * self.config.nominal_current_amps * ratio)
                for voltage in (voltage_l1, voltage_l2, voltage_l3)
            )
            import_w = sum(phase_import_w)

        if import_w > self.max_import_w:
            self.max_import_w = import_w
            self.max_import_time = formatted_timestamp
        if export_w > self.max_export_w:
            self.max_export_w = export_w
            self.max_export_time = formatted_timestamp

        payload: dict[str, Any] = {
            "cpe": self.config.cpe.strip().upper(),
            "SourceTimestamp": formatted_timestamp,
            "LocalTimestamp": formatted_timestamp,
            "activeEnergyExport": round(self.energy_export_wh, 3),
            "activeEnergyImport": round(self.energy_import_wh, 3),
            "instantaneousActivePowerExport": export_w,
            "instantaneousActivePowerImport": import_w,
            "maxActivePowerExport": self.max_export_w,
            "maxActivePowerExportTime": self.max_export_time,
            "maxActivePowerImport": self.max_import_w,
            "maxActivePowerImportTime": self.max_import_time,
            "voltageL1": voltage_l1,
            "clock": formatted_timestamp,
        }

        if self.config.phases == 3:
            payload.update(
                {
                    "voltageL2": voltage_l2,
                    "voltageL3": voltage_l3,
                }
            )
            import_values = phase_import_w or _split_power(import_w)
            for phase, value in enumerate(import_values, start=1):
                payload[f"instantaneousActivePowerImportL{phase}"] = value
            for phase, value in enumerate(_split_power(export_w), start=1):
                payload[f"instantaneousActivePowerExportL{phase}"] = value

        self.energy_import_wh += import_w * self.config.interval / 3600
        self.energy_export_wh += export_w * self.config.interval / 3600
        self.sample_index += 1
        return payload

    def _power_values(self, voltage: float) -> tuple[int, int]:
        """Return import and export power for the current scenario step."""
        if self.config.scenario == "contracted-power":
            return (
                round(
                    voltage
                    * self.config.nominal_current_amps
                    * self._contracted_power_usage_ratio()
                ),
                0,
            )

        pattern = SOLAR_POWER if self.config.scenario == "solar" else HOUSEHOLD_POWER
        return pattern[self.sample_index % len(pattern)]

    def _contracted_power_usage_ratio(self) -> float:
        """Return the usage ratio for the current scenario step."""
        return CONTRACTED_POWER_USAGE_RATIOS[
            self.sample_index % len(CONTRACTED_POWER_USAGE_RATIOS)
        ]


def _format_timestamp(timestamp: datetime) -> str:
    """Format a timestamp in the shape sent by E-Redes."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _split_power(total_watts: int) -> tuple[int, int, int]:
    """Split a total across three phases without changing the total."""
    phase_1 = round(total_watts * 0.34)
    phase_2 = round(total_watts * 0.33)
    return phase_1, phase_2, total_watts - phase_1 - phase_2


def post_payload(
    url: str,
    payload: dict[str, Any],
    timeout: float,
    auth_token: str | None = None,
) -> int:
    """Post one payload and return the HTTP status code."""
    headers = {"Accept": "text/plain", "Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            response.read()
            return response.status
    except HTTPError as err:
        response_body = err.read().decode("utf-8", errors="replace").strip()
        hint = _http_error_hint(err.code, payload["cpe"])
        details = f": {response_body}" if response_body else ""
        raise WebhookRequestError(
            f"Home Assistant returned HTTP {err.code}{details}. {hint}"
        ) from err
    except URLError as err:
        raise WebhookRequestError(
            f"Could not connect to {url}: {err.reason}. "
            "Start Home Assistant with 'make ha-up' and verify the URL."
        ) from err


def _http_error_hint(status_code: int, cpe: str) -> str:
    """Return an actionable hint for common Home Assistant responses."""
    if status_code == 403:
        return (
            f"Add CPE {cpe} in the integration's Configure dialog, or pass the "
            "configured value with --cpe."
        )
    if status_code == 401:
        return "Pass the configured token with --auth-token."
    if status_code == 404:
        return "Add or reload the integration and verify the webhook URL."
    return "Check the Home Assistant logs for the request failure."


def _positive_float(value: str) -> float:
    """Parse a command-line value that must be greater than zero."""
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _non_negative_int(value: str) -> int:
    """Parse a command-line integer that must not be negative."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse simulator command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", default=os.environ.get("WEBHOOK_URL", DEFAULT_WEBHOOK_URL)
    )
    parser.add_argument("--cpe", default=os.environ.get("TEST_CPE", DEFAULT_CPE))
    parser.add_argument(
        "--auth-token",
        default=os.environ.get("WEBHOOK_AUTH_TOKEN"),
        help="Authorization token configured in Home Assistant",
    )
    parser.add_argument(
        "--scenario",
        choices=("household", "solar", "contracted-power"),
        default=os.environ.get("SIMULATION_SCENARIO", "household"),
    )
    parser.add_argument(
        "--interval",
        type=_positive_float,
        default=os.environ.get("SIMULATION_INTERVAL", "2"),
        help="seconds between payloads (default: 2)",
    )
    parser.add_argument(
        "--count",
        type=_non_negative_int,
        default=os.environ.get("SIMULATION_COUNT", "0"),
        help="payloads to send; zero runs until Ctrl+C (default: 0)",
    )
    parser.add_argument(
        "--phases",
        type=int,
        choices=(1, 3),
        default=os.environ.get("SIMULATION_PHASES", "1"),
    )
    parser.add_argument(
        "--nominal-current-amps",
        type=_positive_float,
        default=os.environ.get("SIMULATION_NOMINAL_CURRENT_AMPS", "20"),
        help="nominal current for the contracted-power scenario (default: 20)",
    )
    parser.add_argument("--timeout", type=_positive_float, default=10.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print generated JSON without contacting Home Assistant",
    )
    parser.add_argument(
        "--print-payload",
        action="store_true",
        help="print each JSON payload before sending it",
    )
    args = parser.parse_args(argv)
    if not args.cpe.strip():
        parser.error("--cpe cannot be empty")
    return args


def run(args: argparse.Namespace) -> int:
    """Run a simulation from parsed arguments."""
    config = SimulationConfig(
        cpe=args.cpe,
        scenario=args.scenario,
        interval=args.interval,
        phases=args.phases,
        nominal_current_amps=args.nominal_current_amps,
    )
    simulator = MeterSimulator(config)
    count = 1 if args.dry_run and args.count == 0 else args.count
    duration = f"{count} payload(s)" if count else "until Ctrl+C"
    print(
        f"Simulating {args.scenario} data for {config.cpe.strip().upper()} "
        f"with {args.phases} phase(s), every {args.interval:g}s, {duration}."
    )
    if not args.dry_run:
        print(f"Webhook: {args.url}")

    started_at = datetime.now(UTC)
    next_deadline = time.monotonic()
    sent = 0
    try:
        while count == 0 or sent < count:
            timestamp = started_at + timedelta(seconds=sent * args.interval)
            payload = simulator.next_payload(timestamp)
            if args.dry_run or args.print_payload:
                print(json.dumps(payload, indent=2, sort_keys=True))

            status: int | str = "dry-run"
            if not args.dry_run:
                status = post_payload(args.url, payload, args.timeout, args.auth_token)

            sent += 1
            print(
                f"[{sent:04d}] {payload['SourceTimestamp']} status={status} "
                f"import={payload['instantaneousActivePowerImport']}W "
                f"export={payload['instantaneousActivePowerExport']}W "
                f"voltage={payload['voltageL1']:.1f}V"
            )

            if count and sent >= count:
                break
            next_deadline += args.interval
            time.sleep(max(0.0, next_deadline - time.monotonic()))
    except KeyboardInterrupt:
        print(f"\nSimulation stopped after {sent} payload(s).")
        return 0
    except WebhookRequestError as err:
        print(f"Simulation stopped: {err}", file=sys.stderr)
        return 1

    print(f"Simulation completed after {sent} payload(s).")
    return 0


def main() -> int:
    """Run the command-line simulator."""
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
