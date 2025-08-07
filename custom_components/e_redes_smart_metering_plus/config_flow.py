"""Config flow for E-Redes Smart Metering Plus integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import cloud, webhook
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for E-Redes Smart Metering Plus."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="E-Redes Smart Metering Plus",
                data=user_input,
            )

        # Check cloud status
        cloud_status = "Not connected"
        if cloud.async_is_logged_in(self.hass):
            cloud_status = "Connected (webhook will use secure cloud URL)"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "cloud_status": cloud_status,
            },
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from YAML configuration."""
        return await self.async_step_user(import_data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """E-Redes Smart Metering Plus config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize HACS options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        webhook_url = self.config_entry.data.get("webhook_url", "Not yet generated")
        
        # If webhook URL is not generated yet, try to get it from the running integration
        if webhook_url == "Not yet generated" or not webhook_url:
            if DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
                stored_url = self.hass.data[DOMAIN][self.config_entry.entry_id].get("webhook_url")
                if stored_url:
                    webhook_url = stored_url
        
        # Log for debugging
        _LOGGER.info("Options flow: webhook_url = %s", webhook_url)
        
        # If user clicked something, just close the dialog
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        
        # Create description with embedded webhook URL
        description = f"""Configure your E-Redes Smart Metering Plus integration.

**Webhook URL for E-Redes Configuration:**

{webhook_url}

Copy this URL and configure it in your E-Redes energy provider dashboard to start receiving energy data."""
        
        # Show the webhook URL information with a field containing the URL
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("webhook_url_info", default=webhook_url): str,
            }),
        )
