from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.card import CardSearchResult
from app.services.tcg_api import search_cards_by_name

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/search", response_model=list[CardSearchResult])
async def search_cards(
    q: str = Query(..., min_length=2),
    _: User = Depends(get_current_user),
):
    """Proxy search to the Pokemon TCG API — powers the manual add / search bar."""
    raw_cards = await search_cards_by_name(q)
    return [
        CardSearchResult(
            api_id=c["id"],
            name=c["name"],
            set_name=c.get("set", {}).get("name", ""),
            collector_number=c.get("number", ""),
            rarity=c.get("rarity"),
            image_small=c.get("images", {}).get("small"),
        )
        for c in raw_cards
    ]
