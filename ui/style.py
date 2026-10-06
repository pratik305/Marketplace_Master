"""Light, soft colours for the question screen. Plain HTML/CSS, no extra libraries."""
import html

import streamlit as st

# soft background, strong-enough text, border
TINTS = {
    "blue":   ("#eef5ff", "#1f4e99", "#cfe0ff"),
    "red":    ("#fdecec", "#9b1c1c", "#f5c2c2"),
    "amber":  ("#fff6dc", "#8a5a00", "#f3dca0"),
    "green":  ("#e8f6ee", "#1d6b3f", "#bfe3cf"),
    "gray":   ("#f3f4f6", "#4b5563", "#dfe2e7"),
}
REQUIREMENT_TINT = {"Required": "red", "Conditionally Required": "amber"}

CSS = """
<style>
.q-card {border-radius: 14px; padding: 16px 20px; margin: 8px 0 14px 0; border: 1px solid; }
.q-title {font-size: 1.35rem; font-weight: 700; margin: 0 0 2px 0; color: #1d2330;}
.q-meta {font-size: .85rem; color: #5d6678; margin-bottom: 6px;}
.q-desc {font-size: .92rem; color: #374151; margin-top: 6px;}
.q-pill {display: inline-block; border-radius: 99px; padding: 2px 12px; font-size: .78rem; font-weight: 600;
         border: 1px solid; margin-right: 8px;}
.q-note {border-radius: 10px; padding: 10px 14px; margin: 8px 0; border: 1px solid; font-size: .92rem;}
div[data-testid="stButton"] > button {min-height: 3rem; font-size: 1.02rem; border-radius: 10px;}
div[data-testid="stRadio"] label {background: #f3f4f6; border: 1px solid #dfe2e7; border-radius: 10px;
                                  padding: 6px 14px; margin: 2px 6px 2px 0;}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def pill(text, tint):
    bg, fg, border = TINTS[tint]
    return f'<span class="q-pill" style="background:{bg};color:{fg};border-color:{border}">{html.escape(text)}</span>'


def card(title, requirement, group, description="", example=""):
    tint = REQUIREMENT_TINT.get(requirement, "gray")
    _, _, border = TINTS[tint]
    extra = f'<div class="q-desc">{html.escape(description)}</div>' if description else ""
    extra += f'<div class="q-desc"><i>Example: {html.escape(example)}</i></div>' if example else ""
    st.markdown(
        f'<div class="q-card" style="background:{TINTS["blue"][0]};border-color:{TINTS["blue"][2]};'
        f'border-left:8px solid {border}">'
        f'{pill(requirement, tint)}<span class="q-meta">{html.escape(group)}</span>'
        f'<div class="q-title">{html.escape(title)}</div>{extra}</div>', unsafe_allow_html=True)


def note(text, tint):
    bg, fg, border = TINTS[tint]
    st.markdown(f'<div class="q-note" style="background:{bg};color:{fg};border-color:{border}">'
                f'{html.escape(text)}</div>', unsafe_allow_html=True)
