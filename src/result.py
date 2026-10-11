"""Combine master values and the user's answers into the rows to write."""
import math
from typing import Optional


def clean(value):
    """Turn a master cell into something writable, or None when it is empty."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):          # numpy scalar -> plain Python
        value = value.item()
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def build_rows(info, master, mapping: dict, answers: Optional[dict] = None, rule_values: Optional[dict] = None) -> list:
    """One {column index: value} per master row.

    Rule values (built-in listing rules) replace the raw master value for their columns. An answer for a mapped
    or rule-filled column fills only the rows still empty. Values left in the template's first data
    row are never copied: they are leftovers from earlier use, so they are only offered as suggestions.
    `answers` maps a template column index to a function row_number -> value (or a constant).
    """
    answers = answers or {}
    rule_values = rule_values or {}
    rows = []
    for i in range(len(master)):
        row = {}
        for col_idx, master_col in mapping.items():
            v = clean(master.iloc[i][master_col])
            if v is not None:
                row[col_idx] = v
        for col_idx, vals in rule_values.items():
            if vals[i] is not None:
                row[col_idx] = vals[i]
        for col_idx, ans in answers.items():
            if (col_idx in mapping or col_idx in rule_values) and col_idx in row:
                continue                  # the master or a rule has a value here: an answer only fills gaps
            v = ans(i) if callable(ans) else ans
            if v not in (None, ""):
                row[col_idx] = v
        rows.append(row)
    return rows
