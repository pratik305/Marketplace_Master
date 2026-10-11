"""Saved answers and Claude proposals (no real API calls)."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import ai
from src.answer_store import load_answers, save_answers
from src.questions import CONST, LOOKUP, SKIP, Answer
from src.template_reader import read_template

SAMPLE = Path(__file__).resolve().parent.parent / "sample"
TEMPLATE = SAMPLE / "RING (6).xlsm"
pytestmark = pytest.mark.skipif(not TEMPLATE.exists(), reason="sample/ files not present")


@pytest.fixture(scope="module")
def tpl():
    return read_template(TEMPLATE.read_bytes())


def test_saved_answers_round_trip_and_skip_nothing_real(tpl, tmp_path):
    f = tmp_path / "saved.json"
    a, b, c = tpl.columns[1], tpl.columns[2], tpl.columns[3]
    answers = {a.index: Answer(CONST, value="X"), b.index: Answer(SKIP),
               c.index: Answer(LOOKUP, by="Color", table={"White Gold": "White"})}
    assert save_answers(tpl, answers, f) == 2                  # the skipped column is not saved
    back = load_answers(tpl, f)
    assert back[a.index].value == "X" and back[c.index].table == {"White Gold": "White"} and b.index not in back


def test_saved_answers_survive_a_new_download_of_the_template(tpl, tmp_path):
    f = tmp_path / "saved.json"
    col = next(c for c in tpl.columns if c.label == "Dangerous Goods Regulations")
    save_answers(tpl, {col.index: Answer(CONST, value="Not Applicable")}, f)
    again = read_template(TEMPLATE.read_bytes())                # same attribute keys, fresh objects
    assert load_answers(again, f)[col.index].value == "Not Applicable"


def test_missing_or_broken_store_is_just_empty(tpl, tmp_path):
    assert load_answers(tpl, tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    assert load_answers(tpl, bad) == {}


class FakeClient:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])


def test_proposals_keep_only_valid_values(tpl):
    drop = next(c for c in tpl.columns if c.has_dropdown and c.must_address)
    free = next(c for c in tpl.columns if c.must_address and not c.has_dropdown)
    reply = ('{"answers": {"%d": {"value": "%s", "confidence": 0.9}, "%d": {"value": "nonsense", "confidence": 0.9},'
             ' "%d": {"value": "Hello", "confidence": 0.7}, "999999": {"value": "x", "confidence": 1}}}'
             % (drop.index, drop.allowed[0].lower(), drop.index + 0, free.index))
    # the dropdown index appears twice in the JSON; the later (invalid) entry wins, so it is dropped
    got = ai.propose_answers(FakeClient(reply), [drop, free], {"Color": "White Gold"})
    assert drop.index not in got
    assert got[free.index] == ("Hello", 0.7) and 999999 not in got
    ok = ai.propose_answers(FakeClient('{"answers": {"%d": {"value": "%s", "confidence": 0.9}}}'
                                       % (drop.index, drop.allowed[0].lower())), [drop], {})
    assert ok[drop.index] == (drop.allowed[0], 0.9)           # matched ignoring case, normalised to the allowed spelling


def test_proposals_fail_plainly(tpl):
    with pytest.raises(ai.AIUnavailable, match="API key"):
        ai.propose_answers(None, tpl.columns[:2], {})
    with pytest.raises(ai.AIUnavailable, match="by hand"):
        ai.propose_answers(FakeClient("sorry"), tpl.columns[:2], {})


def test_proposals_are_sent_in_batches(tpl):
    client = FakeClient('{"answers": {}}')
    ai.propose_answers(client, tpl.columns[:70], {}, batch=30)
    assert len(client.prompts) == 3
