from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PokemonCard(Base):
    """Cache of Pokemon TCG API card data. One row per unique card, shared across all users."""

    __tablename__ = "pokemon_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # e.g. "base1-4"
    name: Mapped[str] = mapped_column(String(100), index=True)
    set_name: Mapped[str] = mapped_column(String(100))
    set_id: Mapped[str] = mapped_column(String(50))
    collector_number: Mapped[str] = mapped_column(String(20))
    rarity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_small: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_large: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    collection_entries: Mapped[list["CollectionCard"]] = relationship(back_populates="pokemon_card")
    scan_results: Mapped[list["ScanResult"]] = relationship(back_populates="pokemon_card")
