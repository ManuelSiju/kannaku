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
