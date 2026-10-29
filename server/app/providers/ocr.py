"""Local OCR: OpenCV clean-up + Tesseract (eng + mal by default)."""

from __future__ import annotations

import logging
from functools import lru_cache

import cv2
import numpy as np
import pytesseract
from pydantic import BaseModel

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

MIN_WIDTH = 1000  # upscale narrower images; tesseract struggles with small text


class OcrWord(BaseModel):
    text: str
    conf: float


class OcrResult(BaseModel):
    text: str
    mean_confidence: float
    words: list[OcrWord]
    langs: str


class OcrUnavailable(Exception):
    """Tesseract binary is not installed or not on PATH."""


@lru_cache
def available_langs() -> frozenset[str]:
    try:
        return frozenset(pytesseract.get_languages(config=""))
    except pytesseract.TesseractNotFoundError as e:
        raise OcrUnavailable(
            "tesseract is not installed (Ubuntu: sudo apt install tesseract-ocr)"
        ) from e


def resolve_langs(requested: str) -> str:
    have = available_langs()
    wanted = [lang for lang in requested.split("+") if lang]
    usable = [lang for lang in wanted if lang in have]
    for lang in wanted:
        if lang not in have:
            log.warning("Tesseract language '%s' missing; falling back without it", lang)
    return "+".join(usable) or "eng"


def _deskew(gray: np.ndarray) -> np.ndarray:
    inverted = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(inverted > 128))
    if len(coords) < 50:
        return gray
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    # OpenCV reports angles in (0, 90]; map to a small correction around 0.
    if angle > 45:
        angle -= 90
    angle = -angle
    if abs(angle) < 0.5 or abs(angle) > 15:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("could not decode image")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if w < MIN_WIDTH:
        scale = MIN_WIDTH / w
        gray = cv2.resize(gray, (MIN_WIDTH, int(h * scale)), interpolation=cv2.INTER_CUBIC)
    gray = _deskew(gray)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)


def ocr_image(image_bytes: bytes, settings: Settings | None = None) -> OcrResult:
    settings = settings or get_settings()
    langs = resolve_langs(settings.ocr_langs)
    clean = preprocess(image_bytes)
    data = pytesseract.image_to_data(clean, lang=langs, output_type=pytesseract.Output.DICT)
    words = [
        OcrWord(text=t.strip(), conf=float(c))
        for t, c in zip(data["text"], data["conf"], strict=False)
        if t.strip() and float(c) >= 0
    ]
    text = pytesseract.image_to_string(clean, lang=langs).strip()
    mean = sum(w.conf for w in words) / len(words) if words else 0.0
    return OcrResult(text=text, mean_confidence=round(mean, 1), words=words, langs=langs)
