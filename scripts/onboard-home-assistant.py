#!/usr/bin/env python3
# ruff: noqa: T201
"""Complete Home Assistant development onboarding without browser input."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_CREDENTIALS_FILE = "/config/.dev-onboarding.json"
ONBOARDING_STEPS = ("user", "core_config", "analytics", "integration")


class HomeAssistantRequestError(RuntimeError):
    """Represent an unsuccessful Home Assistant API request."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the request error."""
        super().__init__(message)
        self.status_code = status_code


class HomeAssistantClient:
    """Small client for the Home Assistant 2026.1 onboarding API."""

    def __init__(self, base_url: str, client_id: str, redirect_uri: str) -> None:
        """Initialize the client."""
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.redirect_uri = redirect_uri

    def request_json(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        *,
        access_token: str | None = None,
        form: bool = False,
    ) -> Any:
        """Send a JSON or form request and return decoded JSON."""
        headers = {"Accept": "application/json"}
        body: bytes | None = None
        if data is not None:
            if form:
                body = urlencode(data).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                body = json.dumps(data).encode()
                headers["Content-Type"] = "application/json"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        request = Request(
            f"{self.base_url}{path}", data=body, headers=headers, method=method
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310
                response_body = response.read()
        except HTTPError as err:
            error_body = err.read().decode(errors="replace")
            raise HomeAssistantRequestError(
                f"{method} {path} returned HTTP {err.code}: {error_body}",
                status_code=err.code,
            ) from err
        except URLError as err:
            raise HomeAssistantRequestError(
                f"{method} {path} could not connect: {err.reason}"
            ) from err

        return json.loads(response_body) if response_body else {}

    def onboarding_status(self) -> dict[str, bool]:
        """Return completion state for every onboarding step."""
        response = self.request_json("GET", "/api/onboarding")
        if not isinstance(response, list):
            raise HomeAssistantRequestError("Unexpected onboarding status response")
        return {
            item["step"]: bool(item["done"])
            for item in response
            if isinstance(item, dict) and "step" in item and "done" in item
        }

    def wait_until_available(self, timeout: int) -> dict[str, bool]:
        """Wait for Home Assistant's onboarding API."""
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                return self.onboarding_status()
            except HomeAssistantRequestError as err:
                last_error = err
                if err.status_code == 404:
                    try:
                        auth_response = self.request_json("GET", "/auth/providers")
                    except HomeAssistantRequestError as auth_error:
                        last_error = auth_error
                    else:
                        if isinstance(auth_response, dict) and isinstance(
                            auth_response.get("providers"), list
                        ):
                            return dict.fromkeys(ONBOARDING_STEPS, True)
                time.sleep(2)
        raise HomeAssistantRequestError(
            f"Home Assistant did not become ready within {timeout} seconds: {last_error}"
        )

    def create_owner(self, credentials: dict[str, str]) -> str:
        """Create the initial owner and return an authorization code."""
        response = self.request_json(
            "POST",
            "/api/onboarding/users",
            {
                "name": credentials["name"],
                "username": credentials["username"],
                "password": credentials["password"],
                "client_id": self.client_id,
                "language": credentials["language"],
            },
        )
        return _required_string(response, "auth_code", "owner creation")

    def login(self, credentials: dict[str, str]) -> str:
        """Authenticate an existing development owner and return an auth code."""
        flow = self.request_json(
            "POST",
            "/auth/login_flow",
            {
                "client_id": self.client_id,
                "handler": ["homeassistant", None],
                "redirect_uri": self.redirect_uri,
                "type": "authorize",
            },
        )
        flow_id = _required_string(flow, "flow_id", "login flow creation")
        result = self.request_json(
            "POST",
            f"/auth/login_flow/{flow_id}",
            {
                "client_id": self.client_id,
                "username": credentials["username"],
                "password": credentials["password"],
            },
        )
        if result.get("type") != "create_entry":
            raise HomeAssistantRequestError(
                f"Development owner login did not complete: {result}"
            )
        return _required_string(result, "result", "development owner login")

    def exchange_auth_code(self, auth_code: str) -> str:
        """Exchange an authorization code for a short-lived access token."""
        response = self.request_json(
            "POST",
            "/auth/token",
            {
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": self.client_id,
            },
            form=True,
        )
        return _required_string(response, "access_token", "token exchange")

    def finish_steps(self, status: dict[str, bool], access_token: str) -> None:
        """Complete the authenticated onboarding steps."""
        if not status.get("core_config", False):
            self.request_json(
                "POST", "/api/onboarding/core_config", {}, access_token=access_token
            )
        if not status.get("analytics", False):
            self.request_json(
                "POST", "/api/onboarding/analytics", {}, access_token=access_token
            )
        if not status.get("integration", False):
            self.request_json(
                "POST",
                "/api/onboarding/integration",
                {"client_id": self.client_id, "redirect_uri": self.redirect_uri},
                access_token=access_token,
            )


def _required_string(response: Any, key: str, operation: str) -> str:
    """Extract a required non-empty string from an API response."""
    if isinstance(response, dict) and isinstance(response.get(key), str):
        value = response[key]
        if value:
            return value
    raise HomeAssistantRequestError(
        f"Home Assistant returned an invalid response during {operation}: {response}"
    )


def load_credentials(path: Path) -> dict[str, str] | None:
    """Load previously generated development credentials."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ("name", "username", "password", "language")
    if not isinstance(data, dict) or any(
        not isinstance(data.get(key), str) or not data[key] for key in required
    ):
        raise RuntimeError(f"Invalid development credentials file: {path}")
    return {key: data[key] for key in required}


def create_credentials() -> dict[str, str]:
    """Build credentials from optional environment overrides."""
    return {
        "name": os.environ.get("HOME_ASSISTANT_DEV_NAME", "E-Redes Developer"),
        "username": os.environ.get("HOME_ASSISTANT_DEV_USERNAME", "developer"),
        "password": os.environ.get("HOME_ASSISTANT_DEV_PASSWORD")
        or secrets.token_urlsafe(24),
        "language": os.environ.get("HOME_ASSISTANT_DEV_LANGUAGE", "en"),
    }


def save_credentials(path: Path, credentials: dict[str, str]) -> None:
    """Atomically store development-only credentials with restrictive permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(credentials, indent=2) + "\n", encoding="utf-8"
    )
    os.chmod(temporary_path, 0o600)
    temporary_path.replace(path)


