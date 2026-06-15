"""Food search by name, backed by Open Food Facts text search (SPEC §19.8 W2).

Closes the food-logging gap where a food could only be added by barcode scan (§17.5 B2b)
or manual macro entry. `search_foods` queries OFF's text-search endpoint, caches the hits
in the local `foods` table, then returns matches from that cache — so repeat searches are
served offline/fast and an OFF outage degrades to previously-cached results rather than an
error. Results are per-100 g (`FoodFacts`), feeding the existing `FoodLogIn` path on the FE.

Note (SPEC §17.7): an OFF query leaves the LAN — opt-in/external, like the barcode lookup.
The pure `parse_off_search` is unit-tested without network; `search_off` is the thin fetch.
"""

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Food
from app.services.food_lookup import (
    OFF_TIMEOUT_SECONDS,
    OFF_USER_AGENT,
    FoodFacts,
    FoodLookupError,
    product_to_facts,
)

# rationale (SPEC §19.8 W2): OFF legacy search endpoint, requesting only mapped fields.
OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_SEARCH_FIELDS = "code,product_name,brands,nutriments"
MAX_SEARCH_RESULTS = 25


def parse_off_search(payload: dict) -> list[FoodFacts]:
    """Map an OFF search response (`{products: [...]}`) to FoodFacts. Pure/testable.

    Drops products without a name or a barcode (the cache is keyed on the barcode).
    """
    products = payload.get("products") or []
    facts: list[FoodFacts] = []
    for product in products:
        item = product_to_facts(product)
        if item.name and item.code:
            facts.append(item)
    return facts


async def search_off(
    query: str, *, limit: int, timeout: float = OFF_TIMEOUT_SECONDS
) -> list[FoodFacts]:
    """Fetch text-search results from Open Food Facts. Raises FoodLookupError on failure."""
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
        "fields": OFF_SEARCH_FIELDS,
    }
    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers={"User-Agent": OFF_USER_AGENT}
        ) as client:
            resp = await client.get(OFF_SEARCH_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FoodLookupError(str(exc)) from exc
    return parse_off_search(payload)


async def cache_foods(db: AsyncSession, facts: list[FoodFacts]) -> None:
    """Upsert OFF hits into the local `foods` cache, keyed on barcode."""
    for item in facts:
        if not item.code:
            continue
        values = {
            "code": item.code,
            "name": item.name,
            "brand": item.brand,
            "kcal_per_100g": item.kcal_per_100g,
            "protein_per_100g": item.protein_per_100g,
            "carbs_per_100g": item.carbs_per_100g,
            "fat_per_100g": item.fat_per_100g,
        }
        stmt = pg_insert(Food).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Food.code],
            set_={k: values[k] for k in values if k != "code"},
        )
        await db.execute(stmt)
    await db.commit()


async def search_cache(db: AsyncSession, query: str, *, limit: int) -> list[Food]:
    """Case-insensitive name search over the local cache, shorter names ranked first."""
    pattern = f"%{query.strip()}%"
    stmt = (
        select(Food)
        .where(Food.name.ilike(pattern))
        .order_by(func.length(Food.name), Food.name)
        .limit(limit)
    )
    return list((await db.scalars(stmt)).all())


def _food_to_facts(food: Food) -> FoodFacts:
    return FoodFacts(
        code=food.code,
        name=food.name,
        brand=food.brand,
        serving_size=None,
        kcal_per_100g=None if food.kcal_per_100g is None else float(food.kcal_per_100g),
        protein_per_100g=None if food.protein_per_100g is None else float(food.protein_per_100g),
        carbs_per_100g=None if food.carbs_per_100g is None else float(food.carbs_per_100g),
        fat_per_100g=None if food.fat_per_100g is None else float(food.fat_per_100g),
    )


async def search_foods(db: AsyncSession, query: str, *, limit: int = 10) -> list[FoodFacts]:
    """Search OFF (best-effort), cache the hits, and return matches from the local cache.

    On an OFF failure we skip the refresh and return whatever the cache already holds, so
    the feature still works offline once foods have been seen.
    """
    query = query.strip()
    if not query:
        return []
    try:
        off_hits = await search_off(query, limit=min(limit, MAX_SEARCH_RESULTS))
        await cache_foods(db, off_hits)
    except FoodLookupError:
        pass
    return [_food_to_facts(food) for food in await search_cache(db, query, limit=limit)]
