"""Validation step: what is still missing or doubtful before you download."""
import streamlit as st

from src.questions import build_queue
from src.validator import CONDITIONAL_MISSING, INVALID, REQUIRED_MISSING, blocking, validate


def _fix(col, tpl, master, mapping):
    """Jump to this column's question (adding it to the queue if it was not already there)."""
    ss = st.session_state
    ss.setdefault("q_extra", set()).add(col.index)
    queue = build_queue(tpl, mapping, master, ss.get("include_optional", False), ss["q_extra"],
                        ss.get("rule_covered", ()))
    ss["q_index"] = next(i for i, c in enumerate(queue) if c.index == col.index)
    ss["answers"].pop(col.index, None)
    ss.pop(f"sheet_{col.index}", None)         # let the sheet show a fresh row for this column
    ss["step"] = 3                             # and go back to the answers


def _who(tpl, built_rows, row_number):
    """The real product on a row: 'SKU - title', so a row number means something."""
    from src.rules import find_column
    i = row_number - tpl.data_row
    if not (0 <= i < len(built_rows)):
        return ""
    sku, name = find_column(tpl, "SKU"), find_column(tpl, "Item Name")
    parts = [str(built_rows[i].get(c.index, "")).strip() for c in (sku, name) if c]
    parts = [p[:46] for p in parts if p]
    return " - ".join(parts)


def _rows_text(rows, tpl=None, built_rows=None, n=4):
    shown = ", ".join(str(r) for r in rows[:n])
    first = _who(tpl, built_rows, rows[0]) if tpl is not None and built_rows else ""
    text = f"{len(rows)} rows (row {shown}" + ("" if len(rows) <= n else ", ...") + ")"
    return text + (f". First: {first}" if first else "")


def render(tpl, master, mapping, rows):
    issues = validate(tpl, rows, st.session_state.get("rule_parent_blank", ()))
    must = blocking(issues)
    check = [i for i in issues if i not in must]

    a, b, c = st.columns(3)
    a.metric("Rows to write", len(rows))
    b.metric("Must fix", len(must))
    c.metric("Check these", len(check))
    if not must:
        st.success("Every required column is filled in every row."
                   + (" A few items below are worth a look." if check else " No remaining problems."))
    else:
        st.error("Some required columns are still empty. Press Fix this on a row to go back and answer it.")

    for group, title, expanded in ((must, "Must fix", True), (check, "Check these", False)):
        if not group:
            continue
        with st.expander(f"{title} ({len(group)})", expanded=expanded):
            for n, issue in enumerate(group[:80]):
                left, right = st.columns([5, 1])
                left.markdown(f"**{issue.col.label}** ({issue.col.letter}) — {issue.message}  \n"
                              f"{_rows_text(issue.rows, tpl, rows)}")
                right.button("Fix this", key=f"fix_{issue.severity}_{issue.col.index}_{n}",
                             on_click=_fix, args=(issue.col, tpl, master, mapping))
            if len(group) > 80:
                st.caption(f"Showing the first 80 of {len(group)}.")
    return issues
