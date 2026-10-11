"""Small building blocks for the question cards: a status pill, a note and the question card.

Colours come from the current look (see ui/themes.py); the shapes come from the page stylesheet.
"""
import html

import streamlit as st

from ui import layout

REQUIREMENT_TINT = {"Required": "red", "Conditionally Required": "amber"}


def inject():
    """The stylesheet is injected once per run by the page frame; kept so older callers still work."""
    layout.inject()


def pill(text, tint):
    bg, fg, border = layout.tint(tint)
    return f'<span class="q-pill" style="background:{bg};color:{fg};border-color:{border}">{html.escape(text)}</span>'


def card(title, requirement, group, description="", example=""):
    tint = REQUIREMENT_TINT.get(requirement, "gray")
    extra = f'<div class="q-desc">{html.escape(description)}</div>' if description else ""
    extra += f'<div class="q-desc"><i>Example: {html.escape(example)}</i></div>' if example else ""
    st.markdown(f'<div class="q-card">{pill(requirement, tint)}<span class="q-meta">{html.escape(group)}</span>'
                f'<div class="q-title">{html.escape(title)}</div>{extra}</div>', unsafe_allow_html=True)


def note(text, tint):
    bg, fg, border = layout.tint(tint)
    st.markdown(f'<div class="q-note" style="background:{bg};color:{fg};border-color:{border}">'
                f'{html.escape(text)}</div>', unsafe_allow_html=True)
