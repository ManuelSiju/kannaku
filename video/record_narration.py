"""Records the narration in Alfii's on-device voice. Each line is saved as a guardian note and read by the app's Read
aloud button, under the phone's Screen recorder. A placeholder until the owner records video/cam/vo.wav.
Run from the repo root with the server up, after a red answer exists, and the app on Home. Writes video/narration/.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, "scripts")
from record_scenes import Scenes  # noqa: E402

HERE = Path(__file__).parent
LINES = {
    "n01": "In one year, Indian families filed over twenty six thousand complaints of unfair selling against life insurers.",
    "n02": "Kanakku is a money adviser for families. It checks insurance, loans, stock tips and scam calls before you pay.",
    "n03": "Lakshmi shows the agent's brochure, and asks if fifteen lakh is really guaranteed.",
    "n04": "Muse Spark reads the paper. Code does every sum. The model never writes a number.",
    "n05": "The answer is stop, with the exact questions to ask the agent.",
    "n06": "The seller's claim is checked against the paper, and every amount shows where it came from.",
    "n07": "Her own figures stay on her screen. They are not spoken aloud unless she is private.",
    "n08": "Every answer takes the same path, and code checks each line before it is spoken.",
    "n09": "For a scam call, rules answer on their own, with no AI at all.",
    "n10": "A red answer appears in Arun's guardian view. He can call her, or leave a note.",
    "n11": "Family papers are read line by line and confirmed first. Arun's money stays out of the budget unless the family says so.",
    "n12": "Under the hood, every answer shows its facts, the vote, the privacy check, and the Meta model that ran it.",
    "n13": "Kanakku. Check before you pay.",
}


def main() -> int:
    token = next(x.split("=", 1)[1].strip() for x in open(".env.local") if x.startswith("KANAKKU_TOKEN="))
    api = httpx.Client(base_url="http://127.0.0.1:8013/v1", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    alert = api.get("/families/1/alerts").json()[0]["id"]
    out = HERE / "narration"
    out.mkdir(exist_ok=True)
    s = Scenes(sys.argv[1], out)
    wanted = sys.argv[2].split(",") if len(sys.argv) > 2 else list(LINES)
    s.start_recorder()
    for name in wanted:
        line = LINES[name]
        api.patch(f"/alerts/{alert}", json={"note": line}).raise_for_status()
        for _ in range(8):  # the note on Home must be this line before it is read
            s.p.tap_text(r"^Verdict$")
            time.sleep(1)
            s.p.tap_text(r"^Chat$")
            time.sleep(2)
            if s.p.find(re.escape(line[:24])):
                break
        s.p.tap_text(r"^Read aloud")
        time.sleep(4 + len(line.split()) / 2.0)
        print(name, flush=True)
    s.stop_recorder("all")
    split(out / "all.mp4", out, wanted)
    return 0


def split(source: Path, out: Path, names: list[str]) -> None:
    """One spoken block per line; the words "A note from Arun." at its start are left out."""
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(source), "-map", "0:a", "-af", "silencedetect=noise=-38dB:d=0.22",
         "-f", "null", "-"], capture_output=True, text=True,
    ).stderr  # fmt: skip
    marks = re.findall(r"silence_(start|end): ([\d.]+)", log)
    talk, begin = [], None
    for kind, value in marks:
        if kind == "end":
            begin = float(value)
        elif begin is not None:
            talk.append((begin, float(value)))
            begin = None
    blocks: list[list[tuple[float, float]]] = []
    for a, b in talk:
        if blocks and a - blocks[-1][-1][1] < 1.8:
            blocks[-1].append((a, b))
        else:
            blocks.append([(a, b)])
    blocks = [b for b in blocks if b[-1][1] - b[0][0] > 2]
    if len(blocks) != len(names):
        raise SystemExit(f"found {len(blocks)} spoken blocks for {len(names)} lines")
    info = {}
    for name, block in zip(names, blocks, strict=True):
        start, end = block[1][0] - 0.05, block[-1][1] + 0.15
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-to", str(end),
                        "-i", str(source), "-vn", str(out / f"{name}.wav")], check=True)  # fmt: skip
        info[name] = round(end - start, 2)
    print(info)


if __name__ == "__main__":
    sys.exit(main())
