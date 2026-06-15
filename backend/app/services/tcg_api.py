"""
Pokemon TCG API client with PostgreSQL caching.

Stage 3 of the pipeline: given a card name + collector number from OCR, find the
exact card in the Pokemon TCG database.

Caching strategy: after the first successful lookup we store the card in `pokemon_cards`.
Repeat scans of the same card skip the external API entirely.
"""

from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.card import PokemonCard

TCG_API_BASE = "https://api.pokemontcg.io/v2"
LOW_CONFIDENCE_THRESHOLD = 0.6  # below this we return candidates instead of a definitive match


@dataclass
class CardLookupResult:
    card: PokemonCard | None
    candidates: list[dict]  # raw API dicts, used when confidence is too low for a definitive match
    is_definitive: bool


def _build_headers() -> dict:
    headers = {}
    if settings.pokemon_tcg_api_key:
        headers["X-Api-Key"] = settings.pokemon_tcg_api_key
    return headers


async def lookup_card(
    name: str | None,
    collector_number: str | None,
    confidence: float,
    db: AsyncSession,
) -> CardLookupResult:
    """
    Main entry point. Returns the matched PokemonCard (creating it in the cache if needed),
    or a list of candidates for the user to choose from when confidence is low.
    """
    if not name and not collector_number:
        return CardLookupResult(card=None, candidates=[], is_definitive=False)

    if confidence >= LOW_CONFIDENCE_THRESHOLD and name and collector_number:
        card = await _exact_lookup(name, collector_number, db)
        if card:
            return CardLookupResult(card=card, candidates=[], is_definitive=True)

    # Fall back to name-only search and return candidates
    candidates = await _search_by_name(name or "")
    return CardLookupResult(card=None, candidates=candidates[:3], is_definitive=False)


async def _exact_lookup(name: str, number: str, db: AsyncSession) -> PokemonCard | None:
    """Try to find an exact match by name + collector number. Checks DB cache first."""
    # Check cache
    result = await db.execute(
        select(PokemonCard).where(
            PokemonCard.name.ilike(name),
            PokemonCard.collector_number == number,
        )
    )
    cached = result.scalar_one_or_none()
    if cached:
        return cached

    # Query the Pokemon TCG API
    query = f'name:"{name}" number:"{number}"'
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TCG_API_BASE}/cards",
            params={"q": query, "pageSize": 1},
            headers=_build_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    cards = data.get("data", [])
    if not cards:
        return None

    return await _upsert_card(cards[0], db)


async def _search_by_name(name: str) -> list[dict]:
    """Return raw API card dicts matching the name — used for the candidate list."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TCG_API_BASE}/cards",
            params={"q": f'name:"{name}"', "pageSize": 10},
            headers=_build_headers(),
            timeout=10.0,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("data", [])


async def get_or_create_card_by_api_id(api_id: str, db: AsyncSession) -> PokemonCard | None:
    """Fetch a card by its TCG API id (e.g. 'base1-4'). Used when the user picks a candidate."""
    result = await db.execute(select(PokemonCard).where(PokemonCard.api_id == api_id))
    cached = result.scalar_one_or_none()
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TCG_API_BASE}/cards/{api_id}",
            headers=_build_headers(),
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None
        raw = resp.json().get("data")

    return await _upsert_card(raw, db) if raw else None


async def search_cards_by_name(query: str) -> list[dict]:
    """Proxy search used by the frontend search bar."""
    return await _search_by_name(query)


async def _upsert_card(raw: dict, db: AsyncSession) -> PokemonCard:
    """Convert a raw Pokemon TCG API card dict into a cached PokemonCard row."""
    images = raw.get("images", {})
    card = PokemonCard(
        api_id=raw["id"],
        name=raw["name"],
        set_name=raw.get("set", {}).get("name", ""),
        set_id=raw.get("set", {}).get("id", ""),
        collector_number=raw.get("number", ""),
        rarity=raw.get("rarity"),
        image_small=images.get("small"),
        image_large=images.get("large"),
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card
