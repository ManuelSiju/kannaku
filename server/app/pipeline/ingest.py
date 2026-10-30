"""Step 1: turn audio / images / PDF / DOCX / text into a transcript and numbered pages (evidence)."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Literal

from pydantic import BaseModel

from app.providers.ocr import OcrUnavailable, ocr_image
from app.providers.stt import STTProvider

log = logging.getLogger(__name__)

IMAGE_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/webp")


class Upload(BaseModel):
    filename: str
    data: bytes
    mime: str


class Page(BaseModel):
    source: str  # "page_N"
    text: str
    kind: Literal["image", "pdf", "docx", "text"]
    ocr_text: str | None = None  # independent reading for photos (two-readings check)
    image: bytes | None = None


class Ingested(BaseModel):
    transcript: str
    language: str | None
    pages: list[Page]
    problems: list[str] = []

    @property
    def images(self) -> list[bytes]:
        return [p.image for p in self.pages if p.image is not None]

    @property
    def doc_text(self) -> str:
        return "\n".join(p.text for p in self.pages)


def _kind(upload: Upload) -> str:
    name, mime = upload.filename.lower(), upload.mime.lower()
    if mime in IMAGE_TYPES or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    if mime == "application/pdf" or name.endswith(".pdf"):
        return "pdf"
    if name.endswith(".docx") or "wordprocessingml" in mime:
        return "docx"
    return "text"


def _pdf_pages(data: bytes) -> list[tuple[str, bytes | None]]:
    """(text, rendered page image if the page had no text layer)."""
    import pdfplumber

    out: list[tuple[str, bytes | None]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if text:
                out.append((text, None))
            else:
                buf = io.BytesIO()
                page.to_image(resolution=200).original.save(buf, format="PNG")
                out.append(("", buf.getvalue()))
    return out


def _docx_text(data: bytes) -> str:
    import docx

    return "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs if p.text.strip())


async def _ocr(data: bytes, problems: list[str]) -> str:
    try:
        return (await asyncio.to_thread(ocr_image, data)).text
    except OcrUnavailable as e:
        problems.append(f"ocr: {e}")
    except ValueError as e:
        problems.append(f"ocr: {e}")
    return ""


async def ingest(*, text: str | None, audio: Upload | None, files: list[Upload], stt: STTProvider | None) -> Ingested:
    problems: list[str] = []
    parts, language = [], None
    if audio is not None:
        if stt is None:
            problems.append("stt: no speech-to-text provider")
        else:
            try:
                t = await stt.transcribe(audio.data, audio.mime)
                parts.append(t.text)
                language = t.language
            except Exception as e:  # provider failures are reported, never fatal
                problems.append(f"stt: {type(e).__name__}: {e}")
    if text:
        parts.append(text.strip())

    pages: list[Page] = []

    def add(text: str, kind: str, **extra: object) -> None:
        pages.append(Page(source=f"page_{len(pages) + 1}", text=text, kind=kind, **extra))  # type: ignore[arg-type]

    for up in files:
        kind = _kind(up)
        if kind == "image":
            ocr_text = await _ocr(up.data, problems)
            add(ocr_text, "image", ocr_text=ocr_text, image=up.data)
        elif kind == "pdf":
            for page_text, image in await asyncio.to_thread(_pdf_pages, up.data):
                if image is None:
                    add(page_text, "pdf")
                else:
                    ocr_text = await _ocr(image, problems)
                    add(ocr_text, "image", ocr_text=ocr_text, image=image)
        elif kind == "docx":
            add(await asyncio.to_thread(_docx_text, up.data), "docx")
        else:
            add(up.data.decode("utf-8", errors="replace"), "text")
    return Ingested(
        transcript=" ".join(p for p in parts if p).strip(), language=language, pages=pages, problems=problems
    )
