from fastapi.testclient import TestClient

from app.api import health
from app.main import app


def test_health_reports_providers(monkeypatch):
    async def fake_llm():
        return {"provider": "openai_compatible", "reachable": False}

    monkeypatch.setattr(health, "llm_status", fake_llm)
    monkeypatch.setattr(health, "ocr_status", lambda: {"provider": "tesseract", "reachable": False})
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["providers"]) == {"llm", "stt", "ocr", "tts"}
    assert body["providers"]["llm"]["reachable"] is False
    assert body["providers"]["tts"]["reachable"] is True


async def test_llm_status_flags_missing_model(monkeypatch):
    import httpx

    real_client = httpx.AsyncClient

    def fake_client(**kwargs):
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"data": [{"id": "other-model"}]}))
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(health.httpx, "AsyncClient", fake_client)
    out = await health.llm_status()
    assert out["reachable"] is True
    assert out["model_available"] is False
    assert "llm-pull" in out["error"]
