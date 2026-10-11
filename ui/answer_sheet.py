"""Answer sheet: every remaining column on one screen, pre-filled, answered with one button.

Replaces answering question after question. Each row is pre-filled from, in order: your last answer,
saved answers from an earlier run, a Claude proposal, the template's own first-row suggestion. Nothing is
applied until you press "Apply all answers".
"""
import streamlit as st

from src.ai import AIUnavailable, get_client, propose_answers
from src.answer_store import load_answers, save_answers, store_path
from src.questions import (CONST, LOOKUP, MAX_LOOKUP_VALUES, SKIP, Answer, build_queue, check_value,
                           distinct_values)
from src.result import clean
from ui import style

MIN_AI_CONFIDENCE = 0.8       # below this a Claude proposal is only shown as a hint, never pre-filled
                              # (checked against a hand-filled file: all 0.8+ proposals were right, 0.75 and below were not)


def _suggestion(tpl, col):
    raw = tpl.defaults.get(col.index)
    if raw is None:
        return ""
    text = str(int(raw)) if isinstance(raw, float) and raw.is_integer() else str(raw).strip()
    ok, norm, _ = check_value(col, text)
    return norm if ok else ""


def _prefill(tpl, col, answers, saved, proposals):
    """Initial value for a row and where it came from."""
    a = answers.get(col.index)
    if a and a.mode == CONST:
        return a.value, "answered"
    s = saved.get(col.index)
    if s and s.mode == CONST:
        return s.value, "saved"
    p = proposals.get(col.index)
    if p and p[1] >= MIN_AI_CONFIDENCE:
        return p[0], f"Claude {p[1]:.2f}"
    sug = _suggestion(tpl, col)
    if sug:
        return sug, "template"
    if p:                                             # a doubtful proposal is a hint, not a value
        return "", f"Claude suggests '{p[0]}' ({p[1]:.2f})"
    return "", ""


def _sample_row(master):
    for i in range(len(master)):
        if str(master.iloc[i].get("CATEGORY", "")).upper() != "PARENT":
            return {str(k): clean(v) for k, v in master.iloc[i].items()}
    return {str(k): clean(v) for k, v in master.iloc[0].items()}


def _propose(queue, master):
    """Ask Claude for proposals for the rows still blank; remember them for the sheet."""
    ss = st.session_state
    try:
        with st.spinner("Claude is proposing answers..."):
            found = propose_answers(get_client(), queue, _sample_row(master))
    except AIUnavailable as err:
        st.warning(str(err))
        return
    ss["ai_proposals"] = found
    filled = 0
    for c in queue:
        key = f"sheet_{c.index}"
        p = found.get(c.index)
        if p and p[1] >= MIN_AI_CONFIDENCE and not ss.get(key):
            ss[key] = p[0]
            filled += 1
    st.success(f"Claude proposed {len(found)} answers; {filled} pre-filled into blank rows. Check them, then apply.")


def _apply(queue, tpl):
    """Validate every row, store the answers, and remember them if asked."""
    ss = st.session_state
    errors, answers = {}, ss["answers"]
    for c in queue:
        if answers.get(c.index) and answers[c.index].mode == LOOKUP:
            continue                                   # a per-product answer set in the box below stays
        raw = ss.get(f"sheet_{c.index}", "")
        if not raw:
            answers[c.index] = Answer(SKIP)
            continue
        ok, norm, why = check_value(c, raw)
        if ok:
            answers[c.index] = Answer(CONST, value=norm)
        else:
            errors[c.index] = why
            answers.pop(c.index, None)
    ss["sheet_errors"] = errors
    if ss.get("sheet_remember", True):
        ss["sheet_saved_count"] = save_answers(tpl, answers)


