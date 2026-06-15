from datetime import datetime

from pydantic import BaseModel

from app.schemas.card import PokemonCardResponse, CardSearchResult


class ScanSessionResponse(BaseModel):
    id: int
    status: str
    source_type: str
    created_at: datetime
    results: list["ScanResultResponse"]

    model_config = {"from_attributes": True}


class ScanResultResponse(BaseModel):
    id: int
    confidence: float | None
    frame_timestamp: float | None
    raw_ocr_name: str | None
    raw_ocr_number: str | None
    auto_added: bool
    pokemon_card: PokemonCardResponse | None
    candidates: list[CardSearchResult] = []  # populated when confidence is low

    model_config = {"from_attributes": True}


class ConfirmCardRequest(BaseModel):
    """User confirms a scan result by choosing a specific card (by api_id)."""
    scan_result_id: int
    pokemon_card_api_id: str
    add_to_collection_id: int | None = None
