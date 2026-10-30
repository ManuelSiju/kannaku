"""End-to-end through POST /cases with the LLM mocked by fixtures. Fully offline (PDF has a text layer)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import SERVER_ROOT
from app.main import app
from app.pipeline.events import EventBus
from app.pipeline.explainer import ON_SCREEN
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
    assert details["fd_value"]["value"] == "₹13,44,402.68"
    assert details["surplus_after"]["kind"] == "personal"
    assert details["term.premium"]["source"] == "page_1 (read twice)"

    # the personal amount never reaches a spoken line in discreet mode
    lines = res["spoken_lines"]
    assert [ln["speaker"] for ln in lines] == ["alfii", "dani", "sankz", "alfii"]
    assert lines[2]["text"] == ON_SCREEN
    assert all("9,433" not in ln["text"] for ln in lines)
    assert "3.8%" in lines[1]["text"]
    assert 1 <= len(res["verdict"]["questions"]) <= 3

    bundle = client.get(f"/cases/{res['case_id']}").json()
    dropped = [a for a in bundle["arguments"] if not a["kept"]]
    assert (
        len(dropped) == 1 and "8%" in dropped[0]["drop_reason"] and "high.endowment_return" in dropped[0]["drop_reason"]
    )
    assert [o["rule"] for o in bundle["verdict"]["overrides"]] == ["unbacked_guarantee"]
    blocked = [ln for ln in bundle["spoken_lines"] if not ln["allowed"]]
    assert len(blocked) == 1 and blocked[0]["blocked_reason"].startswith("privacy")
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
    assert details["loan_emi"] == "₹5,166.67" and details["loan_effective_rate"] == "21.6%"
    assert details["surplus_after"] == "₹8,433.33"  # 45,000 - 28,000 - 2,400 EMI - 1,000 policy - 5,166.67
    assert llm.calls == ["CaseDraft", "CouncilOutput", "ExplainerOutput"]
    assert "21.6%" in res["spoken_lines"][1]["text"]


def test_stock_tip_is_red_and_vick_called(harness):
    client, state, _ = harness
    state["llm"] = FakeLLM(load_fixture("stock_tip"))
    res = ask(client, TIP_Q)
    assert res["verdict"]["colour"] == "red"
    assert res["called_agents"] == ["vick", "sankz"]  # 1 lakh is a large share of 1.6 lakh savings
    details = {d["id"]: d["value"] for d in res["screen_details"]}
    assert details["pump_risk"] == "high"
    assert not res["degraded"]


def test_otp_scam_fast_path(harness):
    client, state, repo = harness
    state["llm"] = llm = FakeLLM({})
    res = ask(client, SCAM_Q)
    assert res["verdict"]["colour"] == "red"
    assert res["case_type"] == "scam_or_payment_request"
    assert res["called_agents"] == [] and llm.calls == [] and res["llm_calls"] == 0
    assert {d["id"] for d in res["screen_details"]} >= {"scam.otp_pin_request", "scam.kyc_urgency"}
    assert all(ln["speaker"] == "alfii" for ln in res["spoken_lines"])
    assert repo.list_alerts(1)[0]["note"].startswith("RED: scam warning")


def test_out_of_scope_is_alfii_only(harness):
    client, state, repo = harness
    state["llm"] = llm = FakeLLM(load_fixture("out_of_scope"))
    res = ask(client, "Can you tell me a good recipe for sambar?")
    assert res["called_agents"] == [] and res["verdict"]["colour"] is None
    assert [ln["speaker"] for ln in res["spoken_lines"]] == ["alfii"]
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
    assert res["spoken_lines"][2]["text"] == ON_SCREEN  # no budget left to rewrite: replaced, not spoken
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
    res = ask(client, files=[("audio", ("q.m4a", b"fake-audio", "audio/mp4"))])
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
    assert not any(d["label"].startswith("Could not check") for d in res["screen_details"])
