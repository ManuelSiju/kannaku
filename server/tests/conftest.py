import pytest

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: tests never depend on a developer's local .env
    return Settings(_env_file=None, llm_timeout_s=0.2)
