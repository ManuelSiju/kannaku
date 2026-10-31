"""Fictional demo family. `make seed-demo` (idempotent) / `make reset-demo` (wipe DB, then seed).

Lakshmi (primary) and guardian Arun. All names and products are fictional.
monthly_expenses EXCLUDES loan EMIs; EMIs are family_item rows (kind "loan").
Family 1 speaks English; family 2 (Saraswathi, guardian Meera) speaks Malayalam for language tests.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.db.repo import FamilyItem, Repo

DEMO_FAMILY_ID = 1
DEMO_FAMILY_ML_ID = 2  # Malayalam-speaking demo family (for language tests)


def seed(repo: Repo) -> bool:
    """Returns False if the demo family already exists (nothing changed)."""
    seed_ml(repo)
    if repo.get_family(DEMO_FAMILY_ID) is not None:
        return False
    repo.create_family(language="en", guardian_code="DEMO-ARUN", id=DEMO_FAMILY_ID)
    lakshmi = repo.add_member(DEMO_FAMILY_ID, "Lakshmi", "primary")
    repo.add_member(DEMO_FAMILY_ID, "Arun", "guardian")
    repo.set_profile_value(
        lakshmi, "monthly_income", 45_000, "voice", source_ref="onboarding voice note", confirmed=True
    )
    repo.set_profile_value(lakshmi, "monthly_expenses", 28_000, "typed", source_ref="onboarding", confirmed=True)
    repo.set_profile_value(lakshmi, "savings", 1_60_000, "document", source_ref="passbook photo", confirmed=True)
    repo.save_item(
        DEMO_FAMILY_ID,
        FamilyItem(
            kind="policy",
            name="Money-back policy (fictional)",
            amount=12_000,
            frequency="yearly",
            source="document",
            source_ref="policy bond photo",
        ),
        confirmed=True,
    )
    repo.save_item(
        DEMO_FAMILY_ID,
        FamilyItem(
            kind="loan",
            name="Scooter loan EMI",
            amount=2_400,
            frequency="monthly",
            end_date="2027-03-31",
            source="voice",
        ),
        confirmed=True,
    )
    return True


def seed_ml(repo: Repo) -> bool:
    """Saraswathi (primary, Malayalam) and guardian Meera. Fictional."""
    if repo.get_family(DEMO_FAMILY_ML_ID) is not None:
        return False
    repo.create_family(language="ml", guardian_code="DEMO-MEERA", id=DEMO_FAMILY_ML_ID)
    sara = repo.add_member(DEMO_FAMILY_ML_ID, "Saraswathi", "primary")
    repo.add_member(DEMO_FAMILY_ML_ID, "Meera", "guardian")
    repo.set_profile_value(sara, "monthly_income", 30_000, "voice", confirmed=True)
    repo.set_profile_value(sara, "monthly_expenses", 20_000, "typed", confirmed=True)
    repo.set_profile_value(sara, "savings", 90_000, "document", source_ref="passbook photo", confirmed=True)
    return True


def reset(path: Path) -> Repo:
    for suffix in ("", "-journal", "-wal", "-shm"):
        Path(f"{path}{suffix}").unlink(missing_ok=True)
    repo = Repo(path)
    seed(repo)
    return repo


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="delete the database first")
    args = ap.parse_args()
    path = get_settings().db_path
    if args.reset:
        reset(path).close()
        print(f"✔ reset {path} and seeded demo family {DEMO_FAMILY_ID}")
    else:
        repo = Repo(path)
        print(f"✔ seeded demo family {DEMO_FAMILY_ID}" if seed(repo) else f"demo family {DEMO_FAMILY_ID} already there")
        repo.close()


if __name__ == "__main__":
    main()
