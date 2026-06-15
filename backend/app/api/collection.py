from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.collection import Collection, CollectionCard
from app.models.user import User
from app.schemas.collection import (
    AddCardRequest,
    CollectionCardResponse,
    CollectionResponse,
    CreateCollectionRequest,
    UpdateCardRequest,
)
from app.services.tcg_api import get_or_create_card_by_api_id

router = APIRouter(prefix="/collection", tags=["collection"])


@router.get("", response_model=list[CollectionResponse])
async def list_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Collection).where(Collection.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("", response_model=CollectionResponse, status_code=201)
async def create_collection(
    body: CreateCollectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = Collection(user_id=current_user.id, name=body.name, description=body.description)
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return collection


@router.get("/{collection_id}/cards", response_model=list[CollectionCardResponse])
async def list_cards(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Collection not found")

    cards = await db.execute(
        select(CollectionCard)
        .options(selectinload(CollectionCard.pokemon_card))
        .where(CollectionCard.collection_id == collection_id)
    )
    return cards.scalars().all()


@router.post("/cards", response_model=CollectionCardResponse, status_code=201)
async def add_card(
    body: AddCardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify the collection belongs to the user
    result = await db.execute(
        select(Collection).where(
            Collection.id == body.collection_id, Collection.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Collection not found")

    card = await get_or_create_card_by_api_id(body.pokemon_card_api_id, db)
    if not card:
        raise HTTPException(404, "Card not found in Pokemon TCG API")

    entry = CollectionCard(
        collection_id=body.collection_id,
        pokemon_card_id=card.id,
        quantity=body.quantity,
        condition=body.condition,
        notes=body.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry, ["pokemon_card"])
    return entry


@router.patch("/cards/{entry_id}", response_model=CollectionCardResponse)
async def update_card(
    entry_id: int,
    body: UpdateCardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CollectionCard)
        .options(selectinload(CollectionCard.pokemon_card))
        .join(Collection)
        .where(CollectionCard.id == entry_id, Collection.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Card not found in collection")

    if body.quantity is not None:
        entry.quantity = body.quantity
    if body.condition is not None:
        entry.condition = body.condition
    if body.notes is not None:
        entry.notes = body.notes

    await db.commit()
    await db.refresh(entry, ["pokemon_card"])
    return entry


@router.delete("/cards/{entry_id}", status_code=204)
async def remove_card(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CollectionCard)
        .join(Collection)
        .where(CollectionCard.id == entry_id, Collection.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Card not found in collection")

    await db.delete(entry)
    await db.commit()