def show_credentials(path: Path) -> int:
    """Print development credentials on explicit request."""
    credentials = load_credentials(path)
    if credentials is None:
        print(f"No development credentials found at {path}", file=sys.stderr)
        return 1
    print(f"Username: {credentials['username']}")
    print(f"Password: {credentials['password']}")
    return 0


def run_onboarding(client: HomeAssistantClient, credentials_path: Path) -> None:
    """Complete onboarding idempotently."""
    timeout = int(os.environ.get("HOME_ASSISTANT_STARTUP_TIMEOUT", "180"))
    status = client.wait_until_available(timeout)
    if all(status.get(step, False) for step in ONBOARDING_STEPS):
        print("Home Assistant development onboarding is already complete.")
        return

    credentials = load_credentials(credentials_path)
    if not status.get("user", False):
        credentials = credentials or create_credentials()
        save_credentials(credentials_path, credentials)
        auth_code = client.create_owner(credentials)
    else:
        if credentials is None:
            raise RuntimeError(
                "Home Assistant already has an owner, but the development credentials "
                f"file is missing: {credentials_path}"
            )
        auth_code = client.login(credentials)

    access_token = client.exchange_auth_code(auth_code)
    client.finish_steps(status, access_token)
    final_status = client.onboarding_status()
    incomplete = [
        step for step in ONBOARDING_STEPS if not final_status.get(step, False)
    ]
    if incomplete:
        raise RuntimeError(f"Onboarding did not complete these steps: {incomplete}")

    print("Home Assistant development onboarding completed successfully.")
    print(f"Development username: {credentials['username']}")
    print(f"Credentials file: {credentials_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-credentials", action="store_true")
    parser.add_argument(
        "--credentials-file",
        type=Path,
        default=Path(
            os.environ.get("HOME_ASSISTANT_CREDENTIALS_FILE", DEFAULT_CREDENTIALS_FILE)
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Run the requested command."""
    args = parse_args()
    if args.show_credentials:
        return show_credentials(args.credentials_file)

    client = HomeAssistantClient(
        os.environ.get("HOME_ASSISTANT_URL", "http://homeassistant:8123"),
        os.environ.get("HOME_ASSISTANT_CLIENT_ID", "http://localhost:8123/"),
        os.environ.get("HOME_ASSISTANT_REDIRECT_URI", "http://localhost:8123/"),
    )
    try:
        run_onboarding(client, args.credentials_file)
    except (HomeAssistantRequestError, OSError, RuntimeError, ValueError) as err:
        print(f"Home Assistant development onboarding failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
