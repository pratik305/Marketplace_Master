"""The four-step flow: Upload, Prepare, Answers, Check & download."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.master_reader import read_master
from src.template_reader import read_template

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
TEMPLATE, MASTER = SAMPLE / "RING (6).xlsm", SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"


def app(files_read, step=None):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    if files_read:
        tb = TEMPLATE.read_bytes()
        at.session_state["master"], at.session_state["template"] = read_master(MASTER.read_bytes()), read_template(tb)
        at.session_state["template_bytes"], at.session_state["template_name"] = tb, "RING (6).xlsm"
    if step:
        at.session_state["step"] = step
    at.run()
    return at


def step_buttons(at):
    return {b.label: b for b in at.button if (b.key or "").startswith("stepbtn_")}


def test_before_files_are_read_only_upload_is_open():
    at = app(False, step=3)                                   # even asking for step 3 lands on Upload
    assert not at.exception and at.session_state["step"] == 1
    btns = list(step_buttons(at).values())
    assert len(btns) == 5 and btns[0].disabled is False and all(b.disabled for b in btns[1:])
    assert any(b.label == "Read files" and b.disabled for b in at.button)       # needs both files
    assert not at.dataframe                                    # nothing else is shown yet


@pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")
def test_walk_through_all_steps_with_the_navigation_buttons():
    at = app(True, step=2)
    assert not at.exception and [t.label for t in at.tabs][:2] == ["Built-in rules", "Column mapping"]
    next(b for b in at.button if "Continue to answers" in b.label).click()
    at.run()
    assert at.session_state["step"] == 3 and "Answer sheet" in [s.value for s in at.subheader]
    next(b for b in at.button if "Continue to check" in b.label).click()
    at.run()
    assert at.session_state["step"] == 4 and not at.exception
    next(b for b in at.button if "AI review" in b.label).click()
    at.run()
    assert at.session_state["step"] == 5 and not at.exception
    next(b for b in at.button if "Back" in b.label).click()
    at.run()
    assert at.session_state["step"] == 4 and not at.exception


@pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")
def test_step_bar_jumps_and_marks_finished_steps():
    at = app(True, step=3)
    labels = list(step_buttons(at))
    assert labels[0].startswith("✓") and labels[1].startswith("✓") and not labels[2].startswith("✓")
    step_buttons(at)[labels[1]].click()                        # click "Prepare"
    at.run()
    assert at.session_state["step"] == 2 and not at.exception


@pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")
def test_summary_chips_and_theme_are_present():
    at = app(True, step=3)
    html = " ".join(m.value for m in at.markdown)
    assert "columns filled by rules" in html and "answers given" in html      # the quiet summary line
    assert "mast-title" in html and "--accent" in html                         # masthead and the theme stylesheet
