"""Config flow for the E-Redes Smart Metering Plus integration."""

from __future__ import annotations

import logging
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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EredesSmartMeteringPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for E-Redes Smart Metering Plus."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._webhook_id: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return EredesSmartMeteringPlusOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - show webhook info directly."""
        # Generate webhook ID only once
        if self._webhook_id is None:
            self._webhook_id = webhook.async_generate_id()
            # Set unique ID to prevent duplicates
            await self.async_set_unique_id(self._webhook_id)
            self._abort_if_unique_id_configured()

        if user_input is not None:
            # User confirmed, create the entry
            return self.async_create_entry(
                title="E-Redes Smart Metering Plus",
                data={
                    "webhook_id": self._webhook_id,
                },
            )

        # Generate the preview URL for display (this will be recreated during setup)
        preview_url = webhook.async_generate_url(self.hass, self._webhook_id)

        # Show webhook information with empty schema (no input fields)
        # The webhook URL will be displayed in the description
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),  # Empty schema = no input fields
            description_placeholders={"webhook_url": preview_url},
        )


class EredesSmartMeteringPlusOptionsFlow(OptionsFlow):
    """Handle options flow for E-Redes Smart Metering Plus."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options for the integration."""
        # Get the webhook URL from config entry data
        webhook_id = self.config_entry.data.get("webhook_id")
        if webhook_id:
            webhook_url = webhook.async_generate_url(self.hass, webhook_id)
        else:
            webhook_url = "URL not available"

        # Show the webhook URL as a menu with no options (only close button)
        return self.async_show_menu(
            step_id="init",
            menu_options=[],  # Empty list = only close button
            description_placeholders={"webhook_url": webhook_url},
        )
