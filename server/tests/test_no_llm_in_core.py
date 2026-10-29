"""Phase-2 core (numbers, engines, rules) must stay deterministic: no LLM / provider imports."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
CORE = [
    "numbers/indian_number_parser.py",
    "engines/fact.py",
    "engines/finance.py",
    "engines/tip_signals.py",
    "pipeline/scam_rules.py",
    "pipeline/evidence.py",
    "pipeline/consensus.py",
    "pipeline/privacy.py",
    "pipeline/router.py",
]
BANNED = ("openai", "app.providers", "httpx", "faster_whisper", "pytesseract")


@pytest.mark.parametrize("rel", CORE)
def test_no_llm_imports(rel):
    tree = ast.parse((APP / rel).read_text())
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not [m for m in names if m.startswith(BANNED)]
