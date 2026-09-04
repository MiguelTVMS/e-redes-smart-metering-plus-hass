"""Constants for the E-Redes Smart Metering Plus integration."""

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)

DOMAIN = "e_redes_smart_metering_plus"

# Fixed webhook ID - creates a predictable URL path
WEBHOOK_ID = DOMAIN

# Webhook constants
WEBHOOK_PATH = f"/api/webhook/{WEBHOOK_ID}"

CONF_CPES = "cpes"
CONF_WEBHOOK_AUTH_ENABLED = "webhook_auth_enabled"
CONF_WEBHOOK_AUTH_TOKEN = "webhook_auth_token"

# Device info
MANUFACTURER = "E-Redes"
MODEL = "Smart Metering Plus"


@dataclass(frozen=True, kw_only=True)
class ERedesSensorEntityDescription(SensorEntityDescription):
    """Describe a sensor supplied directly by E-REDES."""


@dataclass(frozen=True, kw_only=True)
class ERedesCalculatedSensorEntityDescription(SensorEntityDescription):
    """Describe a locally calculated sensor."""

    calculation: str
    source_sensors: tuple[str, ...]
    requires_select_entity: str | None = None


INSTANTANEOUS_POWER_IMPORT = ERedesSensorEntityDescription(
    key="instantaneous_active_power_import",
    translation_key="instantaneous_active_power_import",
    native_unit_of_measurement=UnitOfPower.WATT,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:transmission-tower-import",
)
MAX_POWER_IMPORT = ERedesSensorEntityDescription(
    key="max_active_power_import",
    translation_key="max_active_power_import",
    native_unit_of_measurement=UnitOfPower.WATT,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:transmission-tower-import",
)
ACTIVE_ENERGY_IMPORT = ERedesSensorEntityDescription(
    key="active_energy_import",
    translation_key="active_energy_import",
    native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:counter",
)
INSTANTANEOUS_POWER_EXPORT = ERedesSensorEntityDescription(
    key="instantaneous_active_power_export",
    translation_key="instantaneous_active_power_export",
    native_unit_of_measurement=UnitOfPower.WATT,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:transmission-tower-export",
)
MAX_POWER_EXPORT = ERedesSensorEntityDescription(
    key="max_active_power_export",
    translation_key="max_active_power_export",
    native_unit_of_measurement=UnitOfPower.WATT,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:transmission-tower-export",
)
ACTIVE_ENERGY_EXPORT = ERedesSensorEntityDescription(
    key="active_energy_export",
    translation_key="active_energy_export",
    native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:counter",
)


def _voltage_description(phase: int) -> ERedesSensorEntityDescription:
    """Create a voltage description for one phase."""
    return ERedesSensorEntityDescription(
        key=f"voltage_l{phase}",
        translation_key=f"voltage_l{phase}",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
        suggested_display_precision=1,
    )


def _phase_power_description(
    direction: str, phase: int
) -> ERedesSensorEntityDescription:
    """Create a per-phase power description."""
    return ERedesSensorEntityDescription(
        key=f"instantaneous_active_power_{direction}_l{phase}",
        translation_key=f"instantaneous_active_power_{direction}_l{phase}",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon=f"mdi:transmission-tower-{direction}",
    )


VOLTAGE_L1 = _voltage_description(1)
VOLTAGE_L2 = _voltage_description(2)
VOLTAGE_L3 = _voltage_description(3)

SENSOR_MAPPING: dict[str, ERedesSensorEntityDescription] = {
    "instantaneousActivePowerImport": INSTANTANEOUS_POWER_IMPORT,
    "maxActivePowerImport": MAX_POWER_IMPORT,
    # Legacy field observed before E-REDES published its current API examples.
    "maxActivePowerImportTotalLastAverage": MAX_POWER_IMPORT,
    "activeEnergyImport": ACTIVE_ENERGY_IMPORT,
    "instantaneousActivePowerExport": INSTANTANEOUS_POWER_EXPORT,
    "maxActivePowerExport": MAX_POWER_EXPORT,
    "activeEnergyExport": ACTIVE_ENERGY_EXPORT,
    "voltageL1": VOLTAGE_L1,
    "voltageL2": VOLTAGE_L2,
    "voltageL3": VOLTAGE_L3,
}

