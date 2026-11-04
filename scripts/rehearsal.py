#!/usr/bin/env python3
"""Fresh-clone rehearsal of docs/OWNER_GUIDE.md: clones the repository into a NEW folder and runs the guide's
commands in order, as typed by a person (a pseudo-terminal answers the questions make start asks), recording every
command, its output and its time into docs/rehearsal_<n>.md. Also: make start twice, make stop twice, a "laptop
restart" (server killed hard, stale pid file left behind), a Wi-Fi address change (the app is pointed at another
address of the same laptop), the Meta key flow against the fake Meta server, local mode with no key.

usage: scripts/rehearsal.py <n>   (needs: an Android emulator or USB phone, Ollama with the model pulled)
Steps 2.2-2.4 of the guide (sudo apt, the uv / Ollama / Flutter installers) change the machine itself; they are not
re-run: the rehearsal checks that what they install is present.
"""

from __future__ import annotations

import os
import pty
import re
import select
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\r")
SERIAL = os.environ.get("DEVICE", "emulator-5554")  # never a real phone: phone_smoke.py wipes the app's data


class Rehearsal:
    def __init__(self, n: int) -> None:
        self.n = n
        self.dir = Path.home() / f"kanakku-rehearsal-{n}"
        self.rows: list[tuple[str, str, str, float, str]] = []  # section, command, result, seconds, output
        self.failed = False

    # ------------------------------------------------------------------ running commands
    def run(self, section: str, cmd: str, *, answers: list[str] | None = None, expect: str = "", cwd: Path | None = None,
            env: dict[str, str] | None = None, timeout: float = 1800, ok_codes: tuple[int, ...] = (0,)) -> str:  # fmt: skip
        """Runs cmd in bash inside a pseudo-terminal (like a person's terminal); types `answers` at each prompt."""
        t0 = time.time()
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(cwd or self.dir)
            os.execve("/bin/bash", ["bash", "-lc", cmd], {**os.environ, **(env or {})})
        out, pending = b"", list(answers or [])
        end = t0 + timeout
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
                tail = ANSI.sub("", out[-200:].decode(errors="replace")).rstrip()
                if pending and (tail.endswith(":") or tail.endswith("]")):
                    time.sleep(0.3)
                    os.write(fd, (pending.pop(0) + "\n").encode())
        try:
            _, status = os.waitpid(pid, 0)
            code = os.waitstatus_to_exitcode(status)
        except ChildProcessError:
            code = -1
        text = ANSI.sub("", out.decode(errors="replace"))
        ok = code in ok_codes and (not expect or re.search(expect, text) is not None)
        self.failed |= not ok
        secs = time.time() - t0
        self.rows.append((section, cmd, "✔ pass" if ok else f"✘ FAIL (exit {code})", secs, text))
        print(f"{'✔' if ok else '✘'} [{secs:6.1f}s] {section}: {cmd}", flush=True)
        if not ok:
            print(text[-1500:], flush=True)
        return text

    def note(self, section: str, what: str, result: str) -> None:
        self.rows.append((section, what, result, 0.0, ""))
        print(f"  {result}  {section}: {what}", flush=True)

    # ------------------------------------------------------------------ the rehearsal
    def go(self) -> None:
        if self.dir.exists():
            shutil.rmtree(self.dir)
        for tool, guide in (("git", "2.2"), ("curl", "2.2"), ("make", "2.2"), ("tesseract", "2.2"), ("ffmpeg", "2.2"),
                            ("adb", "2.2"), ("uv", "2.3"), ("ollama", "2.3"), ("flutter", "2.4")):  # fmt: skip
            path = shutil.which(tool)
            self.note(f"{guide} install tools", f"`{tool}` present", f"✔ {path}" if path else "✘ missing")
            self.failed |= path is None

        self.run("2.5 download", f"git clone {ROOT} {self.dir}", cwd=Path.home(), expect="Cloning into")
        self.run("2.6 set up", "make setup", expect="setup done. Next: make doctor")
        self.run("2.7 AI model", "make llm-pull", expect="success")
        self.run("2.8 check", "make doctor", expect="All good. Next: make start")

        self.run("3.1 start (Enter = local)", "make start", answers=[""], expect="Kanakku is running")
        lan = self.lan_ip()
        token = self.token()
        self.run("3.1 start again", "make start", answers=[""], expect="already running")
        self.run("4 phone (USB)", "make phone", env={"DEVICE": SERIAL}, expect="Installed on the phone", timeout=2400)
        self.run("3.2 phone connects + demo question", f"python3 scripts/phone_smoke.py --serial {SERIAL} --url http://{lan}:8013 "
                 f"--token {token} --shots run/rehearsal_shots --expect Stop", expect="answer on the phone: Stop",
                 timeout=600)  # fmt: skip
        self.run("7 Wi-Fi address changed", f"python3 scripts/phone_smoke.py --serial {SERIAL} --url http://10.0.2.2:8013 --token {token}"
                 " --keep-data --connect-only", expect="Connected", timeout=300)  # fmt: skip
        self.run("3.3 stop", "make stop", expect="stopped server")
        self.run("3.3 stop again", "make stop", expect="not running|nothing")

        self.run("7 laptop restarted (setup)", "make start", answers=[""], expect="Kanakku is running")
        self.run("7 laptop restarted (power cut)", "kill -9 $(cat run/server.pid); sleep 1; test -f run/server.pid && echo 'stale pid file left behind'",
                 expect="stale pid file")  # fmt: skip
        self.run("7 laptop restarted", "make start", answers=[""], expect="Kanakku is running")
        self.run("3.2 phone after restart", f"python3 scripts/phone_smoke.py --serial {SERIAL} --url http://{lan}:8013 --token {token}"
                 " --keep-data --connect-only", expect="Connected", timeout=300)  # fmt: skip
        self.run("6 demo", "make demo", expect="Try these four questions")
        self.run("3.3 stop", "make stop", expect="stopped server")

        port = self.free_port()
        fake = subprocess.Popen([str(self.dir / ".venv/bin/python"), "-m", "tests.fakes.meta_server", "--port", str(port)],
                                cwd=self.dir / "server", env={**os.environ, "FAKE_META_KEY": "good-key-123456"})  # fmt: skip
        time.sleep(3)
        meta_env = {"META_BASE_URL": f"http://127.0.0.1:{port}/v1"}
        try:
            self.run("5 Meta key typed (fake Meta server)", "make start", answers=["good-key-123456", "y"],
                     env=meta_env, expect=r"key accepted[\s\S]*AI: meta")  # fmt: skip
            self.run("5 Meta key never shown", "grep -c good-key-123456 run/*.log run/*.out || true", expect=r"(:0\s*)+$")
            self.run("5 stop", "make stop", expect="stopped server")
            self.run("5 Meta key rejected", "make forget-key && make start", answers=["wrong-key-999", ""], env=meta_env,
                     expect=r"key rejected[\s\S]*Use local models instead[\s\S]*AI: local")  # fmt: skip
            self.run("5 stop", "make stop", expect="stopped server")
        finally:
            fake.terminate()
        self.run("5 local, no key", "make forget-key; make start", answers=[""], expect="AI: local")
        self.run("3.3 stop", "make stop", expect="stopped server")

    # ------------------------------------------------------------------ helpers
    def token(self) -> str:
        env_local = (self.dir / ".env.local").read_text()
        return re.search(r"^KANAKKU_TOKEN=(.+)$", env_local, re.M).group(1).strip()  # type: ignore[union-attr]

    @staticmethod
    def lan_ip() -> str:
        out = subprocess.run(["ip", "-4", "route", "get", "1.1.1.1"], capture_output=True, text=True).stdout
        return re.search(r"src (\S+)", out).group(1)  # type: ignore[union-attr]

    @staticmethod
    def free_port() -> int:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def report(self) -> Path:
        total = sum(r[3] for r in self.rows)
        md = [f"# Rehearsal {self.n}: fresh clone, following docs/OWNER_GUIDE.md", "",
              f"Folder: `{self.dir}` (a new `git clone` of the repository; nothing copied). "
              f"Date: {time.strftime('%Y-%m-%d %H:%M')}. Total time: {total / 60:.1f} min. "
              f"Result: **{'all steps passed' if not self.failed else 'FAILED'}**.", "",
              "Device: Android emulator (Android 14) standing in for the phone; it reaches the laptop over the "
              "laptop's Wi-Fi address like a phone would.", "",
              "| guide section | command | result | time |", "|---|---|---|---|"]  # fmt: skip
        md += [f"| {s} | `{c}` | {r} | {t:.0f} s |" for s, c, r, t, _ in self.rows]
        md += ["", "## Outputs", ""]
        for s, c, r, t, out in self.rows:
            if not out:
                continue
            lines = [x for x in out.splitlines() if x.strip()]
            shown = lines if len(lines) <= 40 else lines[:12] + ["…"] + lines[-25:]
            md += [f"### {s}: `{c}` — {r} ({t:.0f} s)", "", "```", *shown, "```", ""]
        path = ROOT / "docs" / f"rehearsal_{self.n}.md"
        token = self.token() if (self.dir / ".env.local").exists() else ""
        text = "\n".join(md) + "\n"
        if token:
            text = text.replace(token, "<token>")  # the LAN code is printed on purpose, but not committed
        path.write_text(text)
        return path


if __name__ == "__main__":
    r = Rehearsal(int(sys.argv[1]))
    try:
        r.go()
    finally:
        print(f"report: {r.report()}")
    sys.exit(1 if r.failed else 0)
