from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, complete, failed
    source_type: Mapped[str] = mapped_column(String(10))  # image, video
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # R2 URL of original upload
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="scan_sessions")
    results: Mapped[list["ScanResult"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("scan_sessions.id"), index=True)
    pokemon_card_id: Mapped[int | None] = mapped_column(ForeignKey("pokemon_cards.id"), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)  # seconds into video
    auto_added: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_ocr_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_ocr_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    session: Mapped["ScanSession"] = relationship(back_populates="results")
    pokemon_card: Mapped["PokemonCard | None"] = relationship(back_populates="scan_results")
