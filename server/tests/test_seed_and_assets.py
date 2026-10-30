from app.db.repo import Repo
from app.db.seed_demo import DEMO_FAMILY_ID, reset, seed
from app.mcp_server.tools import STOCKS_DIR


def test_seed_is_idempotent(repo):
    assert seed(repo) is True
    assert seed(repo) is False
    assert [m["name"] for m in repo.members(DEMO_FAMILY_ID)] == ["Lakshmi", "Arun"]
    assert {pv.field: (pv.value, pv.source) for pv in repo.profile_values(DEMO_FAMILY_ID)} == {
        "monthly_income": (45_000, "voice"),
        "monthly_expenses": (28_000, "typed"),
        "savings": (1_60_000, "document"),
    }
    items = repo.list_items(DEMO_FAMILY_ID)
    assert [(i.kind, i.amount, i.frequency, i.source) for i in items] == [
        ("policy", 12_000, "yearly", "document"),
        ("loan", 2_400, "monthly", "voice"),
    ]
    assert items[1].end_date.startswith("2027-03")


def test_reset_wipes_extra_data(tmp_path):
    path = tmp_path / "k.db"
    r = Repo(path)
    seed(r)
    r.create_case(DEMO_FAMILY_ID, transcript="hello")
    r.close()
    r = reset(path)
    assert r.get_case(1) is None and r.get_family(DEMO_FAMILY_ID) is not None
    r.close()


def test_demo_assets_exist():
    from app.config import SERVER_ROOT

    assets = SERVER_ROOT / "demo_assets"
    for name in [
        "suraksha_brochure.pdf",
        "suraksha_brochure_p1.png",
        "suraksha_brochure_p3.png",
        "zephyrx_tip.txt",
        "zephyrx_tip.png",
    ]:
        assert (assets / name).stat().st_size > 0
    assert (STOCKS_DIR / "ZEPHYRX.csv").exists()


def test_brochure_pdf_has_the_key_sentence():
    import pdfplumber

    from app.config import SERVER_ROOT

    with pdfplumber.open(SERVER_ROOT / "demo_assets" / "suraksha_brochure.pdf") as pdf:
        assert len(pdf.pages) == 3
        assert "Bonus rates are not guaranteed and may change every year." in pdf.pages[2].extract_text()
        assert "Rs. 10,20,000" in pdf.pages[1].extract_text()
