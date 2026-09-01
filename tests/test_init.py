"""Tests for E-Redes Smart Metering Plus setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.e_redes_smart_metering_plus import (
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.e_redes_smart_metering_plus.const import (
    CONF_CPES,
    DOMAIN,
    WEBHOOK_ID,
)
from custom_components.e_redes_smart_metering_plus.models import ERedesRuntimeData
from custom_components.e_redes_smart_metering_plus.sensor import (
    async_ensure_sensors_for_data,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


async def test_platforms_ready_before_webhook_registration(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Webhook setup must not run before dynamic entity callbacks are ready."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="E-Redes Smart Metering Plus",
        data={CONF_CPES: ["STARTUP_CPE"]},
        version=2,
    )
    entry.add_to_hass(hass)

    setup_order: list[str] = []
    added_entities: list[object] = []

    async def mock_forward_entry_setups(config_entry, platforms) -> None:
        setup_order.append("platforms")
        config_entry.runtime_data.sensor_add_entities = added_entities.extend

    async def mock_setup_webhook(hass_instance, config_entry) -> str:
        setup_order.append("webhook")
        await async_ensure_sensors_for_data(
            config_entry,
            "STARTUP_CPE",
            {"activeEnergyImport": 12345},
        )
        return DOMAIN

    monkeypatch.setattr(
        hass.config_entries,
        "async_forward_entry_setups",
        mock_forward_entry_setups,
    )
    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.async_setup_webhook",
        mock_setup_webhook,
    )

    assert await async_setup_entry(hass, entry)
    assert setup_order == ["platforms", "webhook"]
    assert len(added_entities) == 1


async def test_migration_adds_existing_device_cpes(hass: HomeAssistant) -> None:
    """Existing meter devices must become allowed CPEs during upgrade."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="E-Redes Smart Metering Plus",
        data={"webhook_id": WEBHOOK_ID},
        version=1,
    )
    entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "PT000000000000000001")},
    )
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "PT000000000000000002")},
    )
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        config_entry=entry,
        unique_id=(f"{DOMAIN}_PT000000000000000003_instantaneous_active_power_import"),
    )

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 6
    assert entry.data[CONF_CPES] == [
        "PT000000000000000001",
        "PT000000000000000002",
        "PT000000000000000003",
    ]


async def test_migration_disables_legacy_current_limit_number(
    hass: HomeAssistant,
) -> None:
    """The retired free-form current-limit number is disabled during migration."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CPES: []}, version=2)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    legacy = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        config_entry=entry,
        unique_id=f"{DOMAIN}_PT000000000000000001_breaker_limit",
    )

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 6
    migrated = registry.async_get(legacy.entity_id)
    assert migrated is not None
    assert migrated.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_migration_renames_contracted_power_entity_keys(
    hass: HomeAssistant,
) -> None:
    """Pre-release entity keys are migrated without creating duplicates."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CPES: []}, version=5)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old_keys = {
        "breaker_load_warning": "contracted_power_usage_warning",
        "breaker_load_critical": "contracted_power_usage_critical",
        "breaker_overload": "contracted_power_exceeded",
        "breaker_load": "contracted_power_usage",
        "breaker_load_status": "contracted_power_usage_status",
    }
    entities = []
    for old_key, new_key in old_keys.items():
        domain = (
            "binary_sensor"
            if old_key
            in {
                "breaker_load_warning",
                "breaker_load_critical",
                "breaker_overload",
            }
            else "sensor"
        )
        entity = registry.async_get_or_create(
            domain=domain,
            platform=DOMAIN,
            config_entry=entry,
            unique_id=f"{DOMAIN}_PT000000000000000001_{old_key}",
            suggested_object_id=f"meter_{old_key}",
        )
        entities.append((entity.entity_id, domain, new_key))

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 6
    for old_entity_id, domain, new_key in entities:
        assert registry.async_get(old_entity_id) is None
        migrated = registry.async_get(f"{domain}.meter_{new_key}")
        assert migrated is not None
        assert migrated.unique_id == (
            f"{DOMAIN}_PT000000000000000001_{new_key}"
        )


async def test_unload_does_not_remove_cloudhook(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reload must unregister locally without deleting the stable Cloudhook."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CPES: []}, version=2)
    entry.runtime_data = ERedesRuntimeData(allowed_cpes=frozenset())
    unload_webhook = Mock()
    remove_cloudhook = AsyncMock()
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.async_unload_webhook",
        unload_webhook,
    )
    monkeypatch.setattr(
        "custom_components.e_redes_smart_metering_plus.async_remove_cloudhook",
        remove_cloudhook,
    )

    assert await async_unload_entry(hass, entry)
    unload_webhook.assert_called_once_with(hass, WEBHOOK_ID)
    remove_cloudhook.assert_not_awaited()
