"""End-to-end through POST /cases with the LLM mocked by fixtures. Fully offline (PDF has a text layer)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import SERVER_ROOT
from app.main import app
from app.pipeline.events import EventBus
from tests.fakes import TIMEOUT, FakeLLM, FakeSTT, load_fixture

BROCHURE = SERVER_ROOT / "demo_assets" / "kanakavalli_brochure.pdf"
ENDOWMENT_Q = "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?"
LOAN_Q = "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?"
TIP_Q = (
    "I got this message: ZEPHYRX LTD - BIG NEWS COMING! Target Rs. 180 in 2 weeks. Upper circuit guaranteed. "
    "Should I put 1 lakh in it?"
)
SCAM_Q = "A man from the bank called. My KYC has expired and he asks me to tell him the OTP."


@pytest.fixture
def harness(demo_repo):
    state = {"llm": FakeLLM(), "stt": FakeSTT(""), "bus": EventBus()}
    app.dependency_overrides[deps.get_repo] = lambda: demo_repo
    app.dependency_overrides[deps.get_llm_provider] = lambda: state["llm"]
    app.dependency_overrides[deps.get_stt_provider] = lambda: state["stt"]
    app.dependency_overrides[deps.get_bus] = lambda: state["bus"]
    with TestClient(app) as client:
        yield client, state, demo_repo
    app.dependency_overrides.clear()


def ask(client, text=None, files=None, **form):
    data = {"family_id": "1", **{k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in form.items()}}
    if text:
        data["text"] = text
    r = client.post("/cases", data=data, files=files or None)
    assert r.status_code in (200, 202), r.text
    return r.json()


def brochure_files():
    return [("files", ("kanakavalli_brochure.pdf", BROCHURE.read_bytes(), "application/pdf"))]


# ---------------------------------------------------------------- the five acceptance cases


def test_endowment_brochure_is_red(harness):
    client, state, repo = harness
    state["llm"] = llm = FakeLLM(load_fixture("endowment"))
    res = ask(client, ENDOWMENT_Q, brochure_files())

    assert res["verdict"]["colour"] == "red"
    assert res["called_agents"] == ["dani", "sankz"]
    assert not res["degraded"], res["degraded_steps"]
    assert llm.calls == ["CaseDraft", "CouncilOutput", "ExplainerOutput", "RewriteOutput"]
    assert res["llm_calls"] == 4
    assert res["privacy_mode"] == "discreet"

    # numbers match the phase-2 golden values
    details = {d["id"]: d for d in res["screen_details"]}
    assert details["endowment_return"]["value"] == "3.8%"
    assert details["fd_value"]["value"] == "₹13.44 lakh"
    assert details["surplus_after"]["kind"] == "personal"
    assert details["term.premium"]["source"] == "Brochure page 1 · checked"
    assert details["profile.savings"]["source"] == "From your passbook photo"
    assert details["ref.fd_rate"]["source"] == "Assumption · as of 1 Oct 2026"

    # the personal amount never reaches a spoken line in discreet mode; Sankz falls back to his own checked argument
    lines = res["spoken_lines"]
    assert [ln["speaker"] for ln in lines] == ["alfii", "dani", "sankz", "alfii"]
    assert all("9,433" not in ln["text"] for ln in lines)
    assert lines[0]["text"] == "Let me ask Dani and Sankz."
    assert lines[1]["text"] == "This plan grows only about 3.8 percent a year, lower than a fixed deposit."
    assert lines[2]["text"].startswith("Only 7.5 lakh rupees is guaranteed")
    assert "15 lakh rupees is not guaranteed" in lines[3]["text"]
    assert [c["kind"] for c in res["council"]] == ["opener", "agent", "agent", "conclusion"]
    assert res["council_words"] <= 110 and res["council_seconds"] == round(res["council_words"] / 150 * 60, 1)
    assert res["short_answer"]["colour"] == "red" and len(res["short_answer"]["text"].split()) <= 20
    assert res["suggested_followups"][0] == "What would an FD give me instead?"
    assert res["claims"][0]["status"] == "contradicted" and res["claims"][0]["evidence"].startswith("Bonus rates")
    notes = {d["id"]: d["label"] for d in res["screen_details"] if d["id"].startswith("note.")}
    assert notes["note.premium_share_of_savings"] == "This premium is 31.2% of your savings each year."
    assert notes["note.surplus_after"] == "After this, you would have ₹9,433 left each month."
    assert 1 <= len(res["verdict"]["questions"]) <= 3

    bundle = client.get(f"/cases/{res['case_id']}").json()
    dropped = [a for a in bundle["arguments"] if not a["kept"]]
    assert len(dropped) == 1 and "raw number" in dropped[0]["drop_reason"] and "8%" in dropped[0]["drop_reason"]
    assert [o["rule"] for o in bundle["verdict"]["overrides"]] == ["unbacked_guarantee"]
    assert all(ln["allowed"] for ln in bundle["spoken_lines"])
    explainer = next(tr for tr in bundle["trace"] if tr["step"] == "explainer")
    assert explainer["detail"]["rewrite_used"] is True and explainer["detail"]["dropped_turns"] == []
    assert bundle["result"]["case_id"] == res["case_id"]
    assert {t["step"] for t in bundle["trace"]} >= {
        "ingest",
        "scam_rules",
        "case_builder",
        "verify_terms",
        "compute",
        "router",
        "council",
        "consensus",
        "privacy",
        "explainer",
    }
    assert len(repo.list_alerts(1)) == 1


def test_flat_rate_loan_is_red_or_yellow(harness):
    client, state, _ = harness
    state["llm"] = llm = FakeLLM(load_fixture("flat_loan"))
    res = ask(client, LOAN_Q)
    assert res["verdict"]["colour"] in ("red", "yellow")
    assert res["called_agents"] == ["sankz"]
    details = {d["id"]: d["value"] for d in res["screen_details"]}
    assert details["loan_emi"] == "₹5,167" and details["loan_effective_rate"] == "21.6%"
    assert details["surplus_after"] == "₹8,433"  # 45,000 - 28,000 - 2,400 EMI - 1,000 policy - 5,166.67
    assert llm.calls == ["CaseDraft", "CouncilOutput", "ExplainerOutput"]
    assert "21.6 percent" in res["spoken_lines"][1]["text"]


def test_stock_tip_is_red_and_vick_called(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("stock_tip"))
    res = ask(client, TIP_Q)
    assert res["verdict"]["colour"] == "red"
    assert res["called_agents"] == ["vick", "sankz"]  # 1 lakh is a large share of 1.6 lakh savings
    details = {d["id"]: d["value"] for d in res["screen_details"]}
    assert details["pump_risk"] == "a high pump-and-dump risk"
    assert not res["degraded"]
    # Sankz's lines all talk about savings: in discreet mode his turn becomes Alfii's note line
    speakers = [ln["speaker"] for ln in res["spoken_lines"]]
    assert "sankz" not in speakers
    assert "Sankz has left a note about your budget on your screen." in [ln["text"] for ln in res["spoken_lines"]]
    assert res["spoken_lines"][-1]["text"].endswith("Talk to Arun before you decide.")
    notes = [d["label"] for d in res["screen_details"] if d["id"].startswith("note.")]
    assert notes == ["This amount is 62.5% of your savings."]


def test_otp_scam_fast_path(harness):
    client, state, repo = harness
    state["llm"] = llm = FakeLLM({})
    res = ask(client, SCAM_Q)
    assert res["verdict"]["colour"] == "red"
    assert res["case_type"] == "scam_or_payment_request"
    assert res["called_agents"] == [] and llm.calls == [] and res["llm_calls"] == 0
    assert {d["id"] for d in res["screen_details"]} >= {"scam.otp_pin_request", "scam.kyc_urgency"}
    assert all(ln["speaker"] == "alfii" for ln in res["spoken_lines"])
    assert [ln["text"] for ln in res["spoken_lines"]] == [
        "You did the right thing by asking me.",
        "No real bank ever asks for your OTP or PIN.",
        "Please don't share any code or pay anyone. Hang up and call your bank yourself.",
    ]
    assert repo.list_alerts(1)[0]["note"].startswith("RED: scam warning")


def test_unknown_case_type_asks_one_clarifying_question(harness):
    client, state, _ = harness
    state["llm"] = llm = FakeLLM(load_fixture("unknown"))
    res = ask(client, "What about this one?")
    assert res["case_type"] == "unknown" and res["called_agents"] == [] and res["verdict"]["colour"] is None
    assert res["spoken_lines"][0]["text"] == "Is this about a loan, a policy, an investment or a payment?"
    assert llm.calls == ["CaseDraft"]


def test_out_of_scope_is_alfii_only(harness):
    client, state, repo = harness
    state["llm"] = llm = FakeLLM(load_fixture("out_of_scope"))
    res = ask(client, "Can you tell me a good recipe for sambar?")
    assert res["called_agents"] == [] and res["verdict"]["colour"] is None
    assert [ln["speaker"] for ln in res["spoken_lines"]] == ["alfii"]
    assert len(res["suggested_followups"]) == 3
    assert llm.calls == ["CaseDraft"]
    assert repo.list_alerts(1) == []


# ---------------------------------------------------------------- limits and failures


def test_forced_timeout_degrades_not_crashes(harness):
    client, state, _ = harness
    script = load_fixture("endowment")
    script["CouncilOutput"] = TIMEOUT
    state["llm"] = FakeLLM(script)
    res = ask(client, ENDOWMENT_Q, brochure_files())
    assert res["degraded"] is True and "council" in res["degraded_steps"]
    assert res["verdict"]["colour"] == "yellow"  # no votes invented; overrides still apply
    assert res["spoken_lines"]


def test_llm_calls_never_exceed_four_even_with_debate(harness):
    client, state, repo = harness
    script = load_fixture("endowment")
    split = json.loads(json.dumps(script["CouncilOutput"]))
    split["opinions"][0]["stance"] = "for"  # dani for, sankz against -> disagreement 1.0 -> debate
    script["CouncilOutput"] = [split, split]
    state["llm"] = llm = FakeLLM(script)
    res = ask(client, ENDOWMENT_Q, brochure_files())
    assert llm.calls == ["CaseDraft", "CouncilOutput", "CouncilOutput", "ExplainerOutput"]
    assert res["llm_calls"] == 4
    # no budget left to rewrite: Sankz falls back to his own checked argument (never a bare fallback sentence)
    assert res["spoken_lines"][2]["speaker"] == "sankz"
    assert res["spoken_lines"][2]["text"].startswith("Only 7.5 lakh rupees is guaranteed")
    trace = {t["step"]: t for t in client.get(f"/cases/{res['case_id']}").json()["trace"]}
    assert trace["debate"]["outcome"] == "ok"


def test_full_privacy_mode_with_earphones_speaks_personal_line(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("endowment"))
    res = ask(client, ENDOWMENT_Q, brochure_files(), earphones=True)
    assert res["privacy_mode"] == "full"
    assert "9,433" in res["spoken_lines"][2]["text"]


def test_context_cue_forces_discreet(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("endowment"))
    res = ask(client, "The agent is here with me. " + ENDOWMENT_Q, brochure_files(), earphones=True)
    assert res["privacy_mode"] == "discreet"


def test_audio_question(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("flat_loan"))
    state["stt"] = FakeSTT(LOAN_Q)
    res = ask(client, files=[("audio", ("q.m4a", b"\x00\x00\x00\x18ftypM4A fake-audio", "audio/mp4"))])
    assert res["verdict"]["colour"] in ("red", "yellow") and res["called_agents"] == ["sankz"]


# ---------------------------------------------------------------- events, async, errors


def test_events_replay_after_finish(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("flat_loan"))
    res = ask(client, LOAN_Q)
    with client.stream("GET", f"/cases/{res['case_id']}/events") as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    assert types[0] == "step_started" and types[-1] == "done"
    assert {"agent_called", "agent_done", "step_finished"} <= set(types)


def test_wait_false_returns_case_id_then_streams(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("flat_loan"))
    out = ask(client, LOAN_Q, wait=False)
    assert out["status"] == "running"
    with client.stream("GET", f"/cases/{out['case_id']}/events") as r:
        last = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")][-1]
    assert last["type"] == "done" and last["verdict"] in ("red", "yellow")
    assert client.get(f"/cases/{out['case_id']}").json()["result"]["called_agents"] == ["sankz"]


def test_follow_up_reuses_case(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("flat_loan"))
    first = ask(client, LOAN_Q)
    second = ask(client, "And what if I pay it back early?", case_id=first["case_id"])
    assert second["case_id"] == first["case_id"]


def test_bad_requests(harness):
    client, _, _ = harness
    assert client.post("/cases", data={"family_id": "1"}).status_code == 422
    assert client.post("/cases", data={"family_id": "99", "text": "hi"}).status_code == 404
    assert client.get("/cases/999").status_code == 404


def test_letter(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("endowment"))
    res = ask(client, ENDOWMENT_Q, brochure_files())
    text = client.post(f"/cases/{res['case_id']}/letter", json={"kind": "cancel", "sender_name": "Lakshmi"}).json()[
        "text"
    ]
    assert "cancel" in text.lower() and "Lakshmi" in text and "3.8%" in text


def _tesseract() -> bool:
    import shutil

    return shutil.which("tesseract") is not None


@pytest.mark.skipif(not _tesseract(), reason="tesseract not installed")
def test_endowment_from_brochure_photos_uses_ocr(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("endowment"))
    photos = [
        (
            "files",
            (f"p{i}.png", (SERVER_ROOT / "demo_assets" / f"kanakavalli_brochure_p{i}.png").read_bytes(), "image/png"),
        )
        for i in (1, 2, 3)
    ]
    res = ask(client, ENDOWMENT_Q, photos)
    assert res["verdict"]["colour"] == "red" and not res["degraded"], res["degraded_steps"]
    details = {d["id"]: d for d in res["screen_details"]}
    assert details["endowment_return"]["value"] == "3.8%"
    assert details["term.premium"]["source"] == "Brochure page 1 · read once"  # text model read the OCR text only
    assert not any(d["label"].startswith("Could not check") for d in res["screen_details"])


def test_opener_is_templated_and_sent_as_event_before_council(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("stock_tip"))
    res = ask(client, TIP_Q)
    assert res["spoken_lines"][0] == {"speaker": "alfii", "text": "Let me ask Vick and Sankz."}
    with client.stream("GET", f"/cases/{res['case_id']}/events") as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    opener = next(e for e in events if e["type"] == "alfii_opener")
    assert opener["text"] == "Let me ask Vick and Sankz."
    council_start = next(i for i, e in enumerate(events) if e.get("step") == "council")
    assert types.index("alfii_opener") < council_start


def test_raw_number_auto_placeholder_recorded_in_trace(harness):
    client, state, _ = harness
    script = load_fixture("endowment")
    script["CouncilOutput"]["opinions"][0]["arguments"][0]["text"] = "This plan returns only about 3.8% a year."
    state["llm"] = FakeLLM(script)
    res = ask(client, ENDOWMENT_Q, brochure_files())
    bundle = client.get(f"/cases/{res['case_id']}").json()
    council = next(t for t in bundle["trace"] if t["step"] == "council")
    assert council["detail"]["auto_placeholder"] == ["auto_placeholder '3.8%' -> {endowment_return}"]
    assert any(a["kept"] and a["text"] == "This plan returns only about 3.8% a year." for a in bundle["arguments"])


def test_endowment_is_not_market_linked_even_if_builder_says_so(harness):
    client, state, _ = harness
    script = load_fixture("endowment")
    script["CaseDraft"]["flags"] = ["market_linked"]
    script["CaseDraft"]["market_linked_quote"] = "returns depend on the stock market"
    state["llm"] = FakeLLM(script)
    res = ask(client, ENDOWMENT_Q, brochure_files())
    assert res["called_agents"] == ["dani", "sankz"]
    script["CaseDraft"]["case_type"] = "ulip"
    state["llm"] = FakeLLM(script)
    res = ask(client, ENDOWMENT_Q, brochure_files())
    assert res["called_agents"] == ["dani", "sankz"] and res["case_type"] == "insurance_offer"


def test_comparison_facts_present(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("endowment"))
    details = {d["id"]: d["value"] for d in ask(client, ENDOWMENT_Q, brochure_files())["screen_details"]}
    assert details["cmp_return_low_vs_fd"] == "lower than"
    assert details["cmp_return_high_vs_fd"] == "higher than"
    assert details["cmp_guaranteed_vs_fd"] == "lower than"
    assert details["cmp_return_low_vs_inflation"] == "lower than"
    assert details["emi_share"] == "5.3%"  # the premium is not an EMI: only the scooter loan counts
    assert details["premium_share_of_income"] == "9.3%"
    assert details["f_return_guaranteed"] == "0%"
    state["llm"] = FakeLLM(load_fixture("flat_loan"))
    details = {d["id"]: d["value"] for d in ask(client, LOAN_Q)["screen_details"]}
    assert details["cmp_effective_vs_quoted"] == "higher than"
    assert details["cmp_effective_vs_typical"] == "higher than"


def test_stock_symbol_fallback_when_builder_omits_it(harness):
    client, state, _ = harness
    script = load_fixture("stock_tip")
    script["CaseDraft"]["stock_symbol"] = None
    state["llm"] = FakeLLM(script)
    details = {d["id"]: d["value"] for d in ask(client, TIP_Q)["screen_details"]}
    assert details["pump_risk"] == "a high pump-and-dump risk"


@pytest.mark.skipif(not _tesseract(), reason="tesseract not installed")
def test_photos_read_twice_when_the_vision_model_reads_them(harness):
    client, state, _ = harness
    state["llm"] = llm = FakeLLM(load_fixture("endowment"), vision=True)
    res = ask(client, ENDOWMENT_Q, _photos())
    assert llm.image_calls == 1
    details = {d["id"]: d for d in res["screen_details"]}
    assert details["term.premium"]["source"] == "Brochure page 1 · read twice"


@pytest.mark.skipif(not _tesseract(), reason="tesseract not installed")
def test_vision_failure_falls_back_to_ocr_text_and_says_read_once(harness):
    client, state, _ = harness
    state["llm"] = llm = FakeLLM(load_fixture("endowment"), vision=True, vision_fails=True)
    res = ask(client, ENDOWMENT_Q, _photos())
    assert llm.calls[:2] == ["CaseDraft", "CaseDraft"]  # vision attempt, then the text model on the OCR text
    assert res["verdict"]["colour"] == "red" and "case_builder" in res["degraded_steps"]
    details = {d["id"]: d for d in res["screen_details"]}
    assert details["term.premium"]["source"] == "Brochure page 1 · read once"


def _photos():
    return [
        (
            "files",
            (f"p{i}.png", (SERVER_ROOT / "demo_assets" / f"kanakavalli_brochure_p{i}.png").read_bytes(), "image/png"),
        )
        for i in (1, 2, 3)
    ]


def test_malayalam_family_gets_malayalam_templates_and_spoken_numbers(harness):
    client, state, _ = harness
    script = load_fixture("flat_loan")
    script["ExplainerOutput"]["agent_lines"][0]["text"] = "ഈ ലോണിന് യഥാർത്ഥത്തിൽ വർഷം {loan_effective_rate} ചെലവാകും."
    script["ExplainerOutput"]["verdict_sentence"]["text"] = "ഈ ലോൺ ഇപ്പോൾ എടുക്കരുത്."
    state["llm"] = FakeLLM(script)
    res = client.post("/cases", data={"family_id": "2", "text": LOAN_Q}).json()
    assert res["language"] == "ml"
    lines = [ln["text"] for ln in res["spoken_lines"]]
    assert lines[0] == "ഞാൻ സാങ്ക്സ്-നോട് ചോദിക്കട്ടെ."
    assert lines[1] == "ഈ ലോണിന് യഥാർത്ഥത്തിൽ വർഷം 21.6 ശതമാനം ചെലവാകും."
    assert lines[-1].startswith("ഈ ലോൺ ഇപ്പോൾ എടുക്കരുത്.")
    assert "Meera" in lines[-1]  # red -> next step: talk to the guardian (Malayalam template)
    assert res["suggested_followups"][0] == "യഥാർത്ഥ പലിശ എത്രയാണ്?"
