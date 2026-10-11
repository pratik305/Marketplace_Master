"""Answer sheet screen: pre-fill, apply, remember, and Claude proposals (stand-in client)."""
import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.master_reader import read_master
from src.template_reader import read_template

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
TEMPLATE, MASTER = SAMPLE / "RING (6).xlsm", SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"
pytestmark = pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")


def make_app():
    tb = TEMPLATE.read_bytes()
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.session_state["master"], at.session_state["template"] = read_master(MASTER.read_bytes()), read_template(tb)
    at.session_state["template_bytes"], at.session_state["template_name"] = tb, "RING (6).xlsm"
    at.run()
    return at


def rows(at):
    return {int(k[6:]): v for k, v in at.session_state.filtered_state.items() if k.startswith("sheet_") and k[6:].isdigit()}


def by_label(at, label):
    return next(c for c in at.session_state["template"].columns if c.label == label)


def test_sheet_shows_all_remaining_columns_prefilled_where_possible():
    at = make_app()
    assert not at.exception and "Answer sheet" in [s.value for s in at.subheader]
    r = rows(at)
    assert len(r) >= 90
    assert 0 < sum(1 for v in r.values() if v) < len(r)          # template suggestions pre-filled, not everything
    assert len(at.tabs) >= 3                                       # grouped by template section


def test_apply_stores_answers_blank_means_skip_and_remembers():
    at = make_app()
    dg = by_label(at, "Dangerous Goods Regulations")
    text_col = next(c for c in at.session_state["template"].columns if c.must_address and not c.has_dropdown
                    and f"sheet_{c.index}" in at.session_state.filtered_state and c.index != dg.index)
    at.text_input(key=f"sheet_{text_col.index}").set_value("My value")
    if dg.has_dropdown:
        at.selectbox(key=f"sheet_{dg.index}").select(dg.allowed[0])
    next(b for b in at.button if b.label == "Apply all answers").click()
    at.run()
    assert not at.exception
    ans = at.session_state["answers"]
    assert ans[text_col.index].mode == "const" and ans[text_col.index].value == "My value"
    assert any(a.mode == "skip" for a in ans.values())             # blank rows are skipped
    saved = json.loads(Path(os.environ["ANSWERS_FILE"]).read_text())
    assert saved[text_col.key]["value"] == "My value"
    assert not any(a.get("mode") == "skip" for a in saved.values())

    again = make_app()                                              # a second run of the same template
    assert again.session_state["saved_answers"][text_col.index].value == "My value"
    assert rows(again)[text_col.index] == "My value"               # pre-filled from last time


def test_claude_proposals_fill_blank_rows_only(monkeypatch):
    import ui.answer_sheet as sheet
    at0 = make_app()
    blank = next(c for c in at0.session_state["template"].columns if c.must_address and not c.has_dropdown
                 and c.index in rows(at0) and not rows(at0)[c.index])
    monkeypatch.setattr(sheet, "propose_answers", lambda client, cols, sample: {blank.index: ("Proposed", 0.9)})
    monkeypatch.setattr(sheet, "get_client", lambda: object())
    at = make_app()
    next(b for b in at.button if b.label == "Let Claude propose answers").click()
    at.run()
    assert not at.exception and rows(at)[blank.index] == "Proposed"
    assert at.session_state["answers"].get(blank.index) is None     # proposals are only pre-filled, never applied


def test_without_a_key_the_proposal_button_explains(monkeypatch):
    at = make_app()
    next(b for b in at.button if b.label == "Let Claude propose answers").click()
    at.run()
    assert not at.exception and any("API key" in w.value for w in at.warning)
