"""Cards and overlays for the demo video, 1920x1080. Run from the repo root: .venv/bin/python video/make_cards.py
Every claim here must be TRUE in docs/reports/claims_audit.md. COMMITS and TESTS come from git and the test run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "cards"
BG, ACCENT, WHITE, MUTED = "#0F1E1B", "#4FD1B2", "#FFFFFF", "#A9B8B3"
FONT = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
W, H = 1920, 1080
STEPS = [
    "Voice (Whisper)\nor photo",
    "Muse Spark reads\nthe paper",
    "Code computes\nevery number",
    "Council debates\n(Muse Spark)",
    "Evidence\ncheck",
    "Verdict",
]
TAGS = {
    "dani": ("Dani · funds", "#6B3FA0"),
    "sankz": ("Sankz · banking", "#1F4FA3"),
    "vick": ("Vick · stock tips", "#A84A12"),
    "alfii": ("Alfii · curator", "#0B5D52"),
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else FONT, size)


def card() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), BG)
    return image, ImageDraw.Draw(image)


def centred(d: ImageDraw.ImageDraw, y: int, text: str, f: ImageFont.FreeTypeFont, fill: str = WHITE) -> None:
    d.multiline_text((W / 2, y), text, font=f, fill=fill, anchor="ma", align="center", spacing=14)


def irdai() -> None:
    image, d = card()
    centred(d, 300, "26,667", font(190, True), ACCENT)
    centred(d, 560, "complaints of unfair selling\nagainst life insurers in one year", font(58))
    centred(d, 850, "Source: IRDAI Annual Report 2024-25 (FY25)", font(32), MUTED)
    image.save(OUT / "irdai.png")


def title() -> None:
    image, d = card()
    centred(d, 370, "Kanakku · ask before you sign", font(86, True))
    centred(d, 530, "A council of AI specialists on Meta Muse Spark", font(46), ACCENT)
    image.save(OUT / "title.png")


def architecture() -> None:
    box, gap, top = 270, 34, 400
    left = (W - 6 * box - 5 * gap) // 2
    for shown in range(1, len(STEPS) + 1):
        image, d = card()
        centred(d, 190, "How an answer is made", font(60, True))
        for i, text in enumerate(STEPS[:shown]):
            x = left + i * (box + gap)
            d.rounded_rectangle((x, top, x + box, top + 230), 24, outline=ACCENT, width=4)
            d.multiline_text((x + box / 2, top + 115), text, font=font(30), fill=WHITE, anchor="mm", align="center")
            if i:
                d.text((x - gap / 2, top + 115), "›", font=font(44, True), fill=ACCENT, anchor="mm")
        image.save(OUT / f"arch_{shown}.png")


def lower_thirds() -> None:
    for name, (text, colour) in TAGS.items():
        image = Image.new("RGBA", (620, 96), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)
        d.rounded_rectangle((0, 0, 619, 95), 18, fill=colour)
        d.text((310, 48), text, font=font(42, True), fill=WHITE, anchor="mm")
        image.save(OUT / f"tag_{name}.png")


def rubric() -> None:
    for name in ("Impact", "Use of Meta AI", "Technical depth"):
        image = Image.new("RGBA", (440, 70), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)
        d.rounded_rectangle((0, 0, 439, 69), 14, fill=(15, 30, 27, 230), outline=ACCENT, width=3)
        d.text((220, 35), name, font=font(32, True), fill=ACCENT, anchor="mm")
        image.save(OUT / f"rubric_{name.lower().replace(' ', '_')}.png")


def end(tests: str, repo: str) -> None:
    commits = subprocess.run(["git", "rev-list", "--count", "HEAD"], capture_output=True, text=True).stdout.strip()
    image, d = card()
    centred(d, 250, "Kanakku", font(96, True))
    centred(d, 400, "Built 27 October – 4 November 2026 on Meta Muse Spark", font(44), ACCENT)
    centred(d, 520, f"{commits} commits · {tests} automated tests", font(44))
    centred(d, 640, "Every number computed by code, never by the AI.", font(40), MUTED)
    if repo:
        centred(d, 780, repo, font(36), WHITE)
    image.save(OUT / "end.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    irdai(), title(), architecture(), lower_thirds(), rubric()
    end(sys.argv[1] if len(sys.argv) > 1 else "?", sys.argv[2] if len(sys.argv) > 2 else "")
    print(f"wrote {len(list(OUT.glob('*.png')))} cards")
