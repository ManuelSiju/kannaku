"""Upload limits. The type is decided by the file's first bytes, not by its name or the client's Content-Type."""

from __future__ import annotations

from typing import Literal

from app.api.errors import ApiError
from app.config import Settings
from app.pipeline.ingest import Upload

Kind = Literal["audio", "image", "pdf", "docx"]
MB = 1024 * 1024
MIME = {"image": None, "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}  # fmt: skip


def sniff(data: bytes) -> tuple[Kind, str] | None:
    """(kind, mime) from magic bytes, or None if the type is not allowed."""
    head = data[:16]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image", "image/webp"
    if head.startswith(b"%PDF-"):
        return "pdf", "application/pdf"
    if head.startswith(b"PK\x03\x04") and b"word/" in data[:4096]:
        return "docx", MIME["docx"]  # type: ignore[return-value]
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio", "audio/wav"
    if head.startswith(b"OggS"):
        return "audio", "audio/ogg"
    if head.startswith(b"fLaC"):
        return "audio", "audio/flac"
    if head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "audio", "audio/mpeg"
    if head[4:8] == b"ftyp":
        return "audio", "audio/mp4"  # m4a / aac from phone recorders
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio", "audio/webm"
    if head.startswith(b"#!AMR"):
        return "audio", "audio/amr"
    return None


def limit_mb(kind: Kind, s: Settings) -> float:
    return {"audio": s.max_audio_mb, "image": s.max_image_mb, "pdf": s.max_pdf_mb, "docx": s.max_pdf_mb}[kind]


def check(up: Upload, s: Settings, *, audio: bool) -> Upload:
    """Returns the upload with its sniffed MIME type, or raises 413 / 415 in the standard error format."""
    found = sniff(up.data)
    if found is None or (found[0] == "audio") != audio:
        allowed = "an audio recording" if audio else "a photo (JPG, PNG, WebP), a PDF or a Word file"
        raise ApiError(415, "unsupported_type", f"{up.filename}: this file type is not accepted; send {allowed}.")
    kind, mime = found
    if len(up.data) > limit_mb(kind, s) * MB:
        raise ApiError(
            413, "file_too_large", f"{up.filename}: {len(up.data) / MB:.1f} MB is over the {limit_mb(kind, s):g} MB "
            f"limit for {kind} files."
        )  # fmt: skip
    return up.model_copy(update={"mime": mime})


def check_all(audio: Upload | None, files: list[Upload], s: Settings) -> tuple[Upload | None, list[Upload]]:
    if len(files) > s.max_files:
        raise ApiError(413, "too_many_files", f"Send at most {s.max_files} files at a time.")
    return (check(audio, s, audio=True) if audio else None), [check(f, s, audio=False) for f in files]
