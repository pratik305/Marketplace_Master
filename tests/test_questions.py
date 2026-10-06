"""Slice 4: the queue, answer checking, and how answers fill rows."""
from pathlib import Path

import pytest

from src.mapper import name_match
from src.master_reader import read_master
from src.questions import (CONST, LOOKUP, SKIP, Answer, build_queue, check_value, distinct_values,
                           resolve_all)
from src.result import build_rows
from src.template_reader import read_template

SAMPLE = Path(__file__).resolve().parent.parent / "sample"
TEMPLATE = SAMPLE / "RING (6).xlsm"
MASTER = SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"
pytestmark = pytest.mark.skipif(not (TEMPLATE.exists() and MASTER.exists()), reason="sample/ files not present")


@pytest.fixture(scope="module")
def ctx():
    info = read_template(TEMPLATE.read_bytes())
    master = read_master(MASTER.read_bytes())
    mapping = name_match(info.columns, master.columns)
    mapping[next(c.index for c in info.columns if c.label == "SKU")] = "Sku Code"
    return info, master, mapping


def col(info, label, nth=0):
    return [c for c in info.columns if c.label == label][nth]


def test_queue_has_needed_unmapped_columns_only(ctx):
    info, master, mapping = ctx
    queue = build_queue(info, mapping, master)
    ids = {c.index for c in queue}
    assert queue and all(c.must_address for c in queue)
    assert not ids & set(mapping)                   # mapped from the master -> not asked
    assert not ids & set(info.defaults)             # pre-filled by the template -> not asked
    assert col(info, "Item Name").index not in ids or "Item Name" not in master.columns
    required_positions = [i for i, c in enumerate(queue) if c.required]
    assert required_positions == sorted(required_positions)
    assert required_positions == list(range(len(required_positions)))     # required come first


def test_optional_columns_only_on_request(ctx):
    info, master, mapping = ctx
    assert len(build_queue(info, mapping, master, True)) > len(build_queue(info, mapping, master))


def test_dropdown_rejects_value_outside_list(ctx):
    info, *_ = ctx
    cond = col(info, "Item Condition") if any(c.label == "Item Condition" for c in info.columns) else col(info, "Stone Shape")
    assert cond.allowed
    ok, norm, _ = check_value(cond, cond.allowed[0].lower())
    assert ok and norm == cond.allowed[0]            # case-insensitive, normalised to the allowed spelling
    ok, _, reason = check_value(cond, "definitely not a value")
    assert not ok and "not one of the allowed" in reason
    assert not check_value(cond, "  ")[0]


def test_answers_fill_the_right_rows(ctx):
    info, master, mapping = ctx
    queue = build_queue(info, mapping, master)
    free = next(c for c in queue if not c.has_dropdown)
    drop = next(c for c in queue if c.has_dropdown)
    dep = next(c for c in queue if c.has_dropdown and c.index != drop.index)
    colors = distinct_values(master, "Color")
    assert 1 <= len(colors) <= 40
    answers = {
        free.index: Answer(CONST, value="Same text"),
        drop.index: Answer(CONST, value=drop.allowed[0]),
        dep.index: Answer(LOOKUP, by="Color", table={colors[0]: dep.allowed[0]}),
        queue[-1].index: Answer(SKIP),
    }
    rows = build_rows(info, master, mapping, resolve_all(answers, master))
    assert len(rows) == len(master)
    assert all(r[free.index] == "Same text" and r[drop.index] == drop.allowed[0] for r in rows)
    first = [i for i in range(len(master)) if str(master.iloc[i]["Color"]).strip() == colors[0]]
    other = [i for i in range(len(master)) if str(master.iloc[i]["Color"]).strip() != colors[0]]
    assert first and all(rows[i][dep.index] == dep.allowed[0] for i in first)
    assert all(dep.index not in rows[i] for i in other)
    assert queue[-1].index not in rows[0] or queue[-1].index in info.defaults
