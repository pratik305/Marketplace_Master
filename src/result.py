"""Combine template defaults, master values and the user's answers into the rows to write."""
import math


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


def build_rows(info, master, mapping: dict, answers: dict | None = None) -> list:
    """One {column index: value} per master row.

    Order of precedence, lowest first: template defaults, master values, answers.
    `answers` maps a template column index to a function row_number -> value (or a constant).
    """
    answers = answers or {}
    rows = []
    for i in range(len(master)):
        row = dict(info.defaults)
        for col_idx, master_col in mapping.items():
            v = clean(master.iloc[i][master_col])
            if v is not None:
                row[col_idx] = v
        for col_idx, ans in answers.items():
            v = ans(i) if callable(ans) else ans
            if v not in (None, ""):
                row[col_idx] = v
        rows.append(row)
    return rows
