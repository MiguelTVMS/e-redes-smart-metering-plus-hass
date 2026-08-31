"""Tests for Home Assistant Cloud webhook handling."""

from __future__ import annotations

import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import homeassistant.components as homeassistant_components
from homeassistant.core import HomeAssistant

from custom_components.e_redes_smart_metering_plus.const import DOMAIN, WEBHOOK_ID
from custom_components.e_redes_smart_metering_plus import webhook as webhook_module
from custom_components.e_redes_smart_metering_plus.webhook import (
    _async_create_cloudhook,
    _async_refresh_cloudhook,
    async_setup_webhook,
)


async def test_cloudhook_waits_for_cloud_connection(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Logged-in but disconnected Cloud must not attempt cloudhook creation."""
    get_or_create = AsyncMock(return_value="https://hooks.nabu.casa/test")
    fake_cloud = SimpleNamespace(
        async_is_logged_in=lambda hass_instance: True,
        async_is_connected=lambda hass_instance: False,
        async_get_or_create_cloudhook=get_or_create,
    )
    monkeypatch.setitem(sys.modules, "homeassistant.components.cloud", fake_cloud)
    monkeypatch.setattr(
        homeassistant_components, "cloud", fake_cloud, raising=False
    )

    assert await _async_create_cloudhook(hass, WEBHOOK_ID) is None
    get_or_create.assert_not_awaited()

    fake_cloud.async_is_connected = lambda hass_instance: True

    assert await _async_create_cloudhook(hass, WEBHOOK_ID) == (
        "https://hooks.nabu.casa/test"
    )
    get_or_create.assert_awaited_once_with(hass, WEBHOOK_ID)


async def test_cloudhook_failure_log_is_not_empty(
    hass: HomeAssistant,
    config_entry,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unexpected cloudhook failures must include an exception type and detail."""

    class EmptyCloudError(Exception):
        """Cloud error without a message."""

    monkeypatch.setattr(
        webhook_module,
        "_async_create_cloudhook",
        AsyncMock(side_effect=EmptyCloudError),
    )

    with caplog.at_level(logging.WARNING):
        assert (
            await _async_refresh_cloudhook(hass, config_entry, WEBHOOK_ID) is None
        )

    assert "Failed to create cloud webhook (EmptyCloudError): no details" in caplog.text


async def test_cloud_connection_refreshes_stored_webhook_url(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later Cloud connection must replace the temporary local webhook URL."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="E-Redes Smart Metering Plus",
        data={"webhook_id": WEBHOOK_ID},
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}

    refresh_cloudhook = AsyncMock(return_value=None)
    connection_callbacks = []

    monkeypatch.setattr(webhook_module, "_async_refresh_cloudhook", refresh_cloudhook)
    monkeypatch.setattr(webhook_module.webhook, "async_register", lambda *args: None)
    monkeypatch.setattr(
        webhook_module.webhook,
        "async_generate_url",
        lambda hass_instance, webhook_id: f"/api/webhook/{webhook_id}",
    )
    monkeypatch.setattr(
        webhook_module,
        "_listen_for_cloud_connection",
        lambda hass_instance, target: connection_callbacks.append(target)
        or (lambda: None),
    )

    await async_setup_webhook(hass, entry)

    assert len(connection_callbacks) == 1
    refresh_cloudhook.reset_mock()

    await connection_callbacks[0]("cloud_connected")

    refresh_cloudhook.assert_awaited_once_with(hass, entry, WEBHOOK_ID)
