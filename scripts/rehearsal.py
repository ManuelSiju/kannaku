#!/usr/bin/env python3
"""Fresh-clone rehearsal of docs/OWNER_GUIDE.md: clones the repository into a NEW folder and uses it as a person would.
make start runs in the foreground in a pseudo-terminal; Ctrl+C is a real Ctrl+C, closing the terminal is a real hang-up.
After every stop it looks for leftovers (processes running from the clone, adb tunnels). Writes docs/rehearsal_<n>.md.

usage: scripts/rehearsal.py <n>     env: DEVICE (default emulator-5554; never a real phone, the smoke test wipes app data)

What it does not do for real: `sudo` is a stub that refuses (no password here), so the "declined" path is tested;
the installers for Ollama / Flutter are not re-run. LLM_BASE_URL / OLLAMA_HOST pass through to use a private Ollama.
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
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\r")
SERIAL = os.environ.get("DEVICE", "emulator-5554")


class Terminal:
    """One terminal window running one command."""

    def __init__(self, cmd: str, cwd: Path, env: dict[str, str]) -> None:
        self.cmd, self.t0, self.buf, self.code = cmd, time.time(), b"", None
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(cwd)
            os.execve("/bin/bash", ["bash", "-c", cmd], env)
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self) -> None:
        while True:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.3)
                if r:
                    chunk = os.read(self.fd, 65536)
                    if not chunk:
                        return
                    self.buf += chunk
            except (OSError, ValueError):
                return

    @property
    def text(self) -> str:
        return ANSI.sub("", self.buf.decode(errors="replace"))

    def wait_text(self, pattern: str, timeout: float = 600, answers: tuple[tuple[str, str], ...] = ()) -> bool:
        pending, end = list(answers), time.time() + timeout
        while time.time() < end:
            if re.search(pattern, self.text):
                return True
            for prompt, reply in pending:
                if re.search(prompt, self.text):
                    time.sleep(0.3)
                    os.write(self.fd, (reply + "\n").encode())
                    pending.remove((prompt, reply))
                    break
            if self.exited():
                return re.search(pattern, self.text) is not None
            time.sleep(0.2)
        return False

    def exited(self) -> bool:
        if self.code is None:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                self.code = os.waitstatus_to_exitcode(status)
        return self.code is not None

    def ctrl_c(self) -> None:
        os.write(self.fd, b"\x03")

    def wait_exit(self, timeout: float = 40) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.exited():
                self.thread.join(1)
                return True
            time.sleep(0.2)
        return False

    def close_window(self) -> None:
        os.close(self.fd)


class Rehearsal:
    def __init__(self, n: int) -> None:
        self.n = n
        self.dir = Path.home() / f"kanakku-rehearsal-{n}"
        self.rows: list[tuple[str, str, bool, float, str]] = []
        self.stub = Path(f"/tmp/kanakku-rehearsal-stub-{n}")
        self.env = {**os.environ, "DEVICE": SERIAL, "PATH": f"{self.stub}:{os.environ['PATH']}"}
        self.env.pop("PROVIDER", None)

    @property
    def failed(self) -> bool:
        return any(not ok for _, _, ok, _, _ in self.rows)

    def record(self, section: str, what: str, ok: bool, secs: float = 0.0, out: str = "") -> None:
        self.rows.append((section, what, ok, secs, out))
        print(f"{'✔' if ok else '✘'} [{secs:6.1f}s] {section}: {what}", flush=True)
        if not ok:
            print(out[-1500:], flush=True)

    def run(self, section: str, cmd: str, expect: str = "", *, timeout: float = 2400, cwd: Path | None = None,
            env: dict[str, str] | None = None, answers: tuple[tuple[str, str], ...] = ()) -> str:  # fmt: skip
        t = Terminal(cmd, cwd or self.dir, {**self.env, **(env or {})})
        t.wait_text(r"\Z.", timeout=0.1)
        end = time.time() + timeout
        pending = list(answers)
        while time.time() < end and not t.exited():
            for prompt, reply in pending:
                if re.search(prompt, t.text):
                    os.write(t.fd, (reply + "\n").encode())
                    pending.remove((prompt, reply))
                    break
            time.sleep(0.2)
        t.wait_exit(5)
        ok = t.code == 0 and (not expect or re.search(expect, t.text) is not None)
        self.record(section, f"`{cmd}`", ok, time.time() - t.t0, t.text)
        return t.text

    def start(self, section: str, *, env: dict[str, str] | None = None, cmd: str = "make start",
              answers: tuple[tuple[str, str], ...] = (("Meta Model API key", ""),), expect: str = "Kanakku is running",
              reject: str = "") -> Terminal:  # fmt: skip
        t = Terminal(cmd, self.dir, {**self.env, **(env or {})})
        ok = t.wait_text(expect + r"[\s\S]*Live log", 1500, answers)
        ok = ok and not (reject and re.search(reject, t.text))
        self.record(section, f"`{cmd}` (foreground, until the box and live log)", ok, time.time() - t.t0, t.text)
        return t

    def ctrl_c(self, section: str, t: Terminal) -> None:
        t0 = time.time()
        t.ctrl_c()
        done = t.wait_exit()
        self.record(section, "Ctrl+C", done and "Kanakku stopped" in t.text and "Traceback" not in t.text,
                    time.time() - t0, t.text[-400:])  # fmt: skip
        self.no_leftovers(section)

    def leftovers(self) -> list[str]:
        out = []
        for p in Path("/proc").iterdir():
            if not p.name.isdigit() or int(p.name) == os.getpid():
                continue
            try:
                cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
                cwd = os.readlink(p / "cwd")
            except OSError:
                continue
            if cmd and (str(self.dir) in cmd or cwd.startswith(str(self.dir))) and "gradle" not in cmd.lower():
                out.append(f"{p.name} {cmd[:100]}")
        return out

    def no_leftovers(self, section: str) -> None:
        time.sleep(1)
        left = self.leftovers()
        tunnels = subprocess.run(["adb", "-s", SERIAL, "reverse", "--list"], capture_output=True, text=True).stdout.strip()
        pidfiles = sorted(p.name for p in (self.dir / "run").glob("*.pid"))
        evidence = (f"$ processes running from the clone: {left or 'none'}\n$ adb reverse --list: {tunnels or 'none'}\n"
                    f"$ pid files in run/: {pidfiles or 'none'}")  # fmt: skip
        self.record(section, "no leftovers (`ps` evidence)", not left and not tunnels and not pidfiles, 0, evidence)

    def go(self) -> None:
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.stub.mkdir(exist_ok=True)
        (self.stub / "sudo").write_text('#!/bin/sh\necho "[stub sudo: refused] $*"\nexit 1\n')
        (self.stub / "sudo").chmod(0o755)
        lan = self.lan_ip()
        smoke = f"python3 scripts/phone_smoke.py --serial {SERIAL} --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2)"

        self.run("2.3 download", f"git clone {ROOT} {self.dir}", "Cloning into", cwd=Path.home())
        t = self.start("2.4 first make start: full setup")
        self.record("2.4 setup ran", "server parts installed, system-package message shown",
                    "Server parts ready" in t.text and "may be asked for your password once" in t.text)  # fmt: skip
        self.run("2.4 check", "make doctor", "Kanakku server")
        self.run("4 app on the phone", "make phone", "Installed on the phone")
        self.run("3.2 phone over Wi-Fi + demo question", f"{smoke} --url http://{lan}:8013 --shots run/shots --expect Stop",
                 "answer on the phone: Stop", timeout=420)  # fmt: skip
        self.record("3.1 live log", "request lines stream in the terminal",
                    re.search(r"\d\d:\d\d:\d\d INFO\s+\S+\s+POST /v1/cases -> 202", t.text) is not None)  # fmt: skip
        self.ctrl_c("3.3 stop", t)

        t0 = time.time()
        self.run("second start: setup check", "scripts/setup.sh")
        fast = time.time() - t0
        self.record("second start: setup check", f"under 2 s ({fast:.2f} s)", fast < 2, fast)
        t = self.start("second start", reject=r"Setting up Kanakku|may be asked for your password")
        self.run("phone via USB", f"{smoke} --url http://127.0.0.1:8013 --keep-data --expect Stop",
                 "answer on the phone: Stop", timeout=420)  # fmt: skip
        self.run("7 Wi-Fi address changed", f"{smoke} --url http://{lan}:8013 --keep-data --connect-only", "Connected", timeout=200)
        self.run("start twice", "make start", "already running in another terminal")
        self.run("6 demo while running", "make demo", "Try these four questions")
        time.sleep(3)
        self.record("6 demo while running", "the foreground make start survives", not t.exited())
        self.ctrl_c("3.3 stop", t)

        self.run("make stop twice (1)", "make stop", "not running")
        self.run("make stop twice (2)", "make stop", "not running")
        t = self.start("make stop from another terminal")
        self.run("make stop from another terminal", "make stop", "Kanakku stopped")
        t.wait_exit()
        self.no_leftovers("make stop from another terminal")

        t = self.start("terminal closed")
        t.close_window()
        time.sleep(12)
        self.no_leftovers("terminal closed (SIGHUP)")

        t = self.start("7 laptop restarted (setup)")
        self.run("7 laptop restarted (power cut)", "kill -9 $(cat run/start.pid) $(cat run/server.pid); sleep 1; ls run/*.pid", "server.pid")
        t.wait_exit(5)
        t = self.start("7 laptop restarted")
        self.run("3.2 phone after restart", f"{smoke} --url http://{lan}:8013 --keep-data --connect-only", "Connected", timeout=200)
        self.ctrl_c("3.3 stop", t)

        self.run("BG=1", "make start BG=1 PROVIDER=local", "Kanakku is running")
        self.run("BG=1 stop", "make stop", "stopped server")
        self.no_leftovers("BG=1")

        port = self.free_port()
        fake = subprocess.Popen([str(self.dir / ".venv/bin/python"), "-m", "tests.fakes.meta_server", "--port", str(port)],
                                cwd=self.dir / "server", env={**os.environ, "FAKE_META_KEY": "good-key-123456"})  # fmt: skip
        time.sleep(3)
        meta = {"META_BASE_URL": f"http://127.0.0.1:{port}/v1"}
        try:
            t = self.start("5 Meta key typed (fake Meta server)", env=meta, expect=r"key accepted[\s\S]*AI: meta",
                           answers=(("Meta Model API key", "good-key-123456"), (r"Save this key", "y")))  # fmt: skip
            self.record("5 Meta key hidden", "not shown on screen", "good-key-123456" not in t.text)
            self.ctrl_c("5 stop", t)
            self.run("5 key never logged", "! grep -rl good-key-123456 run/ ; true")
            leak = subprocess.run(["grep", "-rl", "good-key-123456", str(self.dir / "run")], capture_output=True, text=True)
            self.record("5 key never logged", "no file in run/ contains it", not leak.stdout.strip(), 0, leak.stdout)
            t = self.start("5 saved key: no question", env=meta, answers=(), expect=r"AI: meta", reject="Meta Model API key")
            self.ctrl_c("5 stop", t)
            self.run("5 forget key", "make forget-key", "removed")
            t = self.start("5 Meta key rejected", env=meta, expect=r"key rejected[\s\S]*AI: local",
                           answers=(("Meta Model API key", "wrong-key-999"), (r"Use local models instead", "")))  # fmt: skip
            self.ctrl_c("5 stop", t)
        finally:
            fake.terminate()
        t = self.start("local, no key", expect="AI: local")
        self.ctrl_c("3.3 stop", t)

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
              f"Folder: `{self.dir}` (a new `git clone`; nothing copied). {time.strftime('%Y-%m-%d %H:%M')}. "
              f"Total {total / 60:.1f} min. Result: **{'all steps passed' if not self.failed else 'FAILED'}**.", "",
              f"Device: Android emulator `{SERIAL}` standing in for the phone. `sudo` was a stub that refuses (no password "
              "available), so the declined path ran, not a real install. Ollama and Flutter were already installed.", "",
              "| guide section | step | result | time |", "|---|---|---|---|"]  # fmt: skip
        md += [f"| {s} | {w} | {'✔ pass' if ok else '✘ FAIL'} | {t:.1f} s |" for s, w, ok, t, _ in self.rows]
        md += ["", "## Outputs", ""]
        for s, w, ok, t, out in self.rows:
            lines = [x for x in out.splitlines() if x.strip()]
            if not lines:
                continue
            shown = lines if len(lines) <= 40 else lines[:12] + ["…"] + lines[-25:]
            md += [f"### {s}: {w} — {'pass' if ok else 'FAIL'} ({t:.1f} s)", "", "```", *shown, "```", ""]
        text = "\n".join(md) + "\n"
        env_local = self.dir / ".env.local"
        if env_local.exists() and (m := re.search(r"^KANAKKU_TOKEN=(.+)$", env_local.read_text(), re.M)):
            text = text.replace(m.group(1).strip(), "<token>")
        path = ROOT / "docs" / f"rehearsal_{self.n}.md"
        path.write_text(text)
        return path


if __name__ == "__main__":
    r = Rehearsal(int(sys.argv[1]))
    try:
        r.go()
    finally:
        print(f"report: {r.report()}")
    sys.exit(1 if r.failed else 0)
