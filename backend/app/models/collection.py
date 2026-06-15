from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="collections")
    cards: Mapped[list["CollectionCard"]] = relationship(back_populates="collection", cascade="all, delete-orphan")


class CollectionCard(Base):
    __tablename__ = "collection_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), index=True)
    pokemon_card_id: Mapped[int] = mapped_column(ForeignKey("pokemon_cards.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    condition: Mapped[str | None] = mapped_column(String(20), nullable=True)  # NM, LP, MP, HP, DMG
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    collection: Mapped["Collection"] = relationship(back_populates="cards")
    pokemon_card: Mapped["PokemonCard"] = relationship(back_populates="collection_entries")
