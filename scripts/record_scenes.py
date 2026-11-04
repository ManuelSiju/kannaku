#!/usr/bin/env python3
"""Runs the demo scenes on a Samsung phone through the installed app and records each with the phone's Screen recorder,
sound from Media. Prints what each scene showed and how long it took. Start from a fresh make demo, with the app connected.

usage: record_scenes.py --serial RZCW11V6TLT --out video/raw
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from phone_smoke import TIP_Q, Phone  # noqa: E402

ENDOWMENT_Q = "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?"
SCAM_Q = "A man from the bank called. My KYC has expired and he asks me to tell him the OTP."


class Scenes:
    def __init__(self, serial: str, out: Path) -> None:
        self.p, self.out, self.serial, self.log = Phone(serial), out, serial, {}

    def screen(self) -> str:
        return " | ".join(self.p.label(n).replace("\n", " ") for n in self.p.nodes() if self.p.label(n))

    def scroll_to(self, pattern: str, tries: int = 14) -> None:
        for _ in range(tries):
            if self.p.find(pattern):
                return
            self.p.sh("input", "swipe", "540", "1750", "540", "850", "350")
            time.sleep(0.7)

    def start_recorder(self) -> None:
        """The phone's own Screen recorder with Media sound: it keeps the app's voices, and its toolbar is not filmed."""
        self.p.sh("cmd", "statusbar", "expand-settings")
        time.sleep(2)
        if self.p.find(r"^Expand"):
            self.p.tap_text(r"^Expand")
            time.sleep(1.2)
        self.p.tap_text(r"Screen recorder")
        time.sleep(2)
        self.p.tap_text(r"^Media$")
        time.sleep(0.5)
        self.p.tap_text(r"^Start recording$")
        time.sleep(4.5)  # its countdown

    def stop_recorder(self, name: str) -> None:
        self.p.sh("input", "tap", "972", "180")
        time.sleep(3)
        folder = "/sdcard/DCIM/Screen recordings"
        newest = self.p.sh("ls", "-t", folder.replace(" ", "\\ ")).split("\n")[0].strip()
        subprocess.run(
            ["adb", "-s", self.serial, "pull", f"{folder}/{newest}", str(self.out / f"{name}.mp4")], capture_output=True
        )

    def record(self, name: str, action) -> None:
        self.start_recorder()
        t0 = time.monotonic()
        notes: dict[str, str] = {}
        try:
            action(notes)
            notes["result"] = "ok"
        except Exception as e:  # a failed scene is a finding, the next one still runs
            notes["result"] = f"FAILED: {e}"[:300]
        notes["seconds"] = f"{time.monotonic() - t0:.1f}"
        time.sleep(1)
        self.stop_recorder(name)
        self.log[name] = notes
        print(name, json.dumps(notes, ensure_ascii=False)[:1100], flush=True)
        if notes["result"] != "ok":
            raise SystemExit(f"stopped at {name}")

    def settings_toggle(self, pattern: str) -> None:
        """Between recordings only: the Settings screen shows the server address."""
        for _ in range(6):  # the recorder's closing overlay can swallow a tap
            self.p.tap_text(r"^Settings$")
            time.sleep(2)
            if self.p.find(r"^Voice and language"):
                break
        self.scroll_to(pattern)
        self.p.tap_text(pattern)
        time.sleep(1.2)

    def home(self) -> None:
        for _ in range(4):
            if self.p.find(r"^(Chat|Alerts)$"):
                return
            self.p.sh("input", "keyevent", "KEYCODE_BACK")
            time.sleep(1.2)

    def ask(self, question: str, ready: str = r"Alfii's answer|Retry") -> None:
        self.p.type_into(0, question)
        self.p.hide_keyboard()
        self.p.tap_text(r"^Send$")
        self.p.wait(ready, 120)

    def endowment(self, n: dict) -> None:
        self.p.tap_text(r"Show a paper or photo")
        time.sleep(1.2)
        self.p.tap_text(r"Choose a PDF")
        time.sleep(2.5)
        self.scroll_to(r"^kanakavalli_brochure.pdf")
        self.p.tap_text(r"^kanakavalli_brochure.pdf")
        time.sleep(2)
        t = time.monotonic()
        self.ask(ENDOWMENT_Q)
        n["answer_seconds"] = f"{time.monotonic() - t:.1f}"
        time.sleep(2)
        n["verdict"] = self.screen()[:400]
        self.scroll_to(r"Ask him this")
        time.sleep(2)

    def council(self, n: dict) -> None:
        self.scroll_to(r"Hear the council")
        self.p.tap_text(r"Hear the council")
        time.sleep(1.5)
        n["lines"] = self.screen()[:900]
        time.sleep(30)  # the whole council plays
        self.p.sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)

    def why(self, n: dict) -> None:
        self.p.sh("input", "swipe", "540", "700", "540", "1800", "300")
        time.sleep(0.5)
        self.p.sh("input", "swipe", "540", "700", "540", "1800", "300")
        self.scroll_to(r"^Why")
        self.p.tap_text(r"^Why")
        time.sleep(3)
        n["why"] = self.screen()[:800]
        self.p.sh("input", "swipe", "540", "1750", "540", "850", "700")
        time.sleep(2.5)
        self.p.sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)

    def scam(self, n: dict) -> None:
        self.home()
        self.p.tap_text(r"^Chat$")
        time.sleep(1)
        t = time.monotonic()
        self.ask(SCAM_Q)
        n["answer_seconds"] = f"{time.monotonic() - t:.1f}"
        time.sleep(1.5)
        self.p.tap_text(r"^Read aloud")
        time.sleep(7)
        n["screen"] = self.screen()[:500]

    def alerts(self, n: dict) -> None:
        self.p.tap_text(r"^Alerts")
        time.sleep(3)
        n["screen"] = self.screen()[:600]
        self.scroll_to(r"^Note for Amma")
        self.p.tap_text(r"^Note for Amma")
        time.sleep(1.2)
        self.p.sh("input", "text", "Please%swait%sfor%sme%sbefore%syou%ssign")
        time.sleep(1.5)
        self.p.tap_text(r"^Save$")
        time.sleep(2.5)

    def amma(self, n: dict) -> None:
        self.p.tap_text(r"^Chat$")
        time.sleep(4)
        n["screen"] = self.screen()[:300]
        self.p.tap_text(r"^Read aloud")
        time.sleep(5)

    def upload(self, name: str) -> None:
        self.scroll_to(r"Show paper")
        self.p.tap_text(r"Show paper")
        time.sleep(1.2)
        self.p.tap_text(r"Choose a PDF")
        time.sleep(2.5)
        self.scroll_to(rf"^{name}.pdf")
        self.p.tap_text(rf"^{name}.pdf")
        self.p.wait(r"Save \d", 40)
        time.sleep(3)

    def details(self, n: dict) -> None:
        self.p.tap_text(r"^My Details")
        time.sleep(2.5)
        self.scroll_to(r"^Arun$")
        self.p.tap_text(r"^Arun$")
        time.sleep(1.5)
        self.upload("arun_demat_holdings")
        n["confirm"] = self.screen()[:600]
        self.p.tap_text(r"^Save \d")
        time.sleep(3)
        self.p.sh("input", "swipe", "540", "1750", "540", "850", "600")
        time.sleep(2)

    def tip(self, n: dict) -> None:
        self.home()
        self.p.tap_text(r"^Chat$")
        time.sleep(1)
        t = time.monotonic()
        self.ask(TIP_Q, r"^The council$|Retry")  # with earphones on the council opens and plays by itself
        n["answer_seconds"] = f"{time.monotonic() - t:.1f}"
        time.sleep(1.5)
        n["lines"] = self.screen()[:900]
        time.sleep(30)
        self.p.sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)

    def hood(self, n: dict) -> None:
        self.home()
        self.p.tap_text(r"^Chat$")
        time.sleep(1)
        self.p.sh("input", "swipe", "280", "180", "280", "180", "1100")  # long-press the Kanakku title
        time.sleep(3)
        n["top"] = self.screen()[:500]
        for _ in range(4):
            self.p.sh("input", "swipe", "540", "1750", "540", "900", "700")
            time.sleep(2)
        n["bottom"] = self.screen()[:600]
        self.p.sh("input", "keyevent", "KEYCODE_BACK")
        time.sleep(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", required=True)
    ap.add_argument("--out", default="video/raw")
    ap.add_argument("--start", type=int, default=1, help="5 resumes after the first four scenes")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = Scenes(a.serial, out)
    if a.start <= 1:
        s.record("scene_01_endowment", s.endowment)
        s.record("scene_02_council", s.council)
        s.record("scene_03_why", s.why)
        s.record("scene_04_scam", s.scam)
    s.home()
    s.settings_toggle(r"^Guardian view")
    s.record("scene_05_alerts", s.alerts)
    s.settings_toggle(r"^Guardian view")
    s.record("scene_06_note", s.amma)
    s.record("scene_07_details", s.details)
    s.home()
    s.settings_toggle(r"^I use earphones")
    s.record("scene_08_tip", s.tip)
    s.home()
    s.settings_toggle(r"^I use earphones")
    s.record("scene_09_hood", s.hood)
    (out / "scenes.json").write_text(json.dumps(s.log, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
