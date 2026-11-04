"""Reliability basics: error format, request ids, access token, upload limits, rate limit, idempotency, /v1, /ready,
migrations, backups, the Meta spend guard (cache, daily cap, visible local fallback), retries, and that the Meta key
never shows up in logs, traces, errors or /health."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from app.api import deps
from app.config import Settings
from app.core.logs import RedactFilter, setup_logging
from app.db.backup import backup_daily
from app.db.migrate import migrate, migrations
from app.main import app, create_app
from app.pipeline.events import EventBus
from app.pipeline.schemas import ExplainerOutput
from app.providers.guard import GuardedLLM, SpendCapReached, SpendGuard
from app.providers.llm import AskBudget, LLMStepFailed, OpenAICompatibleLLM, use_budget
from scripts.meta_key import OFFLINE, OK, REJECTED, check_key
from tests.fakes import FakeLLM, load_fixture

SECRET = "sk-meta-SECRET-7f3a9c2e1d"
LOAN_Q = "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
def client(demo_repo):
    state = {"llm": FakeLLM(load_fixture("flat_loan"))}
    app.dependency_overrides[deps.get_repo] = lambda: demo_repo
    app.dependency_overrides[deps.get_llm_provider] = lambda: state["llm"]
    app.dependency_overrides[deps.get_bus] = lambda: EventBus()
    with TestClient(app, raise_server_exceptions=False) as c:
        c.kstate = state  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


def assert_error(r, status, code):
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"error"} and body["error"]["code"] == code
    assert body["error"]["request_id"] == r.headers["x-request-id"]
    assert "Traceback" not in r.text
    return body["error"]


# ---------------------------------------------------------------- error format, request id, versioning


def test_errors_use_one_format(client):
    assert_error(client.get("/cases/999999"), 404, "not_found")
    assert_error(client.post("/cases", data={"family_id": "1"}), 422, "invalid_request")
    assert_error(client.post("/cases", data={"family_id": "abc", "text": "x"}), 422, "invalid_request")


def test_crash_gives_500_without_stack_trace(client):
    def boom():
        raise RuntimeError("secret internals")

    app.dependency_overrides[deps.get_bus] = boom
    err = assert_error(client.post("/cases", data={"family_id": "1", "text": LOAN_Q}), 500, "internal_error")
    assert "secret internals" not in err["message"]


def test_request_id_is_echoed_and_recorded_in_the_trace(client):
    r = client.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}, headers={"X-Request-ID": "abc123"})
    assert r.status_code == 200 and r.headers["x-request-id"] == "abc123"
    assert r.json()["request_id"] == "abc123"
    bundle = client.get(f"/v1/cases/{r.json()['case_id']}").json()
    assert bundle["trace"][0]["step"] == "request" and bundle["trace"][0]["detail"]["request_id"] == "abc123"
    assert client.get("/health").headers["x-request-id"]


def test_v1_and_old_paths_both_work(client):
    assert client.get("/v1/health").json()["version"] == client.get("/health").json()["version"]
    assert client.get("/v1/families/1/profile").status_code == 200
    assert client.get("/families/1/profile").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/v1/cases" in paths and "/cases" not in paths


def test_ready_checks_db_and_llm(client, monkeypatch):
    from app.api import health

    async def up():
        return {"reachable": True}

    async def down():
        return {"reachable": False, "error": "ConnectError: start it with make llm-up"}

    monkeypatch.setattr(health, "llm_status", up)
    r = client.get("/ready")
    assert r.status_code == 200 and r.json()["checks"]["db"]["ok"] is True, r.text
    monkeypatch.setattr(health, "llm_status", down)
    r = client.get("/ready")
    assert r.status_code == 503 and r.json()["ready"] is False


def test_health_shows_provider_without_secrets(client):
    h = client.get("/health").json()
    assert h["provider"]["name"] == "local" and h["provider"]["cache"] is False and h["provider"]["spend_guard"] is None


# ---------------------------------------------------------------- access token


def test_token_required_except_health(demo_repo):
    secured = create_app(Settings(_env_file=None, kanakku_token="lan-token-123"))
    secured.dependency_overrides[deps.get_repo] = lambda: demo_repo
    secured.dependency_overrides[deps.get_llm_provider] = lambda: FakeLLM(load_fixture("flat_loan"))
    with TestClient(secured) as c:
        assert c.get("/health").status_code == 200
        assert c.get("/v1/health").status_code == 200
        assert_error(c.get("/v1/families/1/profile"), 401, "unauthorized")
        assert_error(c.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}), 401, "unauthorized")
        bad = {"Authorization": "Bearer wrong"}
        assert_error(c.get("/v1/families/1/profile", headers=bad), 401, "unauthorized")
        ok = {"Authorization": "Bearer lan-token-123"}
        assert c.get("/v1/families/1/profile", headers=ok).status_code == 200


# ---------------------------------------------------------------- upload limits


def test_oversized_image_gets_413(client):
    big = PNG + b"0" * (8 * 1024 * 1024)
    r = client.post("/v1/cases", data={"family_id": "1"}, files=[("files", ("p.png", big, "image/png"))])
    assert "8 MB" in assert_error(r, 413, "file_too_large")["message"]


def test_oversized_audio_gets_413(client):
    big = b"ID3" + b"0" * (10 * 1024 * 1024 + 10)
    r = client.post("/v1/cases", data={"family_id": "1"}, files=[("audio", ("a.mp3", big, "audio/mpeg"))])
    assert_error(r, 413, "file_too_large")


def test_type_is_checked_by_content_not_name(client):
    r = client.post(
        "/v1/cases", data={"family_id": "1"}, files=[("files", ("photo.png", b"MZ\x90\x00 not an image", "image/png"))]
    )
    assert_error(r, 415, "unsupported_type")
    r = client.post("/v1/cases", data={"family_id": "1"}, files=[("audio", ("a.mp3", PNG, "audio/mpeg"))])
    assert_error(r, 415, "unsupported_type")


def test_too_many_files(client):
    files = [("files", (f"p{i}.png", PNG, "image/png")) for i in range(6)]
    assert_error(client.post("/v1/cases", data={"family_id": "1"}, files=files), 413, "too_many_files")


def test_whole_request_too_large(client):
    r = client.post("/v1/cases", content=b"x", headers={"Content-Length": str(500 * 1024 * 1024)})
    assert_error(r, 413, "request_too_large")


def test_sniff():
    from app.api.uploads import sniff

    assert sniff(b"%PDF-1.7 ...")[0] == "pdf"
    assert sniff(b"\xff\xd8\xff\xe0....")[1] == "image/jpeg"
    assert sniff(b"RIFF\x00\x00\x00\x00WAVEfmt ")[0] == "audio"
    assert sniff(b"\x00\x00\x00\x18ftypM4A ")[0] == "audio"
    assert sniff(b"<html>") is None


# ---------------------------------------------------------------- rate limit, idempotency


def test_rate_limit_per_device():
    from app.api.middleware import RateLimiter

    rl = RateLimiter(20)
    assert all(rl.allow("phone-a", now=0.0) for _ in range(20))
    assert not rl.allow("phone-a", now=1.0)
    assert rl.allow("phone-b", now=1.0)
    assert rl.allow("phone-a", now=61.0)


def test_rate_limit_answers_429(demo_repo):
    limited = create_app(Settings(_env_file=None, asks_per_minute=1))
    limited.dependency_overrides[deps.get_repo] = lambda: demo_repo
    limited.dependency_overrides[deps.get_llm_provider] = lambda: FakeLLM(load_fixture("flat_loan"))
    with TestClient(limited) as c:
        h = {"X-Device-ID": "phone-1"}
        assert c.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}, headers=h).status_code == 200
        r = c.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}, headers=h)
        assert_error(r, 429, "too_many_requests")
        assert r.headers["retry-after"] == "30"


def test_idempotency_key_returns_the_first_case(client, demo_repo):
    h = {"Idempotency-Key": "ask-42"}
    first = client.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}, headers=h)
    again = client.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}, headers=h)
    assert first.status_code == again.status_code == 200
    assert again.json()["case_id"] == first.json()["case_id"]
    assert again.headers["idempotent-replay"] == "true"
    assert client.kstate["llm"].calls.count("CaseDraft") == 1
    other = client.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}, headers={"Idempotency-Key": "ask-43"})
    assert other.json()["case_id"] != first.json()["case_id"]


# ---------------------------------------------------------------- database


def test_migrations_are_numbered_and_recorded(tmp_path):
    nums = [n for n, _ in migrations()]
    assert nums == list(range(1, len(nums) + 1)) and len(nums) >= 3
    conn = sqlite3.connect(tmp_path / "m.db")
    assert migrate(conn) == nums
    assert migrate(conn) == []
    assert [r[0] for r in conn.execute("SELECT version FROM schema_version")] == nums


def test_database_from_before_migrations_upgrades(tmp_path):
    conn = sqlite3.connect(tmp_path / "old.db")
    conn.executescript(migrations()[0][1].read_text())  # old databases were made from the original schema
    conn.execute("INSERT INTO family (id, language) VALUES (1, 'en')")
    conn.commit()
    assert migrate(conn)[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM family").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0] == 0


def test_wal_mode(repo):
    assert repo.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_daily_backup_keeps_three(tmp_path, repo):
    out = tmp_path / "backups"
    for d in range(1, 6):
        backup_daily(repo.path, out, keep=3, today=dt.date(2026, 10, d))
    assert backup_daily(repo.path, out, keep=3, today=dt.date(2026, 10, 5)) is None  # once a day
    names = sorted(p.name for p in out.iterdir())
    assert names == ["test-2026-10-03.db", "test-2026-10-04.db", "test-2026-10-05.db"]
    assert sqlite3.connect(out / names[-1]).execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] >= 3


# ---------------------------------------------------------------- Meta settings and spend guard


def meta_settings(tmp_path, **kw) -> Settings:
    return Settings(
        _env_file=None,
        llm_provider="meta",
        meta_api_key=SECRET,
        meta_base_url="http://meta.test/v1",
        llm_base_url="http://localhost:11434/v1",
        llm_model="qwen2.5:7b-instruct",
        db_path=tmp_path / "k.db",
        **kw,
    )


def test_meta_settings(tmp_path):
    s = meta_settings(tmp_path)
    assert (s.llm_base_url, s.llm_model, s.llm_vision_enabled) == ("http://meta.test/v1", "muse-spark-1.3", True)
    assert s.local_settings().llm_model == "qwen2.5:7b-instruct"
    assert SECRET not in repr(s) and SECRET not in json.dumps(s.model_dump(mode="json"))
    with pytest.raises(ValueError, match="META_API_KEY"):
        Settings(_env_file=None, llm_provider="meta")


def test_bad_config_message_has_no_secret(monkeypatch, capsys):
    from app import main

    monkeypatch.setenv("META_API_KEY", SECRET)
    monkeypatch.setenv("LLM_PROVIDER", "meta")
    monkeypatch.setenv("META_MAX_CALLS_PER_DAY", "0")
    main.get_settings.cache_clear()
    try:
        with pytest.raises(SystemExit):
            main.load_settings()
    finally:
        main.get_settings.cache_clear()
    err = capsys.readouterr().err
    assert "Bad configuration" in err and SECRET not in err


def _openai(handler) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url="http://meta.test/v1",
        api_key=SECRET,
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def chat_reply(obj) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "muse-spark-1.3",
            "choices": [
                {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(obj)}}
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )


VERDICT = {"agent_lines": [], "verdict_sentence": {"speaker": "alfii", "text": "Wait."}, "questions": []}


def test_cache_hit_costs_no_call(tmp_path):
    s = meta_settings(tmp_path)
    sent = []

    def handler(req):
        sent.append(req)
        return chat_reply(VERDICT)

    llm = GuardedLLM(OpenAICompatibleLLM(s, _openai(handler)), s, SpendGuard(s.db_path, 300))

    async def go():
        with use_budget(AskBudget(4)) as b:
            await llm.chat_json("sys", "user", ExplainerOutput)
            await llm.chat_json("sys", "user", ExplainerOutput)
            return b

    b = asyncio.run(go())
    assert len(sent) == 1 and b.used == 1 and b.cache_hits == 1 and llm.guard.calls_today() == 1


def test_daily_cap_fails_fast_or_falls_back_visibly(tmp_path, caplog):
    s = meta_settings(tmp_path, llm_cache=False)
    guard = SpendGuard(s.db_path, 5)
    meta = OpenAICompatibleLLM(s, _openai(lambda req: chat_reply(VERDICT)))
    caplog.set_level(logging.WARNING)

    async def ask(llm):
        with use_budget(AskBudget(4)) as b:
            await llm.chat_json("sys", "{}", ExplainerOutput)
            return b

    llm = GuardedLLM(meta, s, guard)
    for _ in range(4):
        asyncio.run(ask(llm))
    assert "4 of 5" in caplog.text  # 80% warning
    asyncio.run(ask(llm))
    assert guard.status()["exhausted"]
    with pytest.raises(SpendCapReached, match="limit of 5"):
        asyncio.run(ask(llm))

    local = FakeLLM({"ExplainerOutput": VERDICT})
    with_fallback = GuardedLLM(meta, s, guard, fallback=local)
    b = asyncio.run(ask(with_fallback))
    assert b.fallback_used and local.calls == ["ExplainerOutput"]


def test_cap_reached_answers_429_before_the_ask(client, tmp_path):
    s = meta_settings(tmp_path)
    guard = SpendGuard(s.db_path, 1)
    guard.add(1)
    client.kstate["llm"] = GuardedLLM(FakeLLM({}), s, guard)
    err = assert_error(client.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}), 429, "daily_limit")
    assert "make up PROVIDER=local" in err["message"]


def test_local_fallback_is_shown_in_the_result_and_trace(client, tmp_path):
    s = meta_settings(tmp_path)
    guard = SpendGuard(s.db_path, 1)
    guard.add(1)
    client.kstate["llm"] = GuardedLLM(FakeLLM({}), s, guard, fallback=FakeLLM(load_fixture("flat_loan")))
    res = client.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q}).json()
    assert res["provider"] == "local fallback" and res["local_fallback"] is True
    trace = client.get(f"/v1/cases/{res['case_id']}").json()["trace"]
    step = next(t for t in trace if t["step"] == "llm_provider")
    assert step["outcome"] == "degraded" and step["detail"]["local_fallback"] is True


def test_retry_on_5xx_then_success_within_budget(tmp_path):
    s = Settings(_env_file=None, llm_timeout_s=5)
    replies = iter([httpx.Response(503, json={"error": "busy"}), chat_reply(VERDICT)])
    llm = OpenAICompatibleLLM(s, _openai(lambda req: next(replies)))

    async def go():
        with use_budget(AskBudget(4)) as b:
            out, _ = await llm.chat_json("sys", "user", ExplainerOutput)
            return out, b

    out, b = asyncio.run(go())
    assert out.verdict_sentence.text == "Wait." and b.used == 2 and b.retries == 1


def test_no_retry_on_400_or_without_budget(tmp_path):
    s = Settings(_env_file=None, llm_timeout_s=5)
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503, json={"error": "busy"})

    llm = OpenAICompatibleLLM(s, _openai(handler))

    async def go(n):
        with use_budget(AskBudget(n)):
            await llm.chat_json("sys", "user", ExplainerOutput)

    with pytest.raises(LLMStepFailed):
        asyncio.run(go(1))
    assert len(calls) == 1  # the budget had no room for a retry


# ---------------------------------------------------------------- the key never leaks


def test_meta_key_check():
    def t(status):
        return httpx.MockTransport(lambda req: httpx.Response(status, json={"data": []}))

    assert check_key(SECRET, "http://meta.test/v1", transport=t(200)) == (OK, "key accepted")
    assert check_key(SECRET, "http://meta.test/v1", transport=t(401)) == (REJECTED, "key rejected")

    def offline(req):
        raise httpx.ConnectError("Name or service not known")

    code, reason = check_key(SECRET, "http://meta.test/v1", transport=httpx.MockTransport(offline))
    assert code == OFFLINE and reason.startswith("no internet") and SECRET not in reason
    assert check_key("", "http://meta.test/v1")[0] == REJECTED


def test_redact_filter():
    f = RedactFilter([SECRET])
    rec = logging.LogRecord("x", logging.ERROR, __file__, 1, "auth failed for Bearer %s", (SECRET,), None)
    f.filter(rec)
    assert SECRET not in rec.getMessage() and "***" in rec.getMessage()


def test_meta_key_never_appears_in_logs_traces_errors_or_health(tmp_path, demo_repo, monkeypatch):
    """A whole Meta session: key rejected mid-ask, a 5xx, then good answers, with DEBUG logging everywhere."""
    log_file = tmp_path / "server.log"
    s = meta_settings(tmp_path)

    def handler(req):
        assert req.headers["authorization"] == f"Bearer {SECRET}"
        body = json.loads(req.content)
        if "CaseDraft" in json.dumps(body):
            return httpx.Response(401, json={"error": {"message": "Invalid API key"}})
        return httpx.Response(500, json={"error": "upstream"})

    llm = GuardedLLM(OpenAICompatibleLLM(s, _openai(handler)), s, SpendGuard(s.db_path, 300))
    monkeypatch.setenv("LLM_PROVIDER", "meta")
    monkeypatch.setenv("META_API_KEY", SECRET)
    monkeypatch.setenv("META_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("LOG_PATH", str(log_file))
    from app.config import get_settings

    get_settings.cache_clear()
    deps._llm.cache_clear()
    root = logging.getLogger()
    old_level = root.level
    try:
        meta_app = create_app()
        meta_app.dependency_overrides[deps.get_repo] = lambda: demo_repo
        meta_app.dependency_overrides[deps.get_llm_provider] = lambda: llm
        with TestClient(meta_app, raise_server_exceptions=False) as c:
            setup_logging(log_file, secrets=[SECRET], level=logging.DEBUG)
            logging.getLogger("openai").setLevel(logging.DEBUG)
            logging.getLogger("httpx").setLevel(logging.DEBUG)
            logging.getLogger("kanakku.test").error("leak attempt: %s", SECRET)
            res = c.post("/v1/cases", data={"family_id": "1", "text": LOAN_Q})
            bundle = c.get(f"/v1/cases/{res.json()['case_id']}")
            health = c.get("/health")
            bad = c.get("/v1/cases/123456")
            outputs = [res.text, bundle.text, health.text, bad.text]
        for h in root.handlers:
            h.flush()
        logged = log_file.read_text()
        assert "leak attempt: ***" in logged and "POST /v1/cases" in logged
        assert health.json()["provider"]["name"] == "meta"
        for text in [logged, *outputs]:
            assert SECRET not in text
    finally:
        get_settings.cache_clear()
        deps._llm.cache_clear()
        root.setLevel(old_level)
        setup_logging(None)


def test_qr_link_matches_what_the_app_parses():
    from scripts.print_qr import connect_link

    link = connect_link("http://192.168.1.10:8013", "abc-_1")
    assert link == "kanakku://connect?url=http%3A%2F%2F192.168.1.10%3A8013&token=abc-_1"  # app/test/models_test.dart


def test_log_viewer_is_one_readable_line():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "log_view.py"
    spec = importlib.util.spec_from_file_location("log_view", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raw = json.dumps({"ts": "2026-11-04T10:36:12.123+00:00", "level": "INFO", "request_id": "abcdef123456",
                      "msg": "POST /v1/cases -> 202", "ms": 12.4})  # fmt: skip
    assert mod.line(raw, False) == "10:36:12 INFO    abcdef12 POST /v1/cases -> 202  (12 ms)"
    assert "\033[" in mod.line(raw, True)
    assert mod.line("not json", False) == "not json"
