"""Renders video/kanakku_demo.mp4 from video/edit_list.json. Run from the repo root: make video
Each shot is a card or a phone clip. Phone clips keep their own recorded sound, which is the app's real voices.
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
WORK = HERE / "work"
BG, ACCENT, WHITE, MUTED = "#0F1E1B", "#4FD1B2", "#FFFFFF", "#A9B8B3"
FONT = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
PHONE_H, PHONE_W, PHONE_X, PHONE_Y = 1040, 468, 170, 20
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30"]
AUD = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def run(*cmd: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *cmd], check=True)


def panel(shot: dict, path: Path) -> None:
    """The background with the shot's caption, right of the phone."""
    image = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(image)
    x, y = 760, 250
    if shot.get("rubric"):
        d.rounded_rectangle((x, 90, x + 420, 150), 12, outline=ACCENT, width=3)
        d.text((x + 210, 120), shot["rubric"], font=ImageFont.truetype(BOLD, 28), fill=ACCENT, anchor="mm")
    if shot.get("who"):
        d.text((x, y), shot["who"], font=ImageFont.truetype(BOLD, 40), fill=ACCENT)
        y += 70
    title = ImageFont.truetype(BOLD, 58)
    for line in textwrap.wrap(shot.get("title", ""), 30):
        d.text((x, y), line, font=title, fill=WHITE)
        y += 76
    y += 24
    body = ImageFont.truetype(FONT, 38)
    for line in textwrap.wrap(shot.get("text", ""), 46):
        d.text((x, y), line, font=body, fill=MUTED)
        y += 54
    if shot.get("note"):
        d.text((x, 960), shot["note"], font=ImageFont.truetype(FONT, 28), fill=MUTED)
    image.save(path)


def sound(shot: dict, seconds: float, out: Path) -> None:
    """Narration where the shot has it, otherwise true silence. Nothing else is ever added."""
    silence = ["-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=r=48000:cl=stereo"]
    if shot.get("narration"):
        delay = int(shot.get("narration_at", 0.3) * 1000)
        run(*silence, "-i", str(HERE / "narration" / shot["narration"]), "-filter_complex",
            f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={delay}|{delay}[n];[0:a][n]amix=2:duration=first:normalize=0",
            "-t", str(seconds), *AUD, str(out))  # fmt: skip
    else:
        run(*silence, *AUD, str(out))


def push(seconds: float) -> str:
    """A slow push in, so no frame stands still."""
    return (
        "scale=w='trunc((1920+12.8*t)/2)*2':h='trunc((1080+7.2*t)/2)*2':eval=frame:flags=lanczos,"
        "crop=1920:1080:(iw-1920)/2:(ih-1080)/2,setsar=1"
    )


def card(shot: dict, out: Path, seconds: float) -> None:
    audio = out.with_suffix(".m4a")
    sound(shot, seconds, audio)
    if "%d" in shot["card"]:  # numbered cards, one after another over the shot
        count = len(list((HERE / "cards").glob(shot["card"].replace("%d", "*"))))
        image = ["-framerate", f"{count}/{seconds}", "-i", str(HERE / "cards" / shot["card"].replace("%d", "%d"))]
        image[0:0] = ["-start_number", "1"]
    else:
        image = ["-loop", "1", "-framerate", "30", "-t", str(seconds), "-i", str(HERE / "cards" / shot["card"])]
    run(*image, "-i", str(audio), "-vf", f"fps=30,scale=1920:1080,{push(seconds)}", *ENC, *AUD, "-t", str(seconds),
        str(out))  # fmt: skip


def clip(shot: dict, out: Path, background: Path) -> float:
    start, end, speed = shot["in"], shot["out"], shot.get("speed", 1)
    seconds = (end - start) / speed
    source = str(HERE / "raw" / shot["clip"])
    trim = f"trim={start}:{end},setpts=(PTS-STARTPTS)/{speed},fps=30"
    if "zoom" in shot:  # a part of the phone fills the frame, with a box around it for the first 1.5 s
        y = shot["zoom"]
        box = f"drawbox=x=14:y=14:w=iw-28:h=ih-28:color=0x4FD1B2:t=10:enable='lt(t,1.5)'"
        video = (
            f"[1:v]{trim},crop=1080:608:0:{y},scale=1920:1080:flags=lanczos,setsar=1,{push(seconds)},{box}[v]"
        )
    else:
        crop = shot.get("crop_top", 120)  # the status bar stays out of the film
        video = (
            f"[1:v]{trim},crop=1080:{2400 - crop}:0:{crop},scale={PHONE_W}:-2:flags=lanczos[p];"
            f"[0:v][p]overlay={PHONE_X}:(H-h)/2,{push(seconds)}[v]"
        )
    inputs = ["-loop", "1", "-framerate", "30", "-t", str(seconds), "-i", str(background), "-i", source]
    if shot.get("voice"):
        args = ["-filter_complex", f"{video};[1:a]atrim={start}:{end},asetpts=PTS-STARTPTS[a]", "-map", "[v]", "-map", "[a]"]
    else:
        audio = out.with_suffix(".m4a")
        sound(shot, seconds, audio)
        args = ["-filter_complex", video, "-map", "[v]", "-map", "2:a"]
        inputs += ["-i", str(audio)]
    run(*inputs, *args, *ENC, *AUD, "-t", str(seconds), str(out))
    return seconds


def stamp(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main() -> None:
    WORK.mkdir(exist_ok=True)
    shots = json.loads((HERE / "edit_list.json").read_text())["shots"]
    parts, subs, now = [], [], 0.0
    for i, shot in enumerate(shots):
        out = WORK / f"shot_{i:02}.mp4"
        if "card" in shot:
            seconds = shot["seconds"]
            card(shot, out, seconds)
        elif "zoom" in shot:
            seconds = clip(shot, out, HERE / "cards" / "title.png")
        else:
            background = WORK / f"panel_{i:02}.png"
            panel(shot, background)
            seconds = clip(shot, out, background)
        parts.append(out)
        for line in shot.get("captions", []):
            subs.append((now + line["at"], now + line["to"], line["text"]))
        now += seconds
    (WORK / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    joined = WORK / "joined.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(WORK / "list.txt"), "-c", "copy", str(joined))
    srt = HERE / "kanakku.srt"
    wrap = lambda t: "\n".join(textwrap.wrap(t, 42)[:2])  # noqa: E731
    srt.write_text("\n".join(f"{n}\n{stamp(a)} --> {stamp(b)}\n{wrap(t)}\n" for n, (a, b, t) in enumerate(subs, 1)))
    style = (  # right of the phone, under the panel text; sizes are on the subtitle canvas of 384 x 288
        "FontName=Noto Sans,FontSize=11,PrimaryColour=&HFFFFFF&,BackColour=&H10000000&,BorderStyle=4,"
        "Alignment=1,MarginL=152,MarginR=16,MarginV=26"
    )
    vf = f"subtitles={srt}:force_style='{style}'" if subs else "null"
    run("-i", str(joined), "-vf", vf, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        *ENC, *AUD, "-movflags", "+faststart", str(HERE / "kanakku_demo.mp4"))  # fmt: skip
    print(f"rendered {now:.1f} s")


if __name__ == "__main__":
    main()
