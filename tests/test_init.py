"""Tests for E-Redes Smart Metering Plus setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.e_redes_smart_metering_plus as integration
from custom_components.e_redes_smart_metering_plus import (
    async_migrate_entry,
    async_remove_config_entry_device,
    async_reset_meter,
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
from custom_components.e_redes_smart_metering_plus.webhook import handle_webhook
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


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


async def test_migration_rejects_future_config_entry_version(
    hass: HomeAssistant,
) -> None:
    """A future config entry must not be downgraded or changed."""
    original_data = {CONF_CPES: ["PT000000000000000001"], "future_key": "value"}
    entry = MockConfigEntry(domain=DOMAIN, data=original_data, version=7)
    entry.add_to_hass(hass)

    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 7
    assert entry.data == original_data


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
        assert migrated.unique_id == (f"{DOMAIN}_PT000000000000000001_{new_key}")


async def test_migration_skips_conflicting_contracted_power_unique_id(
    hass: HomeAssistant,
) -> None:
    """A conflicting renamed unique ID must not prevent integration setup."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CPES: []}, version=5)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    cpe = "PT000000000000000001"
    legacy = registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        config_entry=entry,
        unique_id=f"{DOMAIN}_{cpe}_breaker_load",
        suggested_object_id="legacy_breaker_load",
    )
    current = registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        config_entry=entry,
        unique_id=f"{DOMAIN}_{cpe}_contracted_power_usage",
        suggested_object_id="current_contracted_power_usage",
    )

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 6
    assert registry.async_get(legacy.entity_id).unique_id == legacy.unique_id
    assert registry.async_get(current.entity_id).unique_id == current.unique_id


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


async def test_remove_device_resets_meter_and_preserves_configuration(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deleting a meter must preserve its CPE and stable webhook configuration."""
    cpe = "PT000000000000000001"
    other_cpe = "PT000000000000000002"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"webhook_id": WEBHOOK_ID, CONF_CPES: [cpe, other_cpe]},
    )
    entry.add_to_hass(hass)
    entry.runtime_data = ERedesRuntimeData(
        allowed_cpes=frozenset({cpe, other_cpe}),
        sensor_entities={f"{cpe}_power": Mock(), f"{other_cpe}_power": Mock()},
        select_entities={cpe: Mock(), other_cpe: Mock()},
        binary_sensor_entities={f"{cpe}_warning": Mock()},
        last_source_timestamps={cpe: Mock()},
        latest_measurement_sensor_keys={cpe: frozenset({"power"})},
        webhook_locks={cpe: Mock()},
        payload_fields={cpe: frozenset({"cpe", "power"})},
    )

    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, cpe)},
    )
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        config_entry=entry,
        device_id=device_entry.id,
        unique_id=f"{DOMAIN}_{cpe}_power",
    )
    reload_entry = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload_entry)

    assert await async_remove_config_entry_device(hass, entry, device_entry)

    assert entry.data == {"webhook_id": WEBHOOK_ID, CONF_CPES: [cpe, other_cpe]}
    assert device_registry.async_get(device_entry.id) is not None
    assert entity_registry.async_get(entity_entry.entity_id) is None
    assert set(entry.runtime_data.sensor_entities) == {f"{other_cpe}_power"}
    assert set(entry.runtime_data.select_entities) == {other_cpe}
    assert not entry.runtime_data.binary_sensor_entities
    assert cpe in entry.runtime_data.last_source_timestamps
    assert cpe not in entry.runtime_data.latest_measurement_sensor_keys
    assert cpe not in entry.runtime_data.webhook_locks
    assert cpe not in entry.runtime_data.payload_fields
    reload_entry.assert_awaited_once_with(entry.entry_id)

    device_registry.async_update_device(
        device_entry.id,
        remove_config_entry_id=entry.entry_id,
    )
    assert device_registry.async_get(device_entry.id) is None


async def test_remove_device_rejects_unconfigured_meter(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A device outside the configured CPE allowlist must not be removed."""
    configured_cpe = "PT000000000000000001"
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CPES: [configured_cpe]})
    entry.add_to_hass(hass)
    entry.runtime_data = ERedesRuntimeData(allowed_cpes=frozenset({configured_cpe}))
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "PT000000000000000002")},
    )
    reload_entry = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload_entry)

    assert not await async_remove_config_entry_device(hass, entry, device_entry)
    assert device_registry.async_get(device_entry.id) is not None
    reload_entry.assert_not_awaited()