for _phase in (1, 2, 3):
    SENSOR_MAPPING[f"instantaneousActivePowerImportL{_phase}"] = (
        _phase_power_description("import", _phase)
    )
    SENSOR_MAPPING[f"instantaneousActivePowerExportL{_phase}"] = (
        _phase_power_description("export", _phase)
    )

SENSOR_DESCRIPTIONS_BY_KEY = {
    description.key: description for description in SENSOR_MAPPING.values()
}

CALCULATED_SENSORS: dict[str, ERedesCalculatedSensorEntityDescription] = {
    "instantaneous_active_current_import": ERedesCalculatedSensorEntityDescription(
        key="instantaneous_active_current_import",
        translation_key="instantaneous_active_current_import",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-ac",
        suggested_display_precision=2,
        calculation="power_voltage",
        source_sensors=("instantaneous_active_power_import", "voltage_l1"),
    ),
    "contracted_power_usage": ERedesCalculatedSensorEntityDescription(
        key="contracted_power_usage",
        translation_key="contracted_power_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        calculation="contracted_power_usage",
        source_sensors=("instantaneous_active_power_import", "voltage_l1"),
        requires_select_entity="contracted_power",
    ),
}

for _phase in (1, 2, 3):
    CALCULATED_SENSORS[f"instantaneous_active_current_import_l{_phase}"] = (
        ERedesCalculatedSensorEntityDescription(
            key=f"instantaneous_active_current_import_l{_phase}",
            translation_key=f"instantaneous_active_current_import_l{_phase}",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:current-ac",
            suggested_display_precision=2,
            calculation="power_voltage",
            source_sensors=(
                f"instantaneous_active_power_import_l{_phase}",
                f"voltage_l{_phase}",
            ),
        )
    )

CALCULATED_SENSORS["contracted_power_usage_status"] = (
    ERedesCalculatedSensorEntityDescription(
        key="contracted_power_usage_status",
        translation_key="contracted_power_usage_status",
        device_class=SensorDeviceClass.ENUM,
        options=["normal", "warning", "critical", "exceeded"],
        calculation="contracted_power_usage_status",
        source_sensors=("contracted_power_usage",),
    )
)

CONTRACTED_POWER_USAGE_WARNING_PERCENT = 80.0
CONTRACTED_POWER_USAGE_CRITICAL_PERCENT = 95.0
CONTRACTED_POWER_USAGE_EXCEEDED_PERCENT = 100.0

SINGLE_PHASE_CONTRACTED_POWER_AMPS = {
    "1.15 kVA": 5.0,
    "2.30 kVA": 10.0,
    "3.45 kVA": 15.0,
    "4.60 kVA": 20.0,
    "5.75 kVA": 25.0,
    "6.90 kVA": 30.0,
    "10.35 kVA": 45.0,
    "13.80 kVA": 60.0,
}

THREE_PHASE_CONTRACTED_POWER_AMPS = {
    "3.45 kVA": 5.0,
    "6.90 kVA": 10.0,
    "10.35 kVA": 15.0,
    "13.80 kVA": 20.0,
    "17.25 kVA": 25.0,
    "20.70 kVA": 30.0,
    "27.60 kVA": 40.0,
    "34.50 kVA": 50.0,
    "41.40 kVA": 60.0,
}

CONTRACTED_POWER_OPTIONS = tuple(
    dict.fromkeys(
        (*SINGLE_PHASE_CONTRACTED_POWER_AMPS, *THREE_PHASE_CONTRACTED_POWER_AMPS)
    )
)

DIAGNOSTIC_SENSORS: dict[str, SensorEntityDescription] = {
    "last_update": SensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "update_interval": SensorEntityDescription(
        key="update_interval",
        translation_key="update_interval",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        suggested_display_precision=1,
    ),
}

TIMESTAMP_FIELDS = (
    "LocalTimestamp",
    "SourceTimestamp",
    "clock",
)

PAYLOAD_METADATA_FIELDS = {
    "cpe",
    *TIMESTAMP_FIELDS,
    "maxActivePowerImportTime",
    "maxActivePowerImportTotalTime",
    "maxActivePowerExportTime",
}

KNOWN_PAYLOAD_FIELDS = frozenset(SENSOR_MAPPING) | PAYLOAD_METADATA_FIELDS
