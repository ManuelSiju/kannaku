"""The 6 fictional owner documents, as PDF and PNG. Run from server/ with the ZEPHYRX close on the statement date:

    ../.venv/bin/python demo_assets/owner_docs/make_docs.py demo_assets/owner_docs 126.98

Every line is written the way app/pipeline/profile_extract.py reads it: one fact per line, ending in a full stop.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
NOTE = "Fictional document for the Kanakku demo."
ZEPHYRX_SHARES = 150


def rupees(amount: float) -> str:
    whole = str(round(amount))
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(([head] if head else []) + groups + [tail])


def documents(close: float) -> dict[str, list[str]]:
    return {
        "lakshmi_bank_passbook": [
            "Nila Cooperative Bank passbook.",
            "Account holder Lakshmi.",
            "Printed on 16 October 2026.",
            "Bank balance Rs 1,85,000.",
        ],
        "lakshmi_gold_loan_letter": [
            "Nila Finance sanction letter.",
            "Borrower Lakshmi.",
            "Sanctioned amount Rs 72,000.",
            "Repayment over 24 months.",
            "Gold loan EMI Rs 3,512 a month.",
        ],
        "lakshmi_health_cover": [
            "Nila Health family cover.",
            "Cover holder Lakshmi.",
            "Sum insured Rs 3,00,000.",
            "Health policy Rs 9,600 a year.",
        ],
        "arun_salary_slip": [
            "Periyar Soft Systems salary slip.",
            "Employee Arun.",
            "Pay month October 2026.",
            "Gross pay Rs 58,000.",
            "Deductions Rs 6,000.",
            "Net salary Rs 52,000 a month.",
        ],
        "arun_mf_statement": [
            "Nila Mutual consolidated statement.",
            "Investor Arun.",
            "Values as on 16 October 2026.",
            "Mutual fund holding Nila Bharat Index Fund value Rs 1,25,400 for 3210.455 units.",
            "Mutual fund holding Nila Short Term Debt Fund value Rs 48,599 for 1502.110 units.",
            "SIP Rs 5,000 a month into Nila Bharat Index Fund.",
        ],
        "arun_demat_holdings": [
            "Nila Demat holding statement.",
            "Client Arun.",
            "Values as on 16 October 2026.",
            "Stock holding PERIYARSOFT value Rs 42,300 for 60 shares.",
            "Stock holding MALABARTEA value Rs 18,750 for 250 shares.",
            f"Stock holding ZEPHYRX value Rs {rupees(close * ZEPHYRX_SHARES)} for {ZEPHYRX_SHARES} shares.",
        ],
    }


def write_pdf(path: Path, lines: list[str]) -> None:
    page = canvas.Canvas(str(path), pagesize=A4)
    page.setTitle(path.stem)
    width, height = A4
    y = height - 80
    page.setFont("Helvetica-Bold", 16)
    page.drawString(50, y, lines[0])
    page.setFont("Helvetica", 12)
    for line in lines[1:]:
        y -= 28
        page.drawString(50, y, line)
    page.setFont("Helvetica-Oblique", 9)
    page.drawString(50, 50, NOTE)
    page.save()


def write_png(path: Path, lines: list[str]) -> None:
    title, body, small = (ImageFont.truetype(FONT, size) for size in (42, 34, 24))
    image = Image.new("RGB", (1800, 120 + 70 * (len(lines) + 2)), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 60), lines[0], fill="black", font=title)
    y = 140
    for line in lines[1:]:
        draw.text((60, y), line, fill="black", font=body)
        y += 70
    draw.text((60, y + 30), NOTE, fill="#444444", font=small)
    image.save(path)


def main() -> None:
    out, close = Path(sys.argv[1]), float(sys.argv[2])
    for name, lines in documents(close).items():
        write_pdf(out / f"{name}.pdf", lines)
        write_png(out / f"{name}.png", lines)
        print(f"wrote {name}.pdf and .png")


if __name__ == "__main__":
    main()
