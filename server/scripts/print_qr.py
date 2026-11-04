"""Prints the phone-setup QR code. Address and token come from the environment (never argv, which ps shows).
The app's Settings -> Scan code reads kanakku://connect?url=...&token=..."""

from __future__ import annotations

import os
from urllib.parse import urlencode

import qrcode


def connect_link(url: str, token: str) -> str:
    return "kanakku://connect?" + urlencode({"url": url, "token": token})


if __name__ == "__main__":
    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(connect_link(os.environ["KANAKKU_URL"], os.environ["KANAKKU_TOKEN"]))
    qr.print_ascii(invert=True)
