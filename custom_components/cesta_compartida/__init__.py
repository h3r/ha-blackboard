"""The Cesta Compartida integration."""

from __future__ import annotations

import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import (
    CestaListsView,
    CestaProductDetailView,
    CestaProductsView,
    CestaVisionView,
)
from .const import (
    CONF_GEMINI_API_KEY,
    DOMAIN,
    FRONTEND_STATIC_PATH,
    FRONTEND_URL_PATH,
    TITLE,
)
from .storage import CestaStorage

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.TODO]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cesta Compartida from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    storage = CestaStorage(hass)
    await storage.async_load()

    api_key = entry.options.get(
        CONF_GEMINI_API_KEY, entry.data.get(CONF_GEMINI_API_KEY, "")
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "storage": storage,
        "entry": entry,
    }

    # Register API views
    hass.http.register_view(CestaListsView(storage))
    hass.http.register_view(CestaProductsView(storage))
    hass.http.register_view(CestaProductDetailView(hass, storage))
    hass.http.register_view(CestaVisionView(hass, api_key))

    # Register frontend static path
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    if os.path.isdir(frontend_dir):
        await hass.http.async_register_static_paths(
            [
                hass.http.create_static_path_config(
                    FRONTEND_STATIC_PATH,
                    frontend_dir,
                    cache_headers=False,
                )
            ]
        )

        # Register custom sidebar panel
        hass.components.frontend.async_register_built_in_panel(
            component_name="iframe",
            sidebar_title=TITLE,
            sidebar_icon="mdi:cart-variant",
            frontend_url_path=FRONTEND_URL_PATH,
            config={"url": f"{FRONTEND_STATIC_PATH}/index.html"},
            require_admin=False,
        )

    # Set up To-do platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.components.frontend.async_remove_panel(FRONTEND_URL_PATH)

    return unload_ok
