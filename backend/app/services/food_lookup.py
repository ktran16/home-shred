"""Barcode → food macros via Open Food Facts (SPEC §17.5 B2b).

The reliable on-device food path is barcode scanning (browser-side, no ML) backed by
Open Food Facts. `parse_off_product` is a pure mapper over the OFF v2 response and is
unit-tested without any network; `lookup_barcode` is the thin httpx fetch.

Note (SPEC §17.7): an OFF lookup **leaves the LAN**, so this is an opt-in external
call rather than a local-only feature. The local-first alternative — an offline OFF
dump served from the host — can replace `lookup_barcode` behind the same interface.
"""

from dataclasses import dataclass

import httpx

# rationale (SPEC §17.5 B2b): OFF v2 single-product endpoint, requesting only the
# fields we map. OFF asks API clients to send a descriptive User-Agent.
OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
OFF_FIELDS = "code,product_name,brands,serving_size,nutriments"
OFF_USER_AGENT = "HomeShred/0.1 (self-hosted personal trainer)"
OFF_TIMEOUT_SECONDS = 6.0


class FoodLookupError(Exception):
    """Upstream/network failure talking to Open Food Facts."""


class FoodNotFoundError(Exception):
    """OFF has no product for this barcode."""


@dataclass
class FoodFacts:
    code: str
    name: str | None
    brand: str | None
    serving_size: str | None
    kcal_per_100g: float | None
    protein_per_100g: float | None
    carbs_per_100g: float | None
    fat_per_100g: float | None


def _num(nutriments: dict, key: str) -> float | None:
    value = nutriments.get(key)
    if isinstance(value, (int, float)):
        return round(float(value), 1)
    if isinstance(value, str):
        try:
            return round(float(value), 1)
        except ValueError:
            return None
    return None


def parse_off_product(payload: dict) -> FoodFacts | None:
    """Map an OFF v2 product response to FoodFacts, or None if not found. Pure/testable."""
    # OFF: status 1 = found, 0 = not found (string variants seen across versions).
    if payload.get("status") not in (1, "1", "success"):
        return None
    product = payload.get("product") or {}
    nutriments = product.get("nutriments") or {}
    return FoodFacts(
        code=str(payload.get("code") or product.get("code") or ""),
        name=(product.get("product_name") or "").strip() or None,
        brand=(product.get("brands") or "").strip() or None,
        serving_size=(product.get("serving_size") or "").strip() or None,
        kcal_per_100g=_num(nutriments, "energy-kcal_100g"),
        protein_per_100g=_num(nutriments, "proteins_100g"),
        carbs_per_100g=_num(nutriments, "carbohydrates_100g"),
        fat_per_100g=_num(nutriments, "fat_100g"),
    )


async def lookup_barcode(code: str, *, timeout: float = OFF_TIMEOUT_SECONDS) -> FoodFacts:
    """Fetch a barcode's macros from Open Food Facts (SPEC §17.5 B2b).

    Raises FoodLookupError on network/upstream failure, FoodNotFoundError if OFF has
    no product for the code.
    """
    url = OFF_URL.format(code=code)
    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers={"User-Agent": OFF_USER_AGENT}
        ) as client:
            resp = await client.get(url, params={"fields": OFF_FIELDS})
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FoodLookupError(str(exc)) from exc
    facts = parse_off_product(payload)
    if facts is None:
        raise FoodNotFoundError(code)
    return facts
