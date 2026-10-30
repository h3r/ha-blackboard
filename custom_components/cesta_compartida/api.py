"""API endpoints for Cesta Compartida."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_GEMINI_API_KEY, DOMAIN
from .storage import CestaStorage, infer_category_from_tags, to_sentence_case

_LOGGER = logging.getLogger(__name__)


def _cors_json_response(data: Any, status: int = 200) -> web.Response:
    """Return JSON response with CORS headers."""
    return web.json_response(
        data,
        status=status,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


class CestaListsView(HomeAssistantView):
    """View to get and mutate shopping lists."""

    url = "/api/cesta_compartida/lists/{code}"
    name = "api:cesta_compartida:lists"
    requires_auth = False
    cors_allowed = True

    def __init__(self, storage: CestaStorage) -> None:
        """Initialize list view."""
        self.storage = storage

    async def get(self, request: web.Request, code: str) -> web.Response:
        """Get shopping list state."""
        return _cors_json_response(self.storage.get_list(code))

    async def post(self, request: web.Request, code: str) -> web.Response:
        """Apply mutation to list."""
        try:
            body = await request.json()
        except Exception:
            return _cors_json_response({"error": "Invalid JSON body"}, status=400)

        if not body or "type" not in body:
            return _cors_json_response({"error": "Missing mutation type"}, status=400)

        updated_list = await self.storage.async_mutate_list(code, body)
        return _cors_json_response(updated_list)


class CestaProductsView(HomeAssistantView):
    """View to get catalog products."""

    url = "/api/cesta_compartida/products"
    name = "api:cesta_compartida:products"
    requires_auth = False
    cors_allowed = True

    def __init__(self, storage: CestaStorage) -> None:
        """Initialize products view."""
        self.storage = storage

    async def get(self, request: web.Request) -> web.Response:
        """Get all catalog products."""
        return _cors_json_response(self.storage.get_catalog_list())


class CestaProductDetailView(HomeAssistantView):
    """View to lookup product by barcode."""

    url = "/api/cesta_compartida/products/{barcode}"
    name = "api:cesta_compartida:product_detail"
    requires_auth = False
    cors_allowed = True

    def __init__(self, hass: HomeAssistant, storage: CestaStorage) -> None:
        """Initialize product detail view."""
        self.hass = hass
        self.storage = storage

    async def get(self, request: web.Request, barcode: str) -> web.Response:
        """Lookup product by barcode locally and fallback to Open Food Facts."""
        clean_code = barcode.strip()

        # Check local catalog first
        local_match = self.storage.get_product(clean_code)
        if local_match:
            return _cors_json_response(
                {
                    "found": True,
                    "source": "local",
                    "product": local_match,
                }
            )

        # Check Open Food Facts for standard numeric barcodes
        if re.match(r"^\d{8,14}$", clean_code):
            session = async_get_clientsession(self.hass)
            off_url = f"https://world.openfoodfacts.org/api/v2/product/{clean_code}.json"
            try:
                async with session.get(
                    off_url,
                    params={
                        "fields": "product_name_es,product_name,generic_name_es,brands,image_front_small_url,categories_tags"
                    },
                    timeout=5,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw_product = data.get("product", {})
                        resolved_name = to_sentence_case(
                            raw_product.get("product_name_es")
                            or raw_product.get("product_name")
                            or raw_product.get("generic_name_es")
                            or ""
                        )

                        if data.get("status") == 1 and resolved_name:
                            brand = (raw_product.get("brands") or "").split(",")[0].strip() or None
                            category = infer_category_from_tags(raw_product.get("categories_tags", []), resolved_name)
                            catalog_entry = {
                                "barcode": clean_code,
                                "name": resolved_name,
                                "brand": brand,
                                "category": category,
                                "imageUrl": raw_product.get("image_front_small_url"),
                                "updatedAt": 0,
                            }
                            self.storage.catalog[clean_code] = catalog_entry
                            await self.storage.async_save()

                            return _cors_json_response(
                                {
                                    "found": True,
                                    "source": "openfoodfacts",
                                    "product": catalog_entry,
                                }
                            )
            except Exception as err:
                _LOGGER.debug("Open Food Facts lookup failed for %s: %s", clean_code, err)

        return _cors_json_response(
            {
                "found": False,
                "source": "none",
                "product": None,
            }
        )


class CestaVisionView(HomeAssistantView):
    """View to parse handwritten or printed shopping list images with Gemini Vision."""

    url = "/api/cesta_compartida/vision"
    name = "api:cesta_compartida:vision"
    requires_auth = False
    cors_allowed = True

    def __init__(self, hass: HomeAssistant, api_key: str | None = None) -> None:
        """Initialize vision view."""
        self.hass = hass
        self.default_api_key = api_key

    async def post(self, request: web.Request) -> web.Response:
        """Extract shopping items from image base64."""
        try:
            body = await request.json()
        except Exception:
            return _cors_json_response({"error": "Invalid JSON body"}, status=400)

        api_key = (body.get("apiKey") or self.default_api_key or "").strip()
        if not api_key:
            return _cors_json_response({"error": "Missing Gemini API key"}, status=400)

        image_base64 = body.get("imageBase64", "")
        if not image_base64:
            return _cors_json_response({"error": "Missing image payload"}, status=400)

        clean_base64 = re.sub(r"^data:[^;]+;base64,", "", image_base64).strip()
        raw_mime = body.get("mimeType") or "image/png"
        mime_type = raw_mime.split(";")[0].strip() or "image/png"

        session = async_get_clientsession(self.hass)
        gemini_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Extrae todos los productos de esta lista de la compra (puede estar escrita a mano o ser una captura). "
                                'Devuelve ÚNICAMENTE un array JSON con objetos {"name": "Nombre en español", "quantity": número, "unit": "gr|kg|ml|l opcional", "category": "Lácteos y Huevos|Fruta y Verdura|Carne y Pescado|Panadería|Despensa|Bebidas|Limpieza y Hogar|Higiene|Otros"}. '
                                "No incluyas los títulos de las secciones como productos."
                            )
                        },
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": clean_base64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        }

        try:
            async with session.post(gemini_url, json=payload, timeout=15) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    _LOGGER.error("Gemini API error (%s): %s", resp.status, err_text)
                    return _cors_json_response({"error": "Gemini API failed"}, status=502)

                data = await resp.json()
                raw_text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "[]")
                )
                parsed = json.loads(raw_text)

                results = []
                for item in parsed:
                    if not item or not isinstance(item, dict):
                        continue
                    name = to_sentence_case(item.get("name", ""))
                    if not name:
                        continue
                    try:
                        qty = float(item.get("quantity", 1))
                        qty = qty if qty > 0 else 1.0
                    except (ValueError, TypeError):
                        qty = 1.0

                    unit = (item.get("unit") or "").strip().lower() or None
                    cat = item.get("category") or infer_category_from_tags([], name)
                    results.append(
                        {
                            "name": name,
                            "quantity": qty,
                            "unit": unit,
                            "category": cat,
                        }
                    )

                return _cors_json_response(results)

        except Exception as err:
            _LOGGER.error("Vision processing error: %s", err)
            return _cors_json_response({"error": "Failed to process image"}, status=500)
