"""
OpenCV card detection pipeline.

Given raw image bytes (from any camera/upload), produces a clean, perspective-corrected
crop of just the Pokemon card. This is stage 1 of the identification pipeline.

How it works:
  1. Grayscale + blur  — reduce color noise and texture
  2. Canny edges       — find sharp boundaries (the card border is a strong edge)
  3. Find contours     — trace connected edge paths into closed shapes
  4. Pick the card     — the largest 4-cornered contour with the right aspect ratio
  5. Perspective warp  — flatten the angled rectangle into a straight-on crop
"""

import cv2
import numpy as np


CARD_ASPECT_RATIO = 3.5 / 2.5  # Pokemon cards are 3.5" tall × 2.5" wide
ASPECT_TOLERANCE = 0.3


def detect_and_crop_card(image_bytes: bytes) -> np.ndarray | None:
    """
    Returns a perspective-corrected BGR image of the card, or None if no card found.
    The output is always 500×700 px (matching the card's 2.5:3.5 ratio).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    corners = _find_card_corners(img)
    if corners is None:
        return None

    return _warp_card(img, corners)


def _find_card_corners(img: np.ndarray) -> np.ndarray | None:
    """Returns the 4 corner points of the card in the image, or None."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny edge detection — lower/upper thresholds tuned for typical card photos
    edges = cv2.Canny(blurred, 50, 150)

    # Dilate edges slightly to close small gaps in the card border
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours largest to smallest by area — the card should be the biggest shape
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    img_area = img.shape[0] * img.shape[1]

    for contour in contours[:5]:  # only check the 5 largest
        area = cv2.contourArea(contour)
        if area < img_area * 0.1:  # card must cover at least 10% of the image
            break

        # Approximate the contour to a polygon
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) != 4:
            continue

        # Check that the bounding box has roughly the right aspect ratio for a Pokemon card
        x, y, w, h = cv2.boundingRect(approx)
        ratio = max(w, h) / min(w, h)
        if abs(ratio - CARD_ASPECT_RATIO) > ASPECT_TOLERANCE:
            continue

        return _order_corners(approx.reshape(4, 2))

    return None


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """
    Order corners as: top-left, top-right, bottom-right, bottom-left.
    This consistent ordering is required for cv2.getPerspectiveTransform.
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    rect[0] = pts[np.argmin(s)]     # top-left has smallest x+y
    rect[2] = pts[np.argmax(s)]     # bottom-right has largest x+y
    rect[1] = pts[np.argmin(diff)]  # top-right has smallest x-y
    rect[3] = pts[np.argmax(diff)]  # bottom-left has largest x-y

    return rect


def _warp_card(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Apply perspective transform to produce a 500×700 front-facing card image."""
    dst_w, dst_h = 500, 700
    dst_corners = np.array(
        [[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(corners, dst_corners)
    return cv2.warpPerspective(img, M, (dst_w, dst_h))


def extract_name_region(card_img: np.ndarray) -> np.ndarray:
    """Top 12% of the card — where the card name is printed."""
    h = card_img.shape[0]
    return card_img[: int(h * 0.12), :]


def extract_number_region(card_img: np.ndarray) -> np.ndarray:
    """Bottom 8% of the card — where the collector number (e.g. 58/102) is printed."""
    h = card_img.shape[0]
    return card_img[int(h * 0.92) :, :]
