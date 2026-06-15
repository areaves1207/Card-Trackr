import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db, AsyncSessionLocal
from app.models.scan import ScanResult, ScanSession
from app.models.user import User
from app.schemas.scan import ConfirmCardRequest, ScanSessionResponse
from app.services import card_detector, ocr_service, r2_storage, tcg_api

router = APIRouter(prefix="/scan", tags=["scan"])

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
SUPPORTED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


@router.post("/images", response_model=ScanSessionResponse, status_code=202)
async def scan_images(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept 1–N image uploads. Returns a session immediately (HTTP 202 Accepted).
    Processing runs in the background — poll GET /scan/{session_id} for results.
    """
    for f in files:
        if f.content_type not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(400, f"Unsupported file type: {f.content_type}")

    session = ScanSession(user_id=current_user.id, source_type="image", status="pending")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Read file bytes now — UploadFile is not safe to read inside a background task
    file_data = [(f.filename, f.content_type, await f.read()) for f in files]

    background_tasks.add_task(_process_images, session.id, file_data)

    await db.refresh(session, ["results"])
    return session


@router.post("/video", response_model=ScanSessionResponse, status_code=202)
async def scan_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in SUPPORTED_VIDEO_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    session = ScanSession(user_id=current_user.id, source_type="video", status="pending")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    video_bytes = await file.read()
    url = await r2_storage.upload_file(video_bytes, file.filename or "video", file.content_type)
    if url:
        session.source_url = url
        await db.commit()

    background_tasks.add_task(_process_video, session.id, video_bytes)

    await db.refresh(session, ["results"])
    return session


@router.get("/{session_id}", response_model=ScanSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScanSession).where(
            ScanSession.id == session_id,
            ScanSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    await db.refresh(session, ["results"])
    return session


@router.post("/confirm")
async def confirm_card(
    body: ConfirmCardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User picks the correct card from the candidate list."""
    result = await db.execute(
        select(ScanResult)
        .join(ScanSession)
        .where(ScanResult.id == body.scan_result_id, ScanSession.user_id == current_user.id)
    )
    scan_result = result.scalar_one_or_none()
    if not scan_result:
        raise HTTPException(404, "Scan result not found")

    card = await tcg_api.get_or_create_card_by_api_id(body.pokemon_card_api_id, db)
    if not card:
        raise HTTPException(404, "Card not found in TCG API")

    scan_result.pokemon_card_id = card.id
    await db.commit()
    return {"ok": True, "card": card.name}


async def _process_images(session_id: int, file_data: list[tuple[str, str, bytes]]):
    """Background task: run the full CV pipeline on each uploaded image."""
    async with AsyncSessionLocal() as db:
        session = await db.get(ScanSession, session_id)
        session.status = "processing"
        await db.commit()

        seen_card_ids: set[int] = set()

        try:
            for filename, content_type, image_bytes in file_data:
                await _process_single_image(db, session, image_bytes, seen_card_ids)

            session.status = "complete"
        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
        finally:
            await db.commit()


async def _process_video(session_id: int, video_bytes: bytes):
    """Background task: extract frames from video and run the pipeline on each."""
    import cv2
    import numpy as np
    import tempfile, os

    async with AsyncSessionLocal() as db:
        session = await db.get(ScanSession, session_id)
        session.status = "processing"
        await db.commit()

        seen_card_ids: set[int] = set()

        try:
            # Write video to a temp file because OpenCV VideoCapture needs a file path
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name

            cap = cv2.VideoCapture(tmp_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frame_interval = max(1, int(fps / 2))  # process 2 frames per second

            frame_idx = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    _, encoded = cv2.imencode(".jpg", frame)
                    image_bytes = encoded.tobytes()
                    timestamp = frame_idx / fps
                    await _process_single_image(db, session, image_bytes, seen_card_ids, timestamp)

                frame_idx += 1

            cap.release()
            os.unlink(tmp_path)
            session.status = "complete"
        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
        finally:
            await db.commit()


async def _process_single_image(
    db: AsyncSession,
    session: ScanSession,
    image_bytes: bytes,
    seen_card_ids: set[int],
    timestamp: float | None = None,
):
    """Run card detect → OCR → API lookup for one image. Appends a ScanResult to the session."""
    card_img = card_detector.detect_and_crop_card(image_bytes)
    if card_img is None:
        return  # no card found in this frame

    ocr_result = ocr_service.extract_card_text(card_img)
    confidence = ocr_service.overall_confidence(ocr_result)

    lookup = await tcg_api.lookup_card(
        name=ocr_result.name,
        collector_number=ocr_result.collector_number,
        confidence=confidence,
        db=db,
    )

    # Skip this frame if we already found this card in the session (video dedup)
    if lookup.card and lookup.card.id in seen_card_ids:
        return
    if lookup.card:
        seen_card_ids.add(lookup.card.id)

    scan_result = ScanResult(
        session_id=session.id,
        pokemon_card_id=lookup.card.id if lookup.card else None,
        confidence=confidence,
        frame_timestamp=timestamp,
        raw_ocr_name=ocr_result.name,
        raw_ocr_number=ocr_result.collector_number,
    )
    db.add(scan_result)
    await db.commit()
