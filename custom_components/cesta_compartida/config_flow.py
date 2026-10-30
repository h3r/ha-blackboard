"""Config flow for Cesta Compartida integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DEFAULT_LIST, CONF_GEMINI_API_KEY, DEFAULT_LIST, DOMAIN, TITLE

_LOGGER = logging.getLogger(__name__)


class CestaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cesta Compartida."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title=TITLE, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_DEFAULT_LIST, default=DEFAULT_LIST): str,
                vol.Optional(CONF_GEMINI_API_KEY, default=""): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get options flow."""
        return CestaOptionsFlowHandler(config_entry)


class CestaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Cesta Compartida."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_default_list = self.config_entry.options.get(
            CONF_DEFAULT_LIST,
            self.config_entry.data.get(CONF_DEFAULT_LIST, DEFAULT_LIST),
        )
        current_api_key = self.config_entry.options.get(
            CONF_GEMINI_API_KEY,
            self.config_entry.data.get(CONF_GEMINI_API_KEY, ""),
        )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_DEFAULT_LIST, default=current_default_list): str,
                vol.Optional(CONF_GEMINI_API_KEY, default=current_api_key): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
