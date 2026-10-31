import pytest

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: tests never depend on a developer's local .env
    return Settings(_env_file=None, llm_timeout_s=0.2)


@pytest.fixture
def repo(tmp_path):
    from app.db.repo import Repo

    r = Repo(tmp_path / "test.db")
    yield r
    r.close()


@pytest.fixture
def demo_repo(repo):
    from app.db.seed_demo import seed

    seed(repo)
    return repo


@pytest.fixture
def harness_red_conclusion(demo_repo):
    """Run the flat-loan case with a red conclusion that has a loophole ("do not ... without ...")."""
    from fastapi.testclient import TestClient

    from app.api import deps
    from app.main import app
    from app.pipeline.events import EventBus
    from tests.fakes import FakeLLM, load_fixture

    script = load_fixture("flat_loan")
    script["ExplainerOutput"]["verdict_sentence"]["text"] = "Do not take this loan without clear written terms."
    app.dependency_overrides[deps.get_repo] = lambda: demo_repo
    app.dependency_overrides[deps.get_llm_provider] = lambda: FakeLLM(script)
    app.dependency_overrides[deps.get_bus] = lambda: EventBus()
    with TestClient(app) as client:
        text = "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?"
        res = client.post("/cases", data={"family_id": "1", "text": text}).json()
    app.dependency_overrides.clear()
    return [ln["text"] for ln in res["spoken_lines"]]