def _lookup_box(queue, master, tpl):
    """Answers that differ per product: pick the master column they depend on, fill one value per entry."""
    ss = st.session_state
    with st.expander("Answers that differ per product (depend on a master column)"):
        labels = {f"{c.label} ({c.letter})": c for c in queue}
        pick = st.selectbox("Template column", [""] + list(labels), key="lk_pick")
        by = st.selectbox("Depends on master column", [""] + [str(c) for c in master.columns], key="lk_by")
        if not (pick and by):
            st.caption("Example: Material depends on Color, so White Gold -> one value, Yellow Gold -> another.")
            return
        col, values = labels[pick], distinct_values(master, by)
        if len(values) > MAX_LOOKUP_VALUES:
            style.note(f"'{by}' has {len(values)} different values; pick a column with at most {MAX_LOOKUP_VALUES}.",
                       "amber")
            return
        prev = ss["answers"].get(col.index)
        old = prev.table if prev and prev.mode == LOOKUP and prev.by == by else {}
        table = [{"Master value": v, "Answer": old.get(v, "")} for v in values]
        config = {"Answer": st.column_config.SelectboxColumn("Answer", options=[""] + col.allowed)} \
            if col.has_dropdown else {}
        edited = st.data_editor(table, column_config=config, disabled=["Master value"], hide_index=True,
                                use_container_width=True, key=f"lk_table_{col.index}_{by}")
        if st.button("Save this per-product answer", key="lk_save"):
            cleaned, bad = {}, ""
            for row in edited:
                if row["Answer"]:
                    ok, norm, why = check_value(col, row["Answer"])
                    if ok:
                        cleaned[row["Master value"]] = norm
                    else:
                        bad = why
            if bad:
                st.error(bad)
            elif not cleaned:
                st.error("Fill at least one answer.")
            else:
                ss["answers"][col.index] = Answer(LOOKUP, by=by, table=cleaned)
                if ss.get("sheet_remember", True):
                    save_answers(tpl, ss["answers"])
                st.success(f"Saved: {col.label} depends on {by}.")


def render(tpl, master, mapping):
    ss = st.session_state
    ss.setdefault("answers", {})
    ss.setdefault("sheet_errors", {})
    ss.setdefault("ai_proposals", {})
    if "saved_answers" not in ss:
        ss["saved_answers"] = load_answers(tpl)
    style.inject()

    st.subheader("Answer sheet")
    queue = build_queue(tpl, mapping, master, ss.get("include_optional", False), ss.setdefault("q_extra", set()),
                        ss.get("rule_covered", ()))
    if not queue:
        style.note("Nothing to answer: every needed column is filled by the master or the rules.", "green")
        return
    answers, saved, proposals = ss["answers"], ss["saved_answers"], ss["ai_proposals"]
    done = sum(1 for c in queue if answers.get(c.index) and answers[c.index].mode != SKIP)
    st.markdown(style.pill(f"{done} answered", "green") + style.pill(f"{len(queue) - done} left", "blue")
                + style.pill(f"{len(saved)} saved from last time", "gray"), unsafe_allow_html=True)
    st.caption("Everything is pre-filled where possible. Change what is wrong, leave a row blank to skip it, then "
               "press Apply all answers. Nothing is used until you apply.")

    a, b = st.columns([1, 2])
    if a.button("Let Claude propose answers", key="ai_btn"):
        _propose(queue, master)
    b.checkbox("Also include optional columns", key="include_optional")

    groups = []                                   # tabs follow the template's own section order
    for col in sorted(queue, key=lambda c: c.index):
        if col.group not in groups:
            groups.append(col.group)
    with st.form("answer_sheet"):
        short = lambda g: (g if len(g) <= 24 else g[:23].rstrip() + "…") or "Other"
        tabs = st.tabs([f"{short(g)} ({sum(1 for c in queue if c.group == g)})" for g in groups])
        for tab, group in zip(tabs, groups):
            with tab:
                for col in [c for c in queue if c.group == group]:
                    left, mid, right = st.columns([3, 5, 2])
                    tint = "red" if col.required else "amber"
                    left.markdown(f"**{col.label}**  \n" + style.pill("Required" if col.required else "Conditional",
                                                                       tint), unsafe_allow_html=True)
                    key = f"sheet_{col.index}"
                    cur = answers.get(col.index)
                    if cur and cur.mode == LOOKUP:
                        mid.markdown(f"Depends on **{cur.by}** ({len(cur.table)} values) — change it in the box below")
                        continue
                    value, source = _prefill(tpl, col, answers, saved, proposals)
                    if key not in ss:
                        ss[key] = value
                    if col.has_dropdown:
                        options = [""] + col.allowed
                        if ss[key] not in options:
                            ss[key] = ""
                        mid.selectbox(col.label, options, key=key, label_visibility="collapsed")
                    else:
                        mid.text_input(col.label, key=key, label_visibility="collapsed",
                                       placeholder=col.example[:40] if col.example else "")
                    err = ss["sheet_errors"].get(col.index)
                    right.markdown(f":red[{err}]" if err else (f"*{source}*" if source else ""))
        st.checkbox("Remember these answers for next time (saved on this computer only)", value=True,
                    key="sheet_remember")
        st.form_submit_button("Apply all answers", type="primary", on_click=_apply, args=(queue, tpl),
                              use_container_width=True)
    if ss["sheet_errors"]:
        style.note(f"{len(ss['sheet_errors'])} row(s) were not accepted; see the red text.", "red")
    elif ss.get("sheet_saved_count"):
        style.note(f"Applied. {ss['sheet_saved_count']} answers saved for next time ({store_path().name}).", "green")
    _lookup_box(queue, master, tpl)
