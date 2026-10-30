"""Generate FICTIONAL demo assets: a 3-page insurance brochure (PDF + PNG pages), a stock tip for the made-up
ticker ZEPHYRX (text + PNG), and its synthetic price/volume CSV with a pump pattern. Deterministic.

No real companies, products or brochures. Run: make demo-assets
"""

from __future__ import annotations

import csv
import datetime as dt
import random
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import SERVER_ROOT  # noqa: E402

OUT = SERVER_ROOT / "demo_assets"
INSURER = "Kanakavalli Life Assurance (fictional)"
PLAN = "Kanakavalli Sthira Endowment Plan"
FOOTER = "FICTIONAL DOCUMENT - FOR THE KANAKKU DEMO ONLY - NOT A REAL PRODUCT"

PAGES: list[tuple[str, list[str]]] = [
    (
        PLAN,
        [
            f"by {INSURER}",
            "A savings plan with life cover for your family.",
            "",
            "Annual premium: Rs. 50,000",
            "Premium paying term: 15 years",
            "Policy term: 15 years",
            "Sum assured: Rs. 7,50,000 (guaranteed)",
            "",
            "Get up to Rs. 15,00,000 at maturity!*",
        ],
    ),
    (
        "Benefit illustration",
        [
            "Total premiums paid over 15 years: Rs. 7,50,000",
            "",
            "Illustrated maturity value at 4% bonus rate: Rs. 10,20,000",
            "Illustrated maturity value at 8% bonus rate: Rs. 15,00,000",
            "",
            "Death benefit: sum assured plus bonuses added till then.",
            "Maturity is paid at the end of year 15.",
        ],
    ),
    (
        "Important terms",
        [
            "Bonus rates are not guaranteed and may change every year.",
            "Surrender value in the first 3 years: nil.",
            "* The Rs. 15,00,000 figure is illustrative, at an 8% bonus rate.",
            "Please read the policy document before you sign.",
        ],
    ),
]

TIP_TEXT = (
    "ZEPHYRX LTD - BIG NEWS COMING!\n"
    "Target Rs. 180 in 2 weeks. Upper circuit guaranteed.\n"
    "Buy before Monday, only for our VIP group members.\n"
    "Already up 5% every day this month - do not miss!\n"
    "(fictional message for the Kanakku demo)"
)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "Arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def brochure_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"{PLAN} (fictional)")
    w, h = A4
    for title, lines in PAGES:
        c.setFont("Helvetica-Bold", 22)
        c.drawString(60, h - 90, title)
        c.setFont("Helvetica", 14)
        y = h - 140
        for line in lines:
            c.drawString(60, y, line)
            y -= 26
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(60, 40, FOOTER)
        c.showPage()
    c.save()


def page_png(path: Path, title: str, lines: list[str]) -> None:
    img = Image.new("RGB", (1240, 1754), "white")  # A4 at 150 dpi
    d = ImageDraw.Draw(img)
    d.text((100, 120), title, fill="black", font=font(56))
    y = 240
    for line in lines:
        d.text((100, y), line, fill="black", font=font(36))
        y += 64
    d.text((100, 1660), FOOTER, fill="gray", font=font(22))
    img.save(path)


def trading_days(start: dt.date, n: int) -> list[dt.date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    return days


def zephyrx_csv(path: Path) -> None:
    """90 quiet days near Rs. 40, then 30 days of mostly 5% jumps on rising volume (pump pattern)."""
    rng = random.Random(42)
    closes = [40 + rng.uniform(-0.6, 0.6) for _ in range(90)]
    vols = [20_000 + rng.uniform(-2_000, 2_000) for _ in range(90)]
    for i in range(30):
        closes.append(closes[-1] * (1.05 if i % 4 else 1.012))
        vols.append(150_000 if i >= 25 else 45_000 + 1_500 * i)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "volume"])
        for day, c, v in zip(trading_days(dt.date(2026, 5, 4), 120), closes, vols, strict=True):
            w.writerow([day.isoformat(), f"{c:.2f}", int(v)])


def tip_png(path: Path) -> None:
    img = Image.new("RGB", (1080, 720), (225, 245, 220))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 80, 1020, 640), radius=30, fill="white")
    y = 130
    for line in TIP_TEXT.splitlines():
        d.text((100, y), line, fill="black", font=font(34))
        y += 90
    img.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stocks").mkdir(exist_ok=True)
    brochure_pdf(OUT / "kanakavalli_brochure.pdf")
    for i, (title, lines) in enumerate(PAGES, start=1):
        page_png(OUT / f"kanakavalli_brochure_p{i}.png", title, lines)
    shutil.copy(OUT / "kanakavalli_brochure_p1.png", OUT / "sample_brochure.png")  # used by make check-models
    zephyrx_csv(OUT / "stocks" / "ZEPHYRX.csv")
    (OUT / "zephyrx_tip.txt").write_text(TIP_TEXT + "\n")
    tip_png(OUT / "zephyrx_tip.png")
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(SERVER_ROOT)}")


if __name__ == "__main__":
    main()
