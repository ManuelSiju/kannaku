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
