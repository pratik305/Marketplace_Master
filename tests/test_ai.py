"""Slice 3: mapping suggestions are parsed safely, and the no-key fallback is plain."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import ai
from src.mapper import name_match
from src.master_reader import read_master
from src.template_reader import read_template

SAMPLE = Path(__file__).resolve().parent.parent / "sample"
TEMPLATE = SAMPLE / "RING (6).xlsm"
MASTER = SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"
pytestmark = pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")


class FakeClient:
    """Stands in for the Claude API: returns a canned reply and records the prompt."""
    def __init__(self, reply):
        self.reply, self.prompt = reply, None
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.prompt = kw["messages"][0]["content"]
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply)])


@pytest.fixture(scope="module")
def files():
    info = read_template(TEMPLATE.read_bytes())
    master = read_master(MASTER.read_bytes())
    return info, master


def idx(info, label):
    return next(c.index for c in info.columns if c.label == label)


def test_no_key_gives_plain_message(files):
    info, master = files
    with pytest.raises(ai.AIUnavailable, match="ANTHROPIC_API_KEY"):
        ai.propose_mapping(None, info.columns, master, {})


def test_valid_pairs_kept_invalid_dropped(files):
    info, master = files
    sku, item = idx(info, "SKU"), idx(info, "Item Name")
    reply = ('```json\n{"mapping": {"%d": {"master": "Sku Code", "confidence": 0.95},'
             ' "%d": {"master": "NO SUCH COLUMN", "confidence": 0.9},'
             ' "99999": {"master": "Sku Name", "confidence": 0.9}}}\n```' % (sku, item))
    client = FakeClient(reply)
    found = ai.propose_mapping(client, info.columns, master, name_match(info.columns, master.columns))
    assert found == {sku: ("Sku Code", 0.95)}
    assert "Sku Code" in client.prompt and "Brand Name" in client.prompt


def test_garbage_reply_is_a_plain_error(files):
    info, master = files
    with pytest.raises(ai.AIUnavailable, match="map the columns by hand"):
        ai.propose_mapping(FakeClient("sorry, I can't"), info.columns, master, {})


def test_low_confidence_pairs_are_not_applied_automatically():
    from ui.mapping_page import MIN_CONFIDENCE
    assert 0.3 < MIN_CONFIDENCE <= 0.6        # live run showed junk pairs at 0.2-0.3 and sound ones from 0.5
