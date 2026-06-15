from datetime import datetime

from pydantic import BaseModel

from app.schemas.card import PokemonCardResponse


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectionCardResponse(BaseModel):
    id: int
    quantity: int
    condition: str | None
    notes: str | None
    added_at: datetime
    pokemon_card: PokemonCardResponse

    model_config = {"from_attributes": True}


class AddCardRequest(BaseModel):
    collection_id: int
    pokemon_card_api_id: str
    quantity: int = 1
    condition: str | None = None
    notes: str | None = None


class UpdateCardRequest(BaseModel):
    quantity: int | None = None
    condition: str | None = None
    notes: str | None = None


class CreateCollectionRequest(BaseModel):
    name: str
    description: str | None = None
