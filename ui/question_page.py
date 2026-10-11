"""Question step: one template column at a time.

Buttons use callbacks: Streamlit runs a callback first, then redraws the page, so the screen
never needs a manual rerun.
"""
import streamlit as st

from src.ai import AIUnavailable, check_answers, get_client
from src.questions import (CONST, LOOKUP, MAX_LOOKUP_VALUES, SKIP, Answer, build_queue, check_value,
                           distinct_values, gap_count)
from ui import style

SAME, DEPENDS = "Same for all rows", "Depends on a master column"
CHOICE_BUTTONS_MAX = 8        # dropdown columns with this many options or fewer show as choice buttons


def _input(col, label, key, current=""):
    """Choice buttons for short dropdowns, a searchable dropdown for long ones, free text otherwise."""
    if col.has_dropdown and len(col.allowed) <= CHOICE_BUTTONS_MAX:
        return st.radio(label, col.allowed, index=col.allowed.index(current) if current in col.allowed else None,
                        horizontal=True, key=key)
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


def _skip_conditionals(queue):
    """Skip every conditionally required column not answered yet, then jump to the first one left."""
    ss = st.session_state
    for c in queue:
        if not c.required and c.index not in ss["answers"]:
            ss["answers"][c.index] = Answer(SKIP)
    left = [i for i, c in enumerate(queue) if c.index not in ss["answers"]]
    ss["q_index"] = left[0] if left else len(queue)


def _use_suggestion(col, master, value):
    """One-click accept of the template's suggested value for every row."""
    st.session_state[f"mode_{col.index}"] = SAME
    st.session_state[f"val_{col.index}"] = value
    _submit(col, master)


def _suggestion(tpl, col):
    """The value left in the template's first data row, if it is usable for this column."""
    raw = tpl.defaults.get(col.index)
    if raw is None:
        return ""
    text = str(int(raw)) if isinstance(raw, float) and raw.is_integer() else str(raw).strip()
    ok, norm, _ = check_value(col, text)
    return norm if ok else ""


def _status_chips(queue, answers):
    """Soft-coloured counts: answered, skipped, still to do."""
    done = sum(1 for c in queue if answers.get(c.index) and answers[c.index].mode != SKIP)
    skipped = sum(1 for c in queue if answers.get(c.index) and answers[c.index].mode == SKIP)
    todo = len(queue) - done - skipped
    st.markdown(style.pill(f"{done} answered", "green") + style.pill(f"{skipped} skipped", "amber")
                + style.pill(f"{todo} to do", "blue"), unsafe_allow_html=True)


def render(tpl, master, mapping):
    ss = st.session_state
    ss.setdefault("answers", {})
    ss.setdefault("q_index", 0)
    ss.setdefault("q_error", {})
    style.inject()

    st.subheader("Questions")
    st.caption("These columns are needed by the template but are not in your master. "
               "Answer once for all rows, or say which master column the answer depends on.")
    include_optional = st.checkbox("Also ask about optional columns", key="include_optional")
    queue = build_queue(tpl, mapping, master, include_optional, ss.setdefault("q_extra", set()),
                        ss.get("rule_covered", ()))
    if not queue:
        style.note("Nothing to ask: every needed column is filled by the master.", "green")
        return
    total = len(queue)
    pos = min(ss["q_index"], total)
    answers = ss["answers"]
    st.progress(pos / total, text=f"Question {min(pos + 1, total)} of {total}")
    _status_chips(queue, answers)
    open_conditionals = [c for c in queue if not c.required and c.index not in answers]
    if open_conditionals:
        st.button(f"Skip all {len(open_conditionals)} conditionally required columns not answered yet",
                  key="skip_conditionals", on_click=_skip_conditionals, args=(queue,),
                  help="Many of these do not apply to your product. They stay in the validation list as 'check these'.")

    if pos >= total:
        style.note(f"All {total} questions covered. Scroll down to check the validation summary "
                   "and download the file.", "green")
        st.button("Go back to the first question", on_click=_restart)
        return

    col = queue[pos]
    prev = answers.get(col.index)
    style.card(col.label, col.requirement, col.group, col.description, col.example)
    gaps = gap_count(mapping, master, col)
    if gaps:
        style.note(f"Your master fills this column for most rows but leaves {gaps} empty. "
                   "Your answer fills only those empty rows.", "blue")

    with st.container(border=True):
        mode = st.radio("How do you want to answer?", [SAME, DEPENDS], horizontal=True,
                        index=1 if prev and prev.mode == LOOKUP else 0, key=f"mode_{col.index}")
        if mode == SAME:
            suggestion = _suggestion(tpl, col)
            _input(col, "Value for every row", f"val_{col.index}",
                   prev.value if prev and prev.mode == CONST else suggestion)
            if suggestion and not prev:
                style.note(f"Suggested from the template's first row: {suggestion}", "green")
                st.button("Use this suggestion and continue", key=f"sug_{col.index}", on_click=_use_suggestion,
                          args=(col, master, suggestion))
        else:
            by = st.selectbox("Which master column does it depend on?", [""] + [str(c) for c in master.columns],
                              key=f"by_{col.index}")
            if by:
                values = distinct_values(master, by)
                if len(values) > MAX_LOOKUP_VALUES:
                    style.note(f"'{by}' has {len(values)} different values. Pick a column with at most "
                               f"{MAX_LOOKUP_VALUES}, or use 'Same for all rows'.", "amber")
                else:
                    for v in values:
                        old = prev.table.get(v, "") if prev and prev.mode == LOOKUP and prev.by == by else ""
                        _input(col, f"When {by} = {v}", f"lk_{col.index}_{v}", old)

    if col.index in ss["q_error"]:
        style.note(ss["q_error"][col.index], "red")
    a, b, c = st.columns([2, 1, 1])
    a.button("Continue", type="primary", key=f"cont_{col.index}", on_click=_submit, args=(col, master),
             use_container_width=True)
    b.button("Skip this column", key=f"skip_{col.index}", on_click=_skip, args=(col,), use_container_width=True)
    c.button("Back", key=f"back_{col.index}", on_click=_back, disabled=pos == 0, use_container_width=True)
