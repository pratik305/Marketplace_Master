"""Slice 4: drive the real question screen (guards against the endless-rerun bug)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.mapper import name_match
from src.master_reader import read_master
from src.questions import build_queue, distinct_values
from src.rules import apply_rules, load_rules
from src.template_reader import read_template

SAMPLE = Path(__file__).resolve().parent.parent / "sample"
TEMPLATE = SAMPLE / "RING (6).xlsm"
MASTER = SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"
pytestmark = pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")


@pytest.fixture()
def app():
    tb = TEMPLATE.read_bytes()
    tpl, master = read_template(tb), read_master(MASTER.read_bytes())
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=60)
    at.session_state["master"], at.session_state["template"] = master, tpl
    at.session_state["template_bytes"], at.session_state["template_name"] = tb, "RING (6).xlsm"
    at.session_state["answer_style"] = "One at a time"            # the older step-by-step screen
    at.session_state["step"] = 3                                  # the Answers step
    at.run()
    covered = apply_rules(tpl, master, load_rules()).covered()       # the app skips what the rules already fill
    queue = build_queue(tpl, name_match(tpl.columns, master.columns), master, covered=covered)
    return at, queue, master


def choose(at, key, value):
    """Pick a value in whichever widget the screen uses: choice buttons (short lists) or a dropdown."""
    try:
        at.radio(key=key).set_value(value)
    except KeyError:
        at.selectbox(key=key).select(value)


def tpl_default(at, col):
    return at.session_state["template"].defaults.get(col.index)


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()


def test_same_for_all_skip_and_back(app):
    at, queue, _ = app
    assert not at.exception
    i = next(i for i, c in enumerate(queue) if not c.has_dropdown and tpl_default(at, c) is None)
    at.session_state["q_index"] = i
    at.run()
    click(at, "Continue")                                   # nothing entered
    assert at.session_state["q_index"] == i and any("Enter a value" in m.value for m in at.markdown)
    at.text_input(key=f"val_{queue[i].index}").set_value("MY-VALUE")
    click(at, "Continue")
    assert at.session_state["answers"][queue[i].index].value == "MY-VALUE"
    assert at.session_state["q_index"] == i + 1
    click(at, "Skip this column")
    assert at.session_state["answers"][queue[i + 1].index].mode == "skip" and at.session_state["q_index"] == i + 2
    click(at, "Back")
    assert at.session_state["q_index"] == i + 1 and not at.exception


def test_depends_on_master_column(app):
    at, queue, master = app
    i = next(i for i, c in enumerate(queue) if c.has_dropdown)
    col = queue[i]
    at.session_state["q_index"] = i
    at.run()
    at.radio(key=f"mode_{col.index}").set_value("Depends on a master column")
    at.run()
    at.selectbox(key=f"by_{col.index}").select("Color")
    at.run()
    first = distinct_values(master, "Color")[0]
    choose(at, f"lk_{col.index}_{first}", col.allowed[0])
    click(at, "Continue")
    ans = at.session_state["answers"][col.index]
    assert ans.mode == "lookup" and ans.by == "Color" and ans.table == {first: col.allowed[0]}
    assert not at.exception


def test_one_click_suggestion_and_light_cards(app):
    at, queue, _ = app
    tpl = at.session_state["template"]
    i = next(i for i, c in enumerate(queue) if tpl.defaults.get(c.index) is not None
             and str(tpl.defaults[c.index]).strip() in (c.allowed or [str(tpl.defaults[c.index]).strip()]))
    col = queue[i]
    at.session_state["q_index"] = i
    at.run()
    assert any("Suggested from the template" in m.value for m in at.markdown)     # green suggestion note
    assert any("q-card" in m.value for m in at.markdown)                          # the coloured question card
    click(at, "Use this suggestion and continue")
    assert at.session_state["answers"][col.index].mode == "const"
    assert at.session_state["q_index"] == i + 1 and not at.exception


def test_short_dropdowns_are_choice_buttons(app):
    at, queue, _ = app
    i = next(i for i, c in enumerate(queue) if c.has_dropdown and len(c.allowed) <= 8)
    at.session_state["q_index"] = i
    at.run()
    assert at.radio(key=f"val_{queue[i].index}").options == queue[i].allowed
    assert not at.exception


def test_skip_all_conditionals_jumps_to_what_is_left(app):
    at, queue, _ = app
    click(at, next(b.label for b in at.button if b.label.startswith("Skip all")))
    answers = at.session_state["answers"]
    assert all(answers[c.index].mode == "skip" for c in queue if not c.required)
    assert not any(c.index in answers for c in queue if c.required)          # required ones are never auto-skipped
    assert at.session_state["q_index"] == next(i for i, c in enumerate(queue) if c.required)   # first required left
    assert not at.exception
