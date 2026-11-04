"""`make up` end to end (scripts/up.sh as a subprocess) against a fake Meta endpoint (tests/fakes/meta_server.py):
PROVIDER flag, saved key, typed key (pseudo-terminal), Enter for local, invalid key, daily cap, 429 once.
Each test uses its own run/ folder, .env.local, database and ports; the key must never appear in any log."""

from __future__ import annotations

import json
import os
import pty
import select
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UP, DOWN = ROOT / "scripts" / "up.sh", ROOT / "scripts" / "down.sh"
GOOD, BAD = "good-key-123456", "wrong-key-999999"
LOAN_Q = "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_http(url: str, timeout: float = 20) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except urllib.error.HTTPError:
            return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(url)


def start_fake(extra: dict[str, str] | None = None) -> tuple[subprocess.Popen, int]:
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "tests.fakes.meta_server", "--port", str(port)],
        cwd=ROOT / "server",
        env={**os.environ, "FAKE_META_KEY": GOOD, **(extra or {})},
    )
    wait_http(f"http://127.0.0.1:{port}/_stats")
    return proc, port


@pytest.fixture(scope="module")
def fake():
    proc, port = start_fake()
    yield port
    proc.terminate()
    proc.wait(5)


class Env:
    def __init__(self, tmp: Path, fake_port: int) -> None:
        self.run = tmp / "run"
        self.env_local = tmp / "env.local"
        self.port = free_port()
        base = f"http://127.0.0.1:{fake_port}/v1"
        keep = {k: v for k, v in os.environ.items() if k not in ("META_API_KEY", "PROVIDER", "CI", "LLM_PROVIDER")}
        self.vars = keep | {
            "KANAKKU_RUN_DIR": str(self.run),
            "KANAKKU_ENV_LOCAL": str(self.env_local),
            "PORT": str(self.port),
            "HOST": "127.0.0.1",
            "META_BASE_URL": base,
            "LLM_BASE_URL": base,
            "LLM_MODEL": "qwen2.5:7b-instruct",
            "DB_PATH": str(tmp / "k.db"),
            "KANAKKU_TOKEN": "",
            "ASKS_PER_MINUTE": "1000",
        }
        self.outputs: list[str] = []

    def up(self, provider: str = "", **extra: str) -> subprocess.CompletedProcess:
        r = subprocess.run(
            ["bash", str(UP)], env=self.vars | {"PROVIDER": provider} | extra, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=120,
        )  # fmt: skip
        self.outputs.append(r.stdout + r.stderr)
        return r

    def up_tty(self, answers: list[str], **extra: str) -> tuple[int, str]:
        """Runs make up in a pseudo-terminal, typing each answer when the script waits for input."""
        pid, fd = pty.fork()
        if pid == 0:
            os.execve("/bin/bash", ["bash", str(UP)], self.vars | {"PROVIDER": ""} | extra)
        out, pending = b"", list(answers)
        end = time.time() + 120
        while time.time() < end:
            ready, _, _ = select.select([fd], [], [], 0.5)
            if ready:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
                if pending and (out.rstrip().endswith(b":") or out.rstrip().endswith(b"]")):
                    os.write(fd, (pending.pop(0) + "\n").encode())
        _, status = os.waitpid(pid, 0)
        text = out.decode(errors="replace")
        self.outputs.append(text)
        return os.waitstatus_to_exitcode(status), text

    def down(self) -> None:
        subprocess.run(["bash", str(DOWN), "--server-only"], env=self.vars, capture_output=True, timeout=60)

    def get(self, path: str, token: bool = True) -> dict:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        if token:
            req.add_header("Authorization", f"Bearer {self.token()}")
        return json.load(urllib.request.urlopen(req, timeout=30))

    def ask(self, text: str) -> tuple[int, dict]:
        data = f"family_id=1&text={urllib.parse.quote(text)}".encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/cases", data=data, method="POST")
        req.add_header("Authorization", f"Bearer {self.token()}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            r = urllib.request.urlopen(req, timeout=120)
            return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def token(self) -> str:
        line = next(x for x in self.env_local.read_text().splitlines() if x.startswith("KANAKKU_TOKEN="))
        return line.split("=", 1)[1]

    def assert_no_key(self, *keys: str) -> None:
        texts = self.outputs + [p.read_text(errors="replace") for p in self.run.glob("*.log*")]
        texts += [p.read_text(errors="replace") for p in self.run.glob("*.out")]
        for key in keys:
            for t in texts:
                assert key not in t, "the Meta key leaked into a log or the terminal"


@pytest.fixture
def env(tmp_path, fake):
    import urllib.parse  # noqa: F401  (used in Env.ask)

    from app.db.repo import Repo
    from app.db.seed_demo import seed

    seed(Repo(tmp_path / "k.db"))
    e = Env(tmp_path, fake)
    yield e
    e.down()


def test_flag_local(env):
    r = env.up("local")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Provider: local" in r.stdout and "Token  :" in r.stdout
    assert oct(env.env_local.stat().st_mode & 0o777) == "0o600"
    assert env.get("/health", token=False)["provider"]["name"] == "local"


def test_flag_meta_with_saved_key(env):
    env.env_local.write_text(f"META_API_KEY={GOOD}\n")
    r = env.up("meta")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "key accepted" in r.stdout and "Provider: meta" in r.stdout
    h = env.get("/health", token=False)["provider"]
    assert h["name"] == "meta" and h["model"] == "muse-spark-1.3" and h["cache"] is True
    env.assert_no_key(GOOD)


def test_saved_key_is_used_without_asking(env):
    env.env_local.write_text(f"META_API_KEY={GOOD}\n")
    r = env.up()
    assert r.returncode == 0 and "Provider: meta" in r.stdout and "Meta Model API key" not in r.stdout
    env.assert_no_key(GOOD)


def test_typed_key_hidden_and_saved(env):
    code, out = env.up_tty([GOOD, "y"])
    assert code == 0, out
    assert "Meta Model API key" in out and "key accepted" in out and "Provider: meta" in out
    assert GOOD not in out, "the typed key was echoed"
    assert f"META_API_KEY={GOOD}" in env.env_local.read_text()
    env.assert_no_key(GOOD)


def test_enter_means_local(env):
    code, out = env.up_tty([""])
    assert code == 0, out
    assert "Provider: local" in out


def test_invalid_key_offers_local(env):
    code, out = env.up_tty([BAD, ""])
    assert code == 0, out
    assert "key rejected" in out and "Use local models instead? [Y/n]" in out and "Provider: local" in out
    assert "META_API_KEY" not in env.env_local.read_text()
    env.assert_no_key(BAD)


def test_invalid_saved_key_non_interactive(env):
    env.env_local.write_text(f"META_API_KEY={BAD}\n")
    r = env.up()
    assert r.returncode == 0 and "key rejected" in r.stdout and "using the local models instead" in r.stdout
    env.down()
    r = env.up("meta")
    assert r.returncode == 1 and "PROVIDER=meta but the key check failed: key rejected" in r.stderr
    env.assert_no_key(BAD)


def test_frozen_ollama_fails_fast_with_the_fix(env):
    """Port held but no answer (Ollama paused with Ctrl+Z): say so at once, do not hang."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        t0 = time.time()
        r = env.up("local", LLM_BASE_URL=f"http://127.0.0.1:{s.getsockname()[1]}/v1")
    assert r.returncode == 1 and time.time() - t0 < 20
    assert "frozen" in r.stderr and "killall -9 ollama" in r.stderr


def test_daily_cap_gives_a_clear_error(env):
    env.env_local.write_text(f"META_API_KEY={GOOD}\n")
    assert env.up("meta", META_MAX_CALLS_PER_DAY="3").returncode == 0
    status, first = env.ask(LOAN_Q)
    assert status == 200 and first["provider"] == "meta"
    status, second = env.ask(LOAN_Q + " Please check again.")
    assert status == 429 and second["error"]["code"] == "daily_limit"
    assert "make up PROVIDER=local" in second["error"]["message"]
    env.assert_no_key(GOOD)


def test_daily_cap_with_local_fallback_is_labelled(env):
    env.env_local.write_text(f"META_API_KEY={GOOD}\n")
    assert env.up("meta", META_MAX_CALLS_PER_DAY="3", LLM_FALLBACK="local").returncode == 0
    env.ask(LOAN_Q)
    status, second = env.ask(LOAN_Q + " Please check again.")
    assert status == 200 and second["provider"] == "local fallback" and second["local_fallback"] is True
    trace = env.get(f"/v1/cases/{second['case_id']}")["trace"]
    assert any(t["step"] == "llm_provider" and t["detail"]["local_fallback"] for t in trace)
    env.assert_no_key(GOOD)


def test_429_once_is_retried(tmp_path):
    proc, port = start_fake({"FAKE_429_ONCE": "1"})
    try:
        from app.db.repo import Repo
        from app.db.seed_demo import seed

        seed(Repo(tmp_path / "k.db"))
        e = Env(tmp_path, port)
        e.env_local.write_text(f"META_API_KEY={GOOD}\n")
        assert e.up("meta").returncode == 0
        status, res = e.ask(LOAN_Q)
        stats = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/_stats"))
        assert status == 200 and stats.get("429") == 1
        assert res["verdict"]["colour"] in ("red", "yellow") and not res["degraded"]
        e.assert_no_key(GOOD)
        e.down()
    finally:
        proc.terminate()
        proc.wait(5)
