"""The question flow: which columns need asking, and how an answer turns into cell values."""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.result import clean

MAX_LOOKUP_VALUES = 40      # a "depends on a master column" answer needs one value per distinct master value

CONST, LOOKUP, SKIP = "const", "lookup", "skip"


@dataclass
class Answer:
    mode: str                                   # CONST, LOOKUP or SKIP
    value: Any = None                           # CONST: the value for every row
    by: Optional[str] = None                    # LOOKUP: the master column the value depends on
    table: dict = field(default_factory=dict)   # LOOKUP: master value -> answer


def key_of(value) -> str:
    """Normalise a master cell so equal-looking values share one lookup key."""
    v = clean(value)
    return "" if v is None else str(v).strip()


def build_queue(info, mapping: dict, master, include_optional: bool = False) -> list:
    """Template columns to ask about: needed, not pre-filled, and not already supplied by the master.

    Required first, then conditionally required, then (on request) the rest, each in template order.
    A mapped column whose master values are all empty still needs asking.
    """
    def supplied(col):
        if col.index in info.defaults:
            return True
        m = mapping.get(col.index)
        return bool(m) and master[m].map(lambda v: key_of(v) != "").any()

    wanted = info.columns if include_optional else info.must_address()
    rank = {"Required": 0, "Conditionally Required": 1}
    queue = [c for c in wanted if not supplied(c)]
    return sorted(queue, key=lambda c: (rank.get(c.requirement, 2), c.index))


def check_value(col, value):
    """Check one value for a column. Returns (ok, normalised value, reason).

    Dropdown columns accept only the template's allowed values (matched ignoring case).
    """
    text = "" if value is None else str(value).strip()
    if not text:
        return False, None, "Enter a value, or skip this column."
    if col.allowed:
        by_lower = {a.lower(): a for a in col.allowed}
        if text.lower() in by_lower:
            return True, by_lower[text.lower()], ""
        return False, None, f"'{text}' is not one of the allowed values for {col.label}."
    return True, text, ""


def distinct_values(master, column: str) -> list:
    """Distinct non-empty values of a master column, in order of appearance."""
    seen, out = set(), []
    for v in master[column]:
        k = key_of(v)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def resolve(answer: Answer, master) -> Optional[Callable]:
    """Turn an Answer into a function row number -> value (None for a skipped column)."""
    if answer.mode == CONST:
        return lambda i, v=answer.value: v
    if answer.mode == LOOKUP:
        by, table = answer.by, answer.table
        return lambda i: table.get(key_of(master.iloc[i][by]))
    return None


def resolve_all(answers: dict, master) -> dict:
    out = {}
    for idx, a in answers.items():
        fn = resolve(a, master)
        if fn is not None:
            out[idx] = fn
    return out
