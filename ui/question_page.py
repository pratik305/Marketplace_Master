"""Question step: one template column at a time.

Buttons use callbacks: Streamlit runs a callback first, then redraws the page, so the screen
never needs a manual rerun.
"""
import streamlit as st

from src.ai import AIUnavailable, check_answers, get_client
from src.questions import (CONST, LOOKUP, MAX_LOOKUP_VALUES, SKIP, Answer, build_queue, check_value,
                           distinct_values)

SAME, DEPENDS = "Same for all rows", "Depends on a master column"


def _input(col, label, key, current=""):
    """A dropdown for dropdown columns, free text otherwise."""
    if col.has_dropdown:
        options = [""] + col.allowed
        return st.selectbox(label, options, index=options.index(current) if current in options else 0, key=key)
    return st.text_input(label, value=current or "", key=key)


# ---- callbacks (run before the page is redrawn) ----

def _advance(delta=1):
    st.session_state["q_index"] = max(0, st.session_state["q_index"] + delta)


def _skip(col):
    st.session_state["answers"][col.index] = Answer(SKIP)
    st.session_state["q_error"].pop(col.index, None)
    _advance()


def _back():
    _advance(-1)


def _restart():
    st.session_state["q_index"] = 0


def _ai_review(col, values):
    """Ask Claude about free-text answers. Returns a message when it doubts them, else ''.

    The user can press Continue again with the same values to use them anyway. If Claude can't be
    reached the answers are accepted: the template rules are the only hard check.
    """
    ss = st.session_state
    ss.setdefault("q_warned", {})
    sig = tuple(values)
    if col.has_dropdown or not values or ss["q_warned"].get(col.index) == sig:
        return ""
    client = get_client()
    if client is None:
        return ""
    try:
        bad = [(v, why) for v, ok, why in check_answers(client, col, values) if not ok]
    except AIUnavailable:
        return ""
    if not bad:
        return ""
    ss["q_warned"][col.index] = sig
    detail = "; ".join(f"'{v}': {why}" if why else f"'{v}'" for v, why in bad)
    return f"Claude thinks this may be wrong ({detail}). Press Continue again to use it anyway."


def _submit(col, master):
    """Check what was typed or chosen for this column; store it and move on, or show why not."""
    ss, errors = st.session_state, st.session_state["q_error"]
    errors.pop(col.index, None)
    if ss.get(f"mode_{col.index}", SAME) == SAME:
        ok, norm, why = check_value(col, ss.get(f"val_{col.index}", ""))
        if not ok:
            errors[col.index] = why
            return
        review = _ai_review(col, [norm])
        if review:
            errors[col.index] = review
            return
        ss["answers"][col.index] = Answer(CONST, value=norm)
    else:
        by = ss.get(f"by_{col.index}", "")
        if not by:
            errors[col.index] = "Choose the master column this answer depends on."
            return
        table = {}
        for v in distinct_values(master, by):
            raw = ss.get(f"lk_{col.index}_{v}", "")
            if raw:
                ok, norm, why = check_value(col, raw)
                if not ok:
                    errors[col.index] = why
                    return
                table[v] = norm
        if not table:
            errors[col.index] = "Give a value for at least one entry, or skip this column."
            return
        review = _ai_review(col, list(table.values()))
        if review:
            errors[col.index] = review
            return
        ss["answers"][col.index] = Answer(LOOKUP, by=by, table=table)
    _advance()


def render(tpl, master, mapping):
    ss = st.session_state
    ss.setdefault("answers", {})
    ss.setdefault("q_index", 0)
    ss.setdefault("q_error", {})

    st.subheader("Questions")
    st.caption("These columns are needed by the template but are not in your master or pre-filled. "
               "Answer once for all rows, or say which master column the answer depends on.")
    include_optional = st.checkbox("Also ask about optional columns", key="include_optional")
    queue = build_queue(tpl, mapping, master, include_optional, ss.setdefault("q_extra", set()))
    if not queue:
        st.success("Nothing to ask: every needed column is filled by the master or the template.")
        return
    total = len(queue)
    pos = min(ss["q_index"], total)
    st.progress(pos / total, text=f"{min(pos + 1, total)} of {total} columns")

    answers = ss["answers"]
    if pos >= total:
        skipped = [c.label for c in queue if answers.get(c.index) and answers[c.index].mode == SKIP]
        unanswered = [c.label for c in queue if c.index not in answers]
        st.success(f"All {total} questions covered: {total - len(skipped) - len(unanswered)} answered, "
                   f"{len(skipped)} skipped.")
        st.button("Go back to the first question", on_click=_restart)
        return

    col = queue[pos]
    prev = answers.get(col.index)
    st.markdown(f"**{col.label}**  \n{col.group} · " + ("**Required**" if col.required else col.requirement))
    if col.description:
        st.caption(col.description)
    if col.example:
        st.caption(f"Example: {col.example}")

    mode = st.radio("How do you want to answer?", [SAME, DEPENDS], horizontal=True,
                    index=1 if prev and prev.mode == LOOKUP else 0, key=f"mode_{col.index}")
    if mode == SAME:
        _input(col, "Value for every row", f"val_{col.index}",
               prev.value if prev and prev.mode == CONST else "")
    else:
        by = st.selectbox("Which master column does it depend on?", [""] + [str(c) for c in master.columns],
                          key=f"by_{col.index}")
        if by:
            values = distinct_values(master, by)
            if len(values) > MAX_LOOKUP_VALUES:
                st.warning(f"'{by}' has {len(values)} different values. Pick a column with at most "
                           f"{MAX_LOOKUP_VALUES}, or use 'Same for all rows'.")
            else:
                for v in values:
                    old = prev.table.get(v, "") if prev and prev.mode == LOOKUP and prev.by == by else ""
                    _input(col, f"When {by} = {v}", f"lk_{col.index}_{v}", old)

    if col.index in ss["q_error"]:
        st.error(ss["q_error"][col.index])
    a, b, c = st.columns(3)
    a.button("Continue", type="primary", key=f"cont_{col.index}", on_click=_submit, args=(col, master))
    b.button("Skip this column", key=f"skip_{col.index}", on_click=_skip, args=(col,))
    c.button("Back", key=f"back_{col.index}", on_click=_back, disabled=pos == 0)
