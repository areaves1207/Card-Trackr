from datetime import datetime

from pydantic import BaseModel


class PokemonCardResponse(BaseModel):
    id: int
    api_id: str
    name: str
    set_name: str
    set_id: str
    collector_number: str
    rarity: str | None
    image_small: str | None
    image_large: str | None

    model_config = {"from_attributes": True}


class CardSearchResult(BaseModel):
    """Lightweight card result used in search / scan candidate lists."""
    api_id: str
    name: str
    set_name: str
    collector_number: str
    rarity: str | None
    image_small: str | None
