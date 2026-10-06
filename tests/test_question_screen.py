"""Slice 4: drive the real question screen (guards against the endless-rerun bug)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.mapper import name_match
from src.master_reader import read_master
from src.questions import build_queue, distinct_values
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
    at.run()
    queue = build_queue(tpl, name_match(tpl.columns, master.columns), master)
    return at, queue, master


def choose(at, key, value):
    """Pick a value in whichever widget the screen uses: choice buttons (short lists) or a dropdown."""
    try:
        at.radio(key=key).set_value(value)
    except KeyError:
        at.selectbox(key=key).select(value)


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()


def test_same_for_all_skip_and_back(app):
    at, queue, _ = app
    assert not at.exception
    click(at, "Continue")                                   # nothing entered
    assert at.session_state["q_index"] == 0 and any("Enter a value" in m.value for m in at.markdown)
    at.text_input(key=f"val_{queue[0].index}").set_value("MY-SKU")
    click(at, "Continue")
    assert at.session_state["answers"][queue[0].index].value == "MY-SKU"
    assert at.session_state["q_index"] == 1
    click(at, "Skip this column")
    assert at.session_state["answers"][queue[1].index].mode == "skip" and at.session_state["q_index"] == 2
    click(at, "Back")
    assert at.session_state["q_index"] == 1 and not at.exception


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
