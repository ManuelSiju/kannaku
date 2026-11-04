#!/usr/bin/env python3
"""Drives the INSTALLED Kanakku app on a phone or emulator through adb, like a person would (no test build):
fresh start -> Welcome -> Start -> Skip -> Settings (server address + token) -> Save and test connection ->
back -> type a question -> wait for the answer. Saves screenshots. Exit code 0 when the answer has the expected word.

usage: phone_smoke.py --url http://192.168.1.10:8013 --token XXX [--question "..."] [--expect Stop] [--shots DIR]
       [--serial emulator-5554] [--keep-data] [--connect-only]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "dev.kanakku.kanakku"
TIP_Q = (
    "I got this message: ZEPHYRX LTD big news coming, target Rs 180 in 2 weeks, upper circuit guaranteed. "
    "Should I put 1 lakh in it?"
)


class Phone:
    def __init__(self, serial: str | None) -> None:
        self.base = ["adb"] + (["-s", serial] if serial else [])

    def sh(self, *args: str, check: bool = True) -> str:
        r = subprocess.run(self.base + ["shell", *args], capture_output=True, text=True, timeout=60)
        if check and r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip())
        return r.stdout

    def nodes(self) -> list[dict[str, str]]:
        for _ in range(8):
            out = self.sh("uiautomator", "dump", "/sdcard/kanakku_ui.xml", check=False)
            if "dumped" in out:
                xml = subprocess.run(self.base + ["exec-out", "cat", "/sdcard/kanakku_ui.xml"], capture_output=True)
                try:
                    return [n.attrib for n in ET.fromstring(xml.stdout).iter("node")]
                except ET.ParseError:
                    pass
            time.sleep(1)
        return []

    def label(self, n: dict[str, str]) -> str:
        return f"{n.get('text', '')} {n.get('content-desc', '')}".strip()

    def find(self, pattern: str, nodes: list[dict[str, str]] | None = None) -> dict[str, str] | None:
        rx = re.compile(pattern, re.I | re.S)
        return next((n for n in (nodes or self.nodes()) if rx.search(self.label(n))), None)

    def wait(self, pattern: str, timeout: float = 60) -> dict[str, str]:
        end = time.time() + timeout
        while time.time() < end:
            n = self.find(pattern)
            if n:
                return n
            time.sleep(1.5)
        seen = " | ".join(self.label(n) for n in self.nodes() if self.label(n))[:800]
        raise TimeoutError(f"'{pattern}' not on screen after {timeout:.0f}s. On screen: {seen}")

    def tap(self, node: dict[str, str]) -> None:
        x1, y1, x2, y2 = map(int, re.findall(r"\d+", node["bounds"]))
        self.sh("input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
        time.sleep(1.2)

    def tap_text(self, pattern: str, timeout: float = 30) -> None:
        self.tap(self.wait(pattern, timeout))

    def type_into(self, index: int, text: str) -> None:
        fields = [n for n in self.nodes() if n.get("class") == "android.widget.EditText"]
        self.tap(fields[index])
        self.sh("input", "keyevent", "KEYCODE_MOVE_END")
        self.sh("input", "keyevent", *["KEYCODE_DEL"] * 80)
        escaped = re.sub(r"([\\'\"()&;<>|$`!?*#~])", r"\\\1", text).replace(" ", "%s")
        self.sh("input", "text", escaped)
        time.sleep(0.8)

    def back(self) -> None:
        self.sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.5)

    def hide_keyboard(self) -> None:
        if "mInputShown=true" in self.sh("dumpsys", "input_method", check=False):
            self.back()

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(subprocess.run(self.base + ["exec-out", "screencap", "-p"], capture_output=True).stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--question", default=TIP_Q)
    ap.add_argument("--expect", default="Stop", help="word expected in the answer (Stop / Careful / Looks fine)")
    ap.add_argument("--shots", default="")
    ap.add_argument("--serial", default=None)
    ap.add_argument("--keep-data", action="store_true", help="do not reset the app (test an existing setup)")
    ap.add_argument("--connect-only", action="store_true", help="stop after Test connection")
    a = ap.parse_args()
    p, shots = Phone(a.serial), Path(a.shots) if a.shots else None
    t0 = time.time()

    def step(msg: str) -> None:
        print(f"[{time.time() - t0:5.1f}s] {msg}", flush=True)

    if not a.keep_data:
        p.sh("pm", "clear", PACKAGE)
    p.sh("monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")
    if not a.keep_data:
        p.wait(r"Hello, I'm Alfii", 60)
        step("app opened: Welcome screen")
        p.tap_text(r"^Start")
        p.tap_text(r"Skip all")
    p.wait(r"Hold and talk", 30)
    step("Home screen")
    p.tap_text(r"^Settings$")
    p.type_into(0, a.url)
    p.type_into(1, a.token)
    p.hide_keyboard()
    p.tap_text(r"Save and test connection")
    connected = p.wait(r"Connected|can't reach|token is missing|not work", 40)
    step(f"Test connection: {p.label(connected)}")
    if "Connected" not in p.label(connected):
        return 1
    if shots:
        p.screenshot(shots / "settings_connected.png")
    nodes = p.nodes()
    for want in (r"App version", r"Server version", r"Model provider"):
        row = p.find(want, nodes)
        step(f"  {p.label(row) if row else want + ': not visible'}")
    p.back()
    p.wait(r"Hold and talk", 20)
    if a.connect_only:
        return 0
    p.type_into(0, a.question)
    p.hide_keyboard()
    p.tap_text(r"^Send$")
    step("question sent")
    answer = p.wait(r"Alfii's answer|The council|Stop|Careful|Looks fine|Retry", 240)
    if "The council" in p.label(answer) or p.find(r"Skip to Alfii"):
        p.back()
    verdict = p.wait(r"^(Stop|Careful|Looks fine)$|Retry", 30)
    word = re.search(r"Stop|Careful|Looks fine|Retry", p.label(verdict)).group(0)  # type: ignore[union-attr]
    step(f"answer on the phone: {word}")
    if shots:
        p.screenshot(shots / "answer.png")
    return 0 if word == a.expect else 1


if __name__ == "__main__":
    sys.exit(main())
