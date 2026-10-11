"""The three looks, and the real product on screen."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.master_reader import read_master
from src.template_reader import read_template
from ui import themes

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
TEMPLATE, MASTER = SAMPLE / "RING (6).xlsm", SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"
needs_samples = pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")


def make_app(step=3, theme=None):
    tb = TEMPLATE.read_bytes()
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.session_state["master"], at.session_state["template"] = read_master(MASTER.read_bytes()), read_template(tb)
    at.session_state["template_bytes"], at.session_state["template_name"] = tb, "RING (6).xlsm"
    at.session_state["step"] = step
    if theme:
        at.session_state["theme"] = theme
    at.run()
    return at


def html_of(at):
    return " ".join(m.value for m in at.markdown)


def test_three_distinct_looks_with_the_agreed_traits():
    assert list(themes.THEMES) == ["Boutique", "Sheet", "Workshop"]
    accents = {n: t["accent"] for n, t in themes.THEMES.items()}
    assert len(set(accents.values())) == 3
    for name, t in themes.THEMES.items():
        css = themes.css(name)
        assert t["accent"] in css and t["head"] in css and "gradient" not in css          # flat: no gradient banner
        assert "box-shadow: none" in css
    assert "Cormorant" in themes.THEMES["Boutique"]["head"] and themes.THEMES["Workshop"]["note"].startswith("'Caveat'")
    assert themes.THEMES["Sheet"]["radius"] == "0px" and themes.THEMES["Sheet"]["accent"] == "#1e7145"   # grid + sheet green


@needs_samples
@pytest.mark.parametrize("theme", list(themes.THEMES))
def test_every_look_works_on_every_step(theme):
    for step in (1, 2, 3, 4, 5):
        at = make_app(step, theme)
        assert not at.exception, (theme, step)
    assert themes.THEMES[theme]["accent"] in html_of(at)                                    # its stylesheet is the one in use


@needs_samples
def test_switching_the_look_changes_the_page():
    at = make_app(3, "Boutique")
    assert themes.THEMES["Sheet"]["accent"] not in html_of(at) and at.radio(key="theme").value == "Boutique"
    at.radio(key="theme").set_value("Sheet")
    at.run()
    assert themes.THEMES["Sheet"]["accent"] in html_of(at) and not at.exception


@needs_samples
def test_the_real_product_is_shown_from_the_master_then_from_the_finished_rows():
    at = make_app(3)
    master = at.session_state["master"]
    first_child = int(at.session_state["preview_no"]) - 1
    assert master.iloc[first_child]["CATEGORY"] != "PARENT"                                  # starts on a real variation
    h = html_of(at)
    assert 'class="product"' in h and "<img src=\"https://" in h
    assert str(master.iloc[first_child]["Sku Code"]) in h and str(master.iloc[first_child]["Sku Name"])[:30] in h
    at.session_state["step"] = 4
    at.run()
    h4 = html_of(at)
    assert str(master.iloc[first_child]["Sku Code"]) in h4 and "variation" in h4 and "<ul>" in h4   # finished listing + bullets


@needs_samples
def test_browsing_products_and_a_parent_borrows_its_childs_photo():
    at = make_app(3)
    start = int(at.session_state["preview_no"])
    next(b for b in at.button if b.label == "Next ›").click()
    at.run()
    assert at.session_state["preview_no"] == start + 1 and not at.exception
    at.session_state["preview_no"] = 1                                                      # row 1 is a parent listing
    at.session_state["step"] = 4
    at.run()
    h = html_of(at)
    assert "parent listing" in h and "<img src=\"https://" in h and "no photo" not in h
    assert next(b for b in at.button if b.label == "‹ Prev").disabled                    # nothing before the first


@needs_samples
def test_problems_name_the_real_product():
    at = make_app(4)
    h = html_of(at)
    assert "First: " in h and "SPLDRG" in h                                                  # an actual SKU, not just a row number
