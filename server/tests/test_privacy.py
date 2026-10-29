import pytest

from app.engines.finance import affordability, endowment_return
from app.pipeline.privacy import Allowed, Blocked, decide_mode, speech_allowed

FACTS = [endowment_return(50_000, 15, 10_20_000, 15), *affordability(45_000, 28_000, 1_60_000, 2_400, 4_167)]


def test_discreet_blocks_citing_personal_fact():
    r = speech_allowed("This would stretch your budget.", ["surplus_after"], FACTS, "discreet")
    assert isinstance(r, Blocked) and "surplus_after" in r.reason


def test_discreet_blocks_personal_amount_even_uncited():
    r = speech_allowed("With 1,60,000 saved you should be careful.", ["endowment_return"], FACTS, "discreet")
    assert isinstance(r, Blocked) and "savings" in r.reason


def test_discreet_allows_offer_facts():
    assert isinstance(
        speech_allowed("This plan returns about 4% a year.", ["endowment_return"], FACTS, "discreet"), Allowed
    )


def test_full_mode_allows_everything():
    assert speech_allowed("You save 1,60,000.", ["surplus_after"], FACTS, "full").allowed


@pytest.mark.parametrize(
    "earphones,alone,second,cue,mode",
    [
        (True, False, None, False, "full"),
        (False, True, None, False, "full"),
        (True, True, False, False, "full"),
        (False, False, None, False, "discreet"),
        (True, False, True, False, "discreet"),
        (False, True, None, True, "discreet"),
        (True, True, True, True, "discreet"),
    ],
)
def test_decide_mode(earphones, alone, second, cue, mode):
    assert decide_mode(earphones, alone, second, cue) == mode
