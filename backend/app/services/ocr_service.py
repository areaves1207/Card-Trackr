"""
EasyOCR text extraction service.

Stage 2 of the pipeline: given a perspective-corrected card image, read the card name
and collector number so we can query the Pokemon TCG API.

EasyOCR is loaded once at startup (it downloads a ~100MB model on first run).
We keep it as a module-level singleton to avoid reloading on every request.
"""

import re
from dataclasses import dataclass

import easyocr
import numpy as np

from app.services.card_detector import extract_name_region, extract_number_region

_reader: easyocr.Reader | None = None


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        # gpu=False so it works without CUDA — set to True if you have a GPU
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


@dataclass
class OcrResult:
    name: str | None
    collector_number: str | None  # e.g. "58" (just the card's number, not the set size)
    name_confidence: float
    number_confidence: float


def extract_card_text(card_img: np.ndarray) -> OcrResult:
    """Read card name from the top strip and collector number from the bottom strip."""
    reader = get_reader()

    name_region = extract_name_region(card_img)
    number_region = extract_number_region(card_img)

    name, name_conf = _read_name(reader, name_region)
    number, number_conf = _read_collector_number(reader, number_region)

    return OcrResult(
        name=name,
        collector_number=number,
        name_confidence=name_conf,
        number_confidence=number_conf,
    )


def _read_name(reader: easyocr.Reader, region: np.ndarray) -> tuple[str | None, float]:
    results = reader.readtext(region, detail=1)
    if not results:
        return None, 0.0

    # Take the detection with the highest confidence
    best = max(results, key=lambda r: r[2])
    text = best[1].strip()
    confidence = float(best[2])

    # Basic cleanup — card names are title-cased words, no numbers
    cleaned = re.sub(r"[^a-zA-Z\s'\-\.]", "", text).strip()
    return cleaned if cleaned else None, confidence


def _read_collector_number(reader: easyocr.Reader, region: np.ndarray) -> tuple[str | None, float]:
    """
    Parse the X/Y collector number format. We only care about X (the card's own number).
    EasyOCR may read "58/102", "58 / 102", or just "58102" — handle all cases.
    """
    results = reader.readtext(region, detail=1)
    if not results:
        return None, 0.0

    # Concatenate all detected text in the region
    all_text = " ".join(r[1] for r in results)
    avg_confidence = sum(r[2] for r in results) / len(results)

    # Match "58/102" or "58 / 102" pattern
    match = re.search(r"(\d+)\s*/\s*\d+", all_text)
    if match:
        return match.group(1), avg_confidence

    # Fallback: just grab the first number sequence
    nums = re.findall(r"\d+", all_text)
    if nums:
        return nums[0], avg_confidence * 0.5  # lower confidence since format didn't match

    return None, 0.0


def overall_confidence(result: OcrResult) -> float:
    """Average of name and number confidence — used to decide whether to show candidates."""
    confs = [c for c in [result.name_confidence, result.number_confidence] if c > 0]
    return sum(confs) / len(confs) if confs else 0.0
