"""Storage management for Cesta Compartida."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFAULT_LIST, DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

DEFAULT_CATALOG: dict[str, dict[str, Any]] = {
    "8480000107046": {
        "barcode": "8480000107046",
        "name": "Leche semidesnatada",
        "brand": "Hacendado",
        "category": "Lácteos y Huevos",
        "updatedAt": 0,
    },
    "8480000160041": {
        "barcode": "8480000160041",
        "name": "Aceite de oliva virgen extra",
        "brand": "Hacendado",
        "category": "Despensa",
        "updatedAt": 0,
    },
    "8480000278623": {
        "barcode": "8480000278623",
        "name": "Huevos camperos",
        "brand": "Hacendado",
        "category": "Lácteos y Huevos",
        "updatedAt": 0,
    },
    "8410128000103": {
        "barcode": "8410128000103",
        "name": "Agua mineral natural 1.5l",
        "brand": "Bezoya",
        "category": "Bebidas",
        "updatedAt": 0,
    },
}


def to_sentence_case(raw: str = "") -> str:
    """Format string to sentence case."""
    trimmed = " ".join(raw.strip().split())
    if not trimmed:
        return ""
    lower = trimmed.lower()
    return lower[0].upper() + lower[1:]


def infer_category_from_tags(tags: list[str] | None = None, product_name: str = "") -> str:
    """Infer Spanish grocery category from tags and product name."""
    combined = " ".join((tags or []) + [product_name]).lower()
    if re.search(r"(milk|leche|yogur|cheese|queso|butter|mantequilla|huevo|egg|dairy|lacteo)", combined):
        return "Lácteos y Huevos"
    if re.search(r"(fruit|fruta|vegetable|verdura|tomate|platano|plátano|lechuga|patata|cebolla|manzana)", combined):
        return "Fruta y Verdura"
    if re.search(r"(meat|carne|pollo|cerdo|ternera|fish|pescado|salmon|salmón|atun|atún|jamon|jamón)", combined):
        return "Carne y Pescado"
    if re.search(r"(bread|pan|bolleria|galleta|biscuit|croissant|tostada)", combined):
        return "Panadería"
    if re.search(r"(water|agua|juice|zumo|beer|cerveza|wine|vino|soda|refresco|beverage|bebida)", combined):
        return "Bebidas"
    if re.search(r"(clean|limpieza|detergente|lejia|lavavajillas|papel higienico|servilleta)", combined):
        return "Limpieza y Hogar"
    if re.search(r"(shampoo|champu|gel|jabon|dentifrico|desodorante|higiene)", combined):
        return "Higiene"
    if re.search(r"(pasta|arroz|rice|oil|aceite|conserva|salsa|cafe|coffee|sugar|azucar|harina|legumbre)", combined):
        return "Despensa"
    return "Otros"


class CestaStorage:
    """Persistent storage backed by Home Assistant Store."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize store."""
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.lists: dict[str, dict[str, Any]] = {}
        self.catalog: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Load data from store."""
        data = await self._store.async_load()
        now = int(time.time() * 1000)

        if not data:
            self.lists = {
                DEFAULT_LIST: {
                    "code": DEFAULT_LIST,
                    "updatedAt": now,
                    "items": [
                        {
                            "id": "seed-1",
                            "name": "Leche semidesnatada",
                            "brand": "Hacendado",
                            "barcode": "8480000107046",
                            "category": "Lácteos y Huevos",
                            "quantity": 6,
                            "completed": False,
                            "addedBy": "Casa",
                            "updatedAt": now,
                        },
                        {
                            "id": "seed-2",
                            "name": "Plátanos de canarias",
                            "category": "Fruta y Verdura",
                            "quantity": 1,
                            "completed": False,
                            "addedBy": "Casa",
                            "updatedAt": now,
                        },
                    ],
                }
            }
            self.catalog = dict(DEFAULT_CATALOG)
            await self.async_save()
            return

        self.lists = data.get("lists", {})
        self.catalog = {**DEFAULT_CATALOG, **data.get("catalog", {})}

        # Normalize names to sentence case
        for list_data in self.lists.values():
            if isinstance(list_data.get("items"), list):
                for item in list_data["items"]:
                    item["name"] = to_sentence_case(item.get("name", ""))

        for entry in self.catalog.values():
            entry["name"] = to_sentence_case(entry.get("name", ""))

    async def async_save(self) -> None:
        """Persist data."""
        await self._store.async_save(
            {
                "lists": self.lists,
                "catalog": self.catalog,
            }
        )

    def get_list(self, code: str) -> dict[str, Any]:
        """Get or initialize a shopping list by code."""
        normalized_code = code.strip().lower()
        if normalized_code not in self.lists:
            now = int(time.time() * 1000)
            self.lists[normalized_code] = {
                "code": normalized_code,
                "updatedAt": now,
                "items": [],
            }
        return self.lists[normalized_code]

    def get_catalog_list(self) -> list[dict[str, Any]]:
        """Get all catalog products as a list."""
        return list(self.catalog.values())

    def get_product(self, barcode: str) -> dict[str, Any] | None:
        """Get product from local catalog."""
        return self.catalog.get(barcode.strip())

    async def async_mutate_list(self, code: str, body: dict[str, Any]) -> dict[str, Any]:
        """Apply a mutation to a shopping list."""
        normalized_code = code.strip().lower()
        shopping_list = self.get_list(normalized_code)
        action_type = body.get("type")
        now = int(time.time() * 1000)

        if action_type in ("add", "addBatch"):
            incoming = body.get("items") if action_type == "addBatch" else [body.get("item", {})]
            items_list = shopping_list.setdefault("items", [])

            for raw_entry in incoming:
                if not raw_entry:
                    continue
                clean_name = to_sentence_case(raw_entry.get("name", ""))
                if not clean_name:
                    continue

                barcode = (raw_entry.get("barcode") or "").strip() or None
                category = raw_entry.get("category") or infer_category_from_tags([], clean_name)
                try:
                    raw_qty = float(raw_entry.get("quantity", 1))
                    qty_to_add = raw_qty if raw_qty >= 0 else 1.0
                except (ValueError, TypeError):
                    qty_to_add = 1.0

                unit = (raw_entry.get("unit") or "").strip().lower() or None

                existing = next(
                    (
                        item
                        for item in items_list
                        if (barcode and item.get("barcode") == barcode)
                        or item.get("name", "").lower() == clean_name.lower()
                    ),
                    None,
                )

                if existing:
                    if existing.get("completed"):
                        existing["completed"] = False
                        existing["quantity"] = max(1.0, qty_to_add)
                        existing["unit"] = unit
                    elif qty_to_add > 0:
                        if existing.get("unit") == unit:
                            existing["quantity"] = round(existing.get("quantity", 1.0) + qty_to_add, 2)
                        else:
                            existing["quantity"] = qty_to_add
                            existing["unit"] = unit
                    existing["name"] = clean_name
                    if raw_entry.get("brand"):
                        existing["brand"] = raw_entry["brand"]
                    if raw_entry.get("category"):
                        existing["category"] = category
                    if raw_entry.get("imageUrl"):
                        existing["imageUrl"] = raw_entry["imageUrl"]
                    if raw_entry.get("addedBy"):
                        existing["addedBy"] = raw_entry["addedBy"]
                    existing["updatedAt"] = now
                else:
                    new_item = {
                        "id": str(uuid.uuid4()),
                        "name": clean_name,
                        "brand": (raw_entry.get("brand") or "").strip() or None,
                        "barcode": barcode,
                        "category": category,
                        "quantity": qty_to_add,
                        "unit": unit,
                        "imageUrl": raw_entry.get("imageUrl"),
                        "completed": False,
                        "addedBy": (raw_entry.get("addedBy") or "").strip() or "Casa",
                        "updatedAt": now,
                    }
                    items_list.insert(0, new_item)

                if action_type != "add" or body.get("saveToCatalog") is not False:
                    catalog_key = barcode or f"MANUAL:{clean_name.lower()}"
                    self.catalog[catalog_key] = {
                        "barcode": catalog_key,
                        "name": clean_name,
                        "brand": (raw_entry.get("brand") or "").strip() or self.catalog.get(catalog_key, {}).get("brand"),
                        "category": category,
                        "imageUrl": raw_entry.get("imageUrl") or self.catalog.get(catalog_key, {}).get("imageUrl"),
                        "updatedAt": now,
                    }

        elif action_type == "toggle":
            target_id = body.get("itemId")
            for item in shopping_list.get("items", []):
                if item.get("id") == target_id:
                    item["completed"] = not item.get("completed", False)
                    item["updatedAt"] = now
                    break

        elif action_type == "quantity":
            target_id = body.get("itemId")
            delta = float(body.get("delta", 0))
            items = shopping_list.get("items", [])
            for item in list(items):
                if item.get("id") == target_id:
                    next_qty = round(float(item.get("quantity", 1)) + delta, 2)
                    if next_qty <= 0:
                        items.remove(item)
                    else:
                        item["quantity"] = next_qty
                        item["updatedAt"] = now
                    break

        elif action_type == "remove":
            target_id = body.get("itemId")
            shopping_list["items"] = [item for item in shopping_list.get("items", []) if item.get("id") != target_id]

        elif action_type == "clearCompleted":
            shopping_list["items"] = [item for item in shopping_list.get("items", []) if not item.get("completed")]

        elif action_type == "replaceAll" and isinstance(body.get("items"), list):
            shopping_list["items"] = body["items"]

        shopping_list["updatedAt"] = now
        await self.async_save()
        return shopping_list
