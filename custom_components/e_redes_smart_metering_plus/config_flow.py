"""Config flow for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import CONF_CPES, DOMAIN, WEBHOOK_ID
from .webhook import async_get_active_webhook_url

_CPE_PATTERN = re.compile(r"^PT[A-Z0-9]{18}$")
_CONF_METER = "meter"


def _normalize_cpes(values: list[str]) -> list[str]:
    """Normalize and validate a non-empty collection of CPE identifiers."""
    cpes = sorted({value.strip().upper() for value in values if value.strip()})
    if not cpes or any(not _CPE_PATTERN.fullmatch(cpe) for cpe in cpes):
        raise vol.Invalid("invalid CPE")
    return cpes


def _cpe_schema(default: list[str] | None = None) -> vol.Schema:
    """Return the schema used to configure one or more CPE identifiers."""
    marker = (
        vol.Required(CONF_CPES, default=default) if default else vol.Required(CONF_CPES)
    )
    return vol.Schema(
        {
            marker: TextSelector(TextSelectorConfig(multiple=True)),
        }
    )


class EredesSmartMeteringPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for E-Redes Smart Metering Plus."""

    VERSION = 6

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return EredesSmartMeteringPlusOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - show webhook info directly."""
        # Check if already configured (single config entry)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            try:
                cpes = _normalize_cpes(user_input[CONF_CPES])
            except (KeyError, TypeError, vol.Invalid):
                return self.async_show_form(
                    step_id="user",
                    data_schema=_cpe_schema(user_input.get(CONF_CPES)),
                    errors={CONF_CPES: "invalid_cpe"},
                    description_placeholders={
                        "webhook_url": webhook.async_generate_url(self.hass, WEBHOOK_ID)
                    },
                )

            return self.async_create_entry(
                title="E-Redes Smart Metering Plus",
                data={
                    "webhook_id": WEBHOOK_ID,
                    CONF_CPES: cpes,
                },
            )

        # Generate the preview URL for display (this will be recreated during setup)
        preview_url = webhook.async_generate_url(self.hass, WEBHOOK_ID)

        # Show webhook information with empty schema (no input fields)
        # The webhook URL will be displayed in the description
        return self.async_show_form(
            step_id="user",
            data_schema=_cpe_schema(),
            description_placeholders={"webhook_url": preview_url},
        )


class EredesSmartMeteringPlusOptionsFlow(OptionsFlow):
    """Handle options flow for E-Redes Smart Metering Plus."""

    _reset_cpe: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the available integration management actions."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["manage_cpes", "reset_meter"],
        )

    async def async_step_manage_cpes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage configured CPEs and display the active webhook URL."""
        if user_input is not None:
            try:
                cpes = _normalize_cpes(user_input[CONF_CPES])
            except (KeyError, TypeError, vol.Invalid):
                webhook_url = await async_get_active_webhook_url(
                    self.hass, self.config_entry
                )
                return self.async_show_form(
                    step_id="manage_cpes",
                    data_schema=_cpe_schema(user_input.get(CONF_CPES)),
                    errors={CONF_CPES: "invalid_cpe"},
                    description_placeholders={"webhook_url": webhook_url},
                )

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_CPES: cpes},
            )
            return self.async_create_entry(data={})

        webhook_url = await async_get_active_webhook_url(self.hass, self.config_entry)
        return self.async_show_form(
            step_id="manage_cpes",
            data_schema=_cpe_schema(list(self.config_entry.data.get(CONF_CPES, ()))),
            description_placeholders={"webhook_url": webhook_url},
        )

    async def async_step_reset_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a discovered meter to reset."""
        devices = {
            identifier: device
            for device in dr.async_entries_for_config_entry(
                dr.async_get(self.hass), self.config_entry.entry_id
            )
            for domain, identifier in device.identifiers
            if domain == DOMAIN
        }
        if not devices:
            return self.async_abort(reason="no_meters")

        if user_input is not None:
            cpe = user_input.get(_CONF_METER)
            if cpe not in devices:
                return self.async_abort(reason="meter_not_found")
            self._reset_cpe = cpe
            return await self.async_step_confirm_reset_meter()

        options = [
            SelectOptionDict(
                value=cpe,
                label=device.name_by_user or device.name or cpe,
            )
            for cpe, device in sorted(devices.items())
        ]
        return self.async_show_form(
            step_id="reset_meter",
            data_schema=vol.Schema(
                {
                    vol.Required(_CONF_METER): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_confirm_reset_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm resetting a meter's entities and names."""
        if self._reset_cpe is None:
            return self.async_abort(reason="meter_not_found")

        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, self._reset_cpe)}
        )
        if device is None or self.config_entry.entry_id not in device.config_entries:
            return self.async_abort(reason="meter_not_found")

        if user_input is not None:
            from . import async_reset_meter

            if not await async_reset_meter(
                self.hass,
                self.config_entry,
                device,
                reset_entity_names=True,
            ):
                return self.async_abort(reason="meter_not_found")
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm_reset_meter",
            data_schema=vol.Schema({}),
            description_placeholders={
                "meter": device.name_by_user or device.name or self._reset_cpe
            },
        )
