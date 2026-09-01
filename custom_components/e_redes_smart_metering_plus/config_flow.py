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
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import CONF_CPES, DOMAIN, WEBHOOK_ID
from .webhook import async_get_active_webhook_url

_CPE_PATTERN = re.compile(r"^PT[A-Z0-9]{18}$")


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

    VERSION = 3

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

    async def async_step_init(
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
                    step_id="init",
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
            step_id="init",
            data_schema=_cpe_schema(list(self.config_entry.data.get(CONF_CPES, ()))),
            description_placeholders={"webhook_url": webhook_url},
        )
