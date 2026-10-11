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


class _ApiError(Exception):
    """Stands in for an Anthropic SDK error: they carry a status code and a body."""
    def __init__(self, status, body, name="BadRequestError"):
        super().__init__(str(body))
        self.status_code, self.body = status, body
        self.__class__ = type(name, (_ApiError,), {})


def test_api_failures_are_explained_in_plain_words():
    credit = _ApiError(400, {"type": "error", "error": {"type": "invalid_request_error",
                      "message": "Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing"}})
    msg = ai.plain_error(credit)
    assert "credit balance is too low" in msg and "Plans & Billing" in msg and "BadRequestError" not in msg
    assert "key was rejected" in ai.plain_error(_ApiError(401, "invalid x-api-key", "AuthenticationError"))
    assert "rate limit" in ai.plain_error(_ApiError(429, "slow down", "RateLimitError")).lower()
    assert "busy or down" in ai.plain_error(_ApiError(529, "overloaded", "InternalServerError"))
    assert "internet connection" in ai.plain_error(_ApiError(None, "x", "APIConnectionError"))
    assert "rejected the request: model not found" in ai.plain_error(_ApiError(400, "model not found"))
    assert ai.plain_error(ValueError("x"), "AI mapping") == "The AI mapping could not be completed (ValueError)."


def test_a_low_credit_balance_reaches_the_user_with_advice(monkeypatch):
    from types import SimpleNamespace
    credit = _ApiError(400, "Your credit balance is too low to access the Anthropic API.")

    def boom(**kw):
        raise credit
    client = SimpleNamespace(messages=SimpleNamespace(create=boom))
    from src.template_reader import read_template
    from pathlib import Path
    tpl_path = Path(__file__).resolve().parent.parent / "sample" / "RING (6).xlsm"
    if not tpl_path.exists():
        pytest.skip("sample/ files not present")
    info = read_template(tpl_path.read_bytes())
    import pandas as pd
    with pytest.raises(ai.AIUnavailable, match="credit balance is too low.*by hand"):
        ai.propose_mapping(client, info.columns, pd.DataFrame({"Sku Code": ["a"]}), {})
    with pytest.raises(ai.AIUnavailable, match="credit balance is too low"):
        ai.propose_answers(client, info.columns[:3], {})
