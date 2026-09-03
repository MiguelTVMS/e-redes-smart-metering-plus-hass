"""Tests for the unattended Home Assistant development onboarding helper."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
from types import ModuleType

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "onboard-home-assistant.py"
)


def _load_onboarding_module() -> ModuleType:
    """Load the standalone development helper as a module."""
    spec = importlib.util.spec_from_file_location("dev_onboarding", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


onboarding = _load_onboarding_module()


class FakeClient:
    """Record onboarding operations without making HTTP requests."""

    def __init__(self, initial_status: dict[str, bool]) -> None:
        """Initialize the fake client."""
        self.status = initial_status.copy()
        self.created_owner = False
        self.logged_in = False
        self.finished = False

    def wait_until_available(self, timeout: int) -> dict[str, bool]:
        """Return the configured status immediately."""
        assert timeout > 0
        return self.status.copy()

    def create_owner(self, credentials: dict[str, str]) -> str:
        """Record owner creation."""
        assert credentials["password"]
        self.created_owner = True
        self.status["user"] = True
        return "owner-code"

    def login(self, credentials: dict[str, str]) -> str:
        """Record recovery login."""
        assert credentials["username"] == "developer"
        self.logged_in = True
        return "login-code"

    def exchange_auth_code(self, auth_code: str) -> str:
        """Return a token for either supported flow."""
        assert auth_code in {"owner-code", "login-code"}
        return "access-token"

    def finish_steps(self, status: dict[str, bool], access_token: str) -> None:
        """Mark every remaining step complete."""
        assert access_token == "access-token"
        assert status
        self.finished = True
        self.status = dict.fromkeys(onboarding.ONBOARDING_STEPS, True)

    def onboarding_status(self) -> dict[str, bool]:
        """Return the latest fake status."""
        return self.status.copy()


def test_first_run_generates_credentials_and_completes_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh instance creates an owner and finishes onboarding."""
    monkeypatch.delenv("HOME_ASSISTANT_DEV_PASSWORD", raising=False)
    credentials_path = tmp_path / ".dev-onboarding.json"
    client = FakeClient(dict.fromkeys(onboarding.ONBOARDING_STEPS, False))

    onboarding.run_onboarding(client, credentials_path)

    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    assert credentials["username"] == "developer"
    assert len(credentials["password"]) >= 24
    assert stat.S_IMODE(credentials_path.stat().st_mode) == 0o600
    assert client.created_owner
    assert client.finished


def test_completed_onboarding_is_idempotent(tmp_path: Path) -> None:
    """A completed instance exits without generating new credentials."""
    credentials_path = tmp_path / ".dev-onboarding.json"
    client = FakeClient(dict.fromkeys(onboarding.ONBOARDING_STEPS, True))

    onboarding.run_onboarding(client, credentials_path)

    assert not credentials_path.exists()
    assert not client.created_owner
    assert not client.logged_in
    assert not client.finished


def test_partial_run_uses_saved_credentials(tmp_path: Path) -> None:
    """An interrupted run logs in with its existing generated account."""
    credentials_path = tmp_path / ".dev-onboarding.json"
    onboarding.save_credentials(
        credentials_path,
        {
            "name": "E-Redes Developer",
            "username": "developer",
            "password": "saved-password",
            "language": "en",
        },
    )
    client = FakeClient(
        {
            "user": True,
            "core_config": False,
            "analytics": False,
            "integration": False,
        }
    )

    onboarding.run_onboarding(client, credentials_path)

    assert client.logged_in
    assert not client.created_owner
    assert client.finished


def test_partial_run_without_credentials_fails(tmp_path: Path) -> None:
    """Never guess credentials for an owner that already exists."""
    client = FakeClient(
        {
            "user": True,
            "core_config": False,
            "analytics": False,
            "integration": False,
        }
    )

    with pytest.raises(RuntimeError, match="credentials file is missing"):
        onboarding.run_onboarding(client, tmp_path / "missing.json")


def test_missing_onboarding_endpoint_means_restart_is_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fully onboarded restart is detected through available auth providers."""
    client = onboarding.HomeAssistantClient(
        "http://homeassistant:8123",
        "http://localhost:8123/",
        "http://localhost:8123/",
    )

    def request_json(method: str, path: str) -> object:
        assert method == "GET"
        if path == "/api/onboarding":
            raise onboarding.HomeAssistantRequestError("not found", status_code=404)
        assert path == "/auth/providers"
        return {"providers": [{"type": "homeassistant"}]}

    monkeypatch.setattr(client, "request_json", request_json)
    status = client.wait_until_available(1)

    assert status == dict.fromkeys(onboarding.ONBOARDING_STEPS, True)