async def test_deleted_meter_is_recreated_from_next_payload(
    hass: HomeAssistant, config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The next payload must recreate a deleted meter with a fresh field set."""
    cpe = "CPE001"
    initial_request = Mock()
    initial_request.json = AsyncMock(
        return_value={
            "cpe": cpe,
            "SourceTimestamp": "2026-09-04 10:00:00",
            "activeEnergyImport": 12345,
        }
    )
    response = await handle_webhook(hass, WEBHOOK_ID, initial_request, config_entry)
    assert response.status == 200
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    device_entry = device_registry.async_get_device(identifiers={(DOMAIN, cpe)})
    assert device_entry is not None
    old_unique_id = f"{DOMAIN}_{cpe}_active_energy_import"
    old_entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, old_unique_id)
    assert old_entity_id is not None
    custom_entity_id = "sensor.preserved_custom_energy"
    entity_registry.async_update_entity(
        old_entity_id,
        new_entity_id=custom_entity_id,
    )

    webhook_had_watermark: list[bool] = []
    original_setup_webhook = integration.async_setup_webhook

    async def assert_watermark_before_webhook(hass_instance, entry):
        webhook_had_watermark.append(cpe in entry.runtime_data.last_source_timestamps)
        return await original_setup_webhook(hass_instance, entry)

    monkeypatch.setattr(
        integration,
        "async_setup_webhook",
        assert_watermark_before_webhook,
    )

    original_data = dict(config_entry.data)
    original_webhook_url = config_entry.runtime_data.webhook_url
    assert await async_remove_config_entry_device(hass, config_entry, device_entry)
    await hass.async_block_till_done()

    assert device_registry.async_get(device_entry.id) is not None
    device_registry.async_update_device(
        device_entry.id,
        remove_config_entry_id=config_entry.entry_id,
    )

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.data == original_data
    assert config_entry.runtime_data.webhook_url == original_webhook_url
    assert device_registry.async_get(device_entry.id) is None
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, old_unique_id) is None
    assert cpe in config_entry.runtime_data.last_source_timestamps
    assert webhook_had_watermark == [True]

    stale_request = Mock()
    stale_request.json = AsyncMock(
        return_value={
            "cpe": cpe,
            "SourceTimestamp": "2026-09-04 09:59:59",
            "voltageL1": 229.0,
        }
    )
    response = await handle_webhook(hass, WEBHOOK_ID, stale_request, config_entry)
    assert response.status == 200
    await hass.async_block_till_done()
    assert (
        entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_{cpe}_voltage_l1"
        )
        is None
    )

    next_request = Mock()
    next_request.json = AsyncMock(
        return_value={
            "cpe": cpe,
            "SourceTimestamp": "2026-09-04 10:00:01",
            "voltageL1": 231.5,
        }
    )
    response = await handle_webhook(hass, WEBHOOK_ID, next_request, config_entry)
    assert response.status == 200
    await hass.async_block_till_done()

    recreated_device = device_registry.async_get_device(identifiers={(DOMAIN, cpe)})
    assert recreated_device is not None
    assert (
        entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_{cpe}_voltage_l1"
        )
        is not None
    )
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, old_unique_id) is None

    restored_request = Mock()
    restored_request.json = AsyncMock(
        return_value={
            "cpe": cpe,
            "SourceTimestamp": "2026-09-04 10:00:02",
            "activeEnergyImport": 12346,
        }
    )
    response = await handle_webhook(hass, WEBHOOK_ID, restored_request, config_entry)
    assert response.status == 200
    await hass.async_block_till_done()
    assert (
        entity_registry.async_get_entity_id("sensor", DOMAIN, old_unique_id)
        == custom_entity_id
    )


async def test_full_meter_reset_restores_generated_entity_name_and_id(
    hass: HomeAssistant, config_entry
) -> None:
    """The confirmed reset must discard customized entity names and IDs."""
    cpe = "CPE001"
    request = Mock()
    request.json = AsyncMock(return_value={"cpe": cpe, "activeEnergyImport": 12345})
    response = await handle_webhook(hass, WEBHOOK_ID, request, config_entry)
    assert response.status == 200
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    device_entry = device_registry.async_get_device(identifiers={(DOMAIN, cpe)})
    assert device_entry is not None
    unique_id = f"{DOMAIN}_{cpe}_active_energy_import"
    original_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, unique_id
    )
    assert original_entity_id is not None
    custom_entity_id = "sensor.my_custom_energy_name"
    entity_registry.async_update_entity(
        original_entity_id,
        name="My custom energy name",
        new_entity_id=custom_entity_id,
    )

    assert await async_reset_meter(
        hass,
        config_entry,
        device_entry,
        reset_entity_names=True,
    )
    await hass.async_block_till_done()
    assert entity_registry.async_get(custom_entity_id) is None

    recreated_request = Mock()
    recreated_request.json = AsyncMock(
        return_value={"cpe": cpe, "activeEnergyImport": 12346}
    )
    response = await handle_webhook(hass, WEBHOOK_ID, recreated_request, config_entry)
    assert response.status == 200
    await hass.async_block_till_done()

    recreated_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, unique_id
    )
    assert recreated_entity_id == original_entity_id
    recreated_entry = entity_registry.async_get(recreated_entity_id)
    assert recreated_entry is not None
    assert recreated_entry.name is None
