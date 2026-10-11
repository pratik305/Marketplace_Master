"""Page frame: masthead with the look switcher, clickable step bar, summary line, Back / Continue navigation."""
import html

import streamlit as st

from ui import themes

STEPS = ["Upload", "Prepare", "Answers", "Check", "AI review"]


def current_theme() -> str:
    return st.session_state.get("theme", themes.DEFAULT_THEME)


def inject():
    st.markdown(themes.css(current_theme()), unsafe_allow_html=True)


def tint(which):
    """(background, text, border) of a soft status colour in the current look."""
    return themes.tint(current_theme(), which)


def chip(text, which="blue"):
    bg, fg, border = tint(which)
    return f'<span class="chip" style="background:{bg};color:{fg};border-color:{border}">{html.escape(text)}</span>'


def hero():
    """Masthead: the name, one line about it, and the Look switcher."""
    st.session_state.setdefault("theme", themes.DEFAULT_THEME)
    left, right = st.columns([5, 3])
    left.markdown('<div class="masthead"><p class="mast-title">Marketplace Template Filler</p>'
                  '<p class="mast-sub">Your master sheet in, a filled marketplace template out. '
                  'Rules and Claude do the routine part; you decide the rest.</p></div>', unsafe_allow_html=True)
    right.radio("Look", list(themes.THEMES), key="theme", horizontal=True,
                help="; ".join(f"{n}: {t['about']}" for n, t in themes.THEMES.items()))


def summary_line(parts):
    """A quiet line of facts: [("608", "rows"), ("51", "columns filled by rules"), ...]."""
    dot = '<span class="dot">·</span>'
    st.markdown('<div class="summary">' + dot.join(f"<b>{html.escape(str(n))}</b> {html.escape(label)}"
                                                    for n, label in parts) + "</div>", unsafe_allow_html=True)


def go(step):
    st.session_state["step"] = step


def step_bar(ready):
    """Clickable steps. Steps after Upload unlock once the files are read."""
    cur = st.session_state.get("step", 1)
    cols = st.columns(len(STEPS))
    for i, (col, name) in enumerate(zip(cols, STEPS), start=1):
        label = f"✓  {name}" if i < cur else f"{i}   {name}"
        col.button(label, key=f"stepbtn_{i}", on_click=go, args=(i,), disabled=(i > 1 and not ready),
                   type="primary" if i == cur else "secondary", use_container_width=True)
    st.progress((cur - 1) / (len(STEPS) - 1))


def nav(back_to=None, next_to=None, next_label="Continue"):
    """Back / Continue buttons at the bottom of a step."""
    st.write("")
    a, b, c = st.columns([1, 2, 3])
    if back_to:
        a.button("← Back", key=f"back_{back_to}", on_click=go, args=(back_to,), use_container_width=True)
    if next_to:
        b.button(next_label + " →", key=f"next_{next_to}", on_click=go, args=(next_to,), type="primary",
                 use_container_width=True)


def help_text(text):
    st.markdown(f'<p class="step-help">{text}</p>', unsafe_allow_html=True)
