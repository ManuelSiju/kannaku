from app.config import REPO_ROOT, Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.llm_base_url == "http://localhost:8080/v1"
    assert s.llm_max_calls_per_ask == 4
    assert s.llm_timeout_s == 20
    assert s.stt_provider == "faster_whisper"
    assert s.ocr_langs == "eng+mal"
    assert s.db_path == REPO_ROOT / "server" / "kanakku.db"


def test_env_override_and_relative_paths(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("LLM_MODEL", "muse-spark-1.3")
    monkeypatch.setenv("DB_PATH", "server/other.db")
    s = Settings(_env_file=None)
    assert s.llm_base_url == "https://api.meta.ai/v1"
    assert s.llm_model == "muse-spark-1.3"
    assert s.db_path == REPO_ROOT / "server" / "other.db"
