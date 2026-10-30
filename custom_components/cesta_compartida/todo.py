"""Todo platform integration for Cesta Compartida."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEFAULT_LIST, DEFAULT_LIST, DOMAIN
from .storage import CestaStorage

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Cesta Compartida Todo entity."""
    storage: CestaStorage = hass.data[DOMAIN][entry.entry_id]["storage"]
    default_list = entry.data.get(CONF_DEFAULT_LIST, DEFAULT_LIST)
    async_add_entities([CestaTodoListEntity(storage, default_list, entry.entry_id)])


class CestaTodoListEntity(TodoListEntity):
    """A Home Assistant TodoListEntity synced with Cesta Compartida."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, storage: CestaStorage, list_code: str, entry_id: str) -> None:
        """Initialize the todo entity."""
        self.storage = storage
        self.list_code = list_code
        self._attr_unique_id = f"{DOMAIN}_{list_code}_{entry_id}"
        self._attr_name = f"Cesta {list_code.capitalize()}"
        self._attr_icon = "mdi:cart-variant"

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return items from the shopping list."""
        shopping_list = self.storage.get_list(self.list_code)
        items = shopping_list.get("items", [])
        result = []

        for item in items:
            item_id = item.get("id", "")
            name = item.get("name", "")
            qty = item.get("quantity", 1)
            unit = item.get("unit")
            summary = f"{name} ({qty} {unit})".strip() if unit else (f"{name} (x{qty})" if qty > 1 else name)

            status = (
                TodoItemStatus.COMPLETED
                if item.get("completed")
                else TodoItemStatus.NEEDS_ACTION
            )
            result.append(
                TodoItem(
                    uid=item_id,
                    summary=summary,
                    status=status,
                )
            )

        return result

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new item from Home Assistant."""
        await self.storage.async_mutate_list(
            self.list_code,
            {
                "type": "add",
                "item": {
                    "name": item.summary,
                    "quantity": 1,
                    "addedBy": "Home Assistant",
                },
            },
        )
        self.async_write_ha_state()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item status."""
        is_completed = item.status == TodoItemStatus.COMPLETED
        shopping_list = self.storage.get_list(self.list_code)
        target = next((i for i in shopping_list.get("items", []) if i.get("id") == item.uid), None)

        if target and target.get("completed") != is_completed:
            await self.storage.async_mutate_list(
                self.list_code,
                {
                    "type": "toggle",
                    "itemId": item.uid,
                },
            )
            self.async_write_ha_state()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items from the list."""
        for uid in uids:
            await self.storage.async_mutate_list(
                self.list_code,
                {
                    "type": "remove",
                    "itemId": uid,
                },
            )
        self.async_write_ha_state()
