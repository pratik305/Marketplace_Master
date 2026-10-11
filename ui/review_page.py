"""Step 5: AI review of the finished file, then download."""
import html

import streamlit as st

from src.ai import AIUnavailable, get_client
from src.review import fingerprint, run_review
from ui import layout
from ui.validation_page import _fix

SEVERITY_TINT = {"high": "red", "medium": "amber", "low": "blue"}
SEVERITY_LABEL = {"high": "Likely to be rejected", "medium": "Worth fixing", "low": "Minor"}
SOURCE_LABEL = {"template": "Template rule", "general": "General knowledge - verify"}


def _run(tpl, rows):
    ss = st.session_state
    try:
        with st.spinner("Claude is reading the template's rules and your data..."):
            ss["ai_review"] = run_review(get_client(), tpl, rows)
        ss["ai_review_for"] = fingerprint(rows)
        ss["ai_review_error"] = ""
    except AIUnavailable as err:
        ss["ai_review_error"] = str(err)


def _card(f):
    bg, fg, border = layout.tint(SEVERITY_TINT[f.severity])
    parts = [layout.chip(SEVERITY_LABEL[f.severity], SEVERITY_TINT[f.severity]),
             layout.chip(SOURCE_LABEL[f.source], "gray" if f.source == "template" else "amber")]
    body = f"<b>{html.escape(f.column) or 'Whole file'}</b> &mdash; {html.escape(f.issue)}"
    if f.suggestion:
        body += f"<br><span style='color:var(--detail)'>Suggestion: {html.escape(f.suggestion)}</span>"
    if f.rule:
        body += f"<br><i style='color:var(--muted)'>Template says: &ldquo;{html.escape(f.rule)}&rdquo;</i>"
    st.markdown(f"<div style='background:{bg};border:1px solid {border};border-radius:var(--radius);padding:12px 16px;"
                f"margin:8px 0'>{''.join(parts)}<br>{body}</div>", unsafe_allow_html=True)


def render(tpl, master, mapping, rows):
    ss = st.session_state
    layout.help_text("A second pair of eyes. Claude reads the template's own rules and your finished data and lists "
                     "what looks wrong. It is advice, not a guarantee or legal advice: Amazon's upload check is "
                     "the final judge.")
    for key in ("ai_review", "ai_review_for", "ai_review_error"):
        ss.setdefault(key, None if key == "ai_review" else "")
    stale = ss["ai_review"] is not None and ss["ai_review_for"] != fingerprint(rows)
    label = "Review again" if ss["ai_review"] is not None else "Run the AI review"
    st.button(label, type="primary", on_click=_run, args=(tpl, rows), use_container_width=True)
    if ss["ai_review_error"]:
        st.warning(ss["ai_review_error"])
    review = ss["ai_review"]
    if review is None:
        st.caption("Takes about 20 seconds. Column names, statistics and a few sample rows are sent to the Claude API.")
        return
    if stale:
        st.info("Your answers changed since this review. Run it again to check the new data.")
    high = sum(f.severity == "high" for f in review.findings)
    a, b, c = st.columns(3)
    a.metric("Findings", len(review.findings))
    b.metric("Likely to be rejected", high)
    c.metric("Template rules used", sum(f.source == "template" for f in review.findings))
    if review.summary:
        st.markdown(f"**Summary.** {review.summary}")
    if not review.findings:
        st.success("Claude found nothing to flag in this file.")
    by_label = {}
    for col in tpl.columns:
        by_label.setdefault(col.label, col)
    for n, f in enumerate(review.findings):
        _card(f)
        col = by_label.get(f.column)
        if col is not None:
            st.button("Fix this", key=f"rev_fix_{n}", on_click=_fix, args=(col, tpl, master, mapping))
