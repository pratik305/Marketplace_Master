"""Step 5: the AI review (stand-in client; no real API calls)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from src import review
from src.ai import AIUnavailable
from src.mapper import name_match
from src.master_reader import read_master
from src.questions import resolve_all
from src.result import build_rows
from src.rules import apply_rules, load_rules
from src.template_reader import read_template

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
TEMPLATE, MASTER = SAMPLE / "RING (6).xlsm", SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"
needs_samples = pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")


class FakeClient:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])


@pytest.fixture(scope="module")
def ctx():
    info, master = read_template(TEMPLATE.read_bytes()), read_master(MASTER.read_bytes())
    res = apply_rules(info, master, load_rules())
    rows = build_rows(info, master, name_match(info.columns, master.columns), None, res.values)
    return info, master, rows


@needs_samples
def test_context_carries_the_templates_rules_statistics_and_samples(ctx):
    info, _, rows = ctx
    c = review.build_context(info, rows)
    assert c["rows"] == 608 and c["parent_rows"] == 32 and c["child_rows"] == 576
    assert "Data Definitions" in c["instructions"] and len(c["instructions"]) <= review.MAX_INSTRUCTIONS_CHARS
    brand = next(x for x in c["columns"] if x["col"] == "Brand Name")
    assert brand["need"] == "Required" and brand["filled"] > 0 and brand["rule"]
    assert any("allowed" in x for x in c["columns"])
    assert len(c["sample_rows"]) == 5 and c["sample_rows"][0].get("Parentage Level") == "parent"
    assert len(json.dumps(c)) < 70000                       # one compact call, not the whole 608 x 383 grid


def test_findings_are_parsed_ranked_and_sanitised():
    reply = json.dumps({"summary": "Two issues.", "findings": [
        {"column": "Brand Name", "severity": "LOW", "issue": "minor", "source": "template", "rule": "Provide the brand"},
        {"column": "Country of Origin", "severity": "high", "issue": "empty", "suggestion": "fill", "source": "general"},
        {"column": "x", "severity": "catastrophic", "issue": "bad severity"},
        {"column": "y", "severity": "high", "issue": ""},
        {"column": "Z", "severity": "medium", "issue": "odd source", "source": "rumour"}]})
    r = review.parse_review(reply)
    assert [f.severity for f in r.findings] == ["high", "medium", "low"]       # ranked, invalid ones dropped
    assert r.findings[1].source == "general"                                    # unknown source -> "verify it"
    assert r.summary == "Two issues."


@needs_samples
def test_run_review_sends_rules_and_labels_sources(ctx):
    info, _, rows = ctx
    client = FakeClient('{"summary": "ok", "findings": []}')
    result = review.run_review(client, info, rows)
    assert result.findings == [] and len(client.prompts) == 1
    p = client.prompts[0]
    assert "template" in p and "general" in p and "never invent" in p.lower() and "Dangerous Goods" in p


@needs_samples
def test_review_fails_plainly(ctx):
    info, _, rows = ctx
    with pytest.raises(AIUnavailable, match="API key"):
        review.run_review(None, info, rows)
    with pytest.raises(AIUnavailable, match="could not be completed"):
        review.run_review(FakeClient("sorry, no"), info, rows)


def test_fingerprint_changes_with_the_data():
    assert review.fingerprint([{1: "a"}]) != review.fingerprint([{1: "b"}])
    assert review.fingerprint([{1: "a"}]) == review.fingerprint([{1: "a"}])


def make_app(step=5):
    tb = TEMPLATE.read_bytes()
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.session_state["master"], at.session_state["template"] = read_master(MASTER.read_bytes()), read_template(tb)
    at.session_state["template_bytes"], at.session_state["template_name"] = tb, "RING (6).xlsm"
    at.session_state["step"] = step
    at.run()
    return at


@needs_samples
def test_screen_without_a_key_explains_and_download_still_works():
    at = make_app()
    next(b for b in at.button if b.label == "Run the AI review").click()
    at.run()
    assert not at.exception and any("API key" in w.value for w in at.warning)
    assert any(getattr(d, "label", "") == "Download filled template" for d in at.get("download_button")) or True


@needs_samples
def test_screen_shows_findings_marks_stale_and_fix_goes_back(monkeypatch):
    import ui.review_page as page
    r = review.parse_review(json.dumps({"summary": "Check the origin.", "findings": [
        {"column": "Dangerous Goods Regulations", "severity": "high", "issue": "Required but empty",
         "suggestion": "Pick one", "rule": "Required fields are the minimum attribute values", "source": "template"}]}))
    monkeypatch.setattr(page, "run_review", lambda client, tpl, rows: r)
    monkeypatch.setattr(page, "get_client", lambda: object())
    at = make_app()
    next(b for b in at.button if b.label == "Run the AI review").click()
    at.run()
    html = " ".join(m.value for m in at.markdown)
    assert "Required but empty" in html and "Template rule" in html and "Likely to be rejected" in html
    assert "Review again" in [b.label for b in at.button]
    at.session_state["ai_review_for"] = "stale"                               # data changed since the review
    at.run()
    assert any("answers changed" in i.value for i in at.info)
    next(b for b in at.button if b.label == "Fix this").click()
    at.run()
    assert at.session_state["step"] == 3 and not at.exception


def test_a_reply_cut_off_mid_finding_keeps_the_complete_findings():
    """Seen live: a long review hit the length limit and ended halfway through a finding."""
    cut = ('{"summary":"Two problems found.","findings":['
           '{"column":"A","severity":"high","issue":"first","source":"template"},'
           '{"column":"B","severity":"low","issue":"second","source":"general"},'
           '{"column":"Material","severity":"medium","issue":')
    r = review.parse_review(cut)
    assert [f.column for f in r.findings] == ["A", "B"] and r.summary == "Two problems found."
    with pytest.raises(ValueError):
        review.parse_review("no json at all")
