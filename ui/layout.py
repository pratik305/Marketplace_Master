"""Page frame: soft light theme, header, clickable step bar and Back / Continue navigation."""
import streamlit as st

STEPS = ["Upload", "Prepare", "Answers", "Check", "AI review & download"]

CSS = """
<style>
.stApp {background: #f5f8fc;}
.block-container {max-width: 1150px; padding-top: 3.6rem; padding-bottom: 4rem;}
footer {visibility: hidden;}
h1, h2, h3 {color: #1d2a44; letter-spacing: -0.01em;}
/* hero */
.hero {background: linear-gradient(120deg, #e6f0ff 0%, #f4f9ff 60%, #ffffff 100%); border: 1px solid #d4e3fb;
       border-radius: 18px; padding: 20px 26px; margin-bottom: 14px;}
.hero-title {font-size: 1.7rem; font-weight: 750; color: #1d2a44; margin: 0;}
.hero-sub {color: #51607a; margin: 4px 0 0 0; font-size: .98rem;}
/* cards: bordered containers and metrics */
div[data-testid="stVerticalBlockBorderWrapper"] {background: #ffffff; border-radius: 14px;}
div[data-testid="stMetric"] {background: #ffffff; border: 1px solid #e1e9f5; border-radius: 14px; padding: 12px 16px;}
div[data-testid="stMetricValue"] {color: #1f4e99;}
/* buttons */
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button,
button[kind="primaryFormSubmit"], button[kind="secondaryFormSubmit"] {
    border-radius: 12px; min-height: 2.9rem; font-weight: 600; border: 1px solid #cfdcf0;}
div[data-testid="stButton"] > button[kind="primary"], div[data-testid="stDownloadButton"] > button {
    background: #1f6feb; color: #ffffff; border-color: #1f6feb;}
div[data-testid="stButton"] > button[kind="primary"]:hover, div[data-testid="stDownloadButton"] > button:hover {
    background: #1859c2; border-color: #1859c2; color: #ffffff;}
/* tabs, expanders, uploaders */
button[data-baseweb="tab"] {font-weight: 600;}
details {background: #ffffff; border-radius: 12px;}
section[data-testid="stFileUploaderDropzone"], div[data-testid="stFileUploaderDropzone"] {
    background: #f0f6ff; border: 2px dashed #9dbdf0; border-radius: 14px;}
/* chips */
.chip {display: inline-block; border-radius: 99px; padding: 3px 14px; font-size: .82rem; font-weight: 600;
       border: 1px solid; margin: 0 8px 6px 0;}
.step-help {color: #51607a; margin: 2px 0 10px 0;}
</style>
"""

CHIP_TINTS = {"blue": ("#eef5ff", "#1f4e99", "#cfe0ff"), "green": ("#e8f6ee", "#1d6b3f", "#bfe3cf"),
              "amber": ("#fff6dc", "#8a5a00", "#f3dca0"), "red": ("#fdecec", "#9b1c1c", "#f5c2c2"),
              "gray": ("#f3f4f6", "#4b5563", "#dfe2e7")}


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def chip(text, tint="blue"):
    bg, fg, border = CHIP_TINTS[tint]
    return f'<span class="chip" style="background:{bg};color:{fg};border-color:{border}">{text}</span>'


def hero():
    st.markdown('<div class="hero"><p class="hero-title">Marketplace Template Filler</p>'
                '<p class="hero-sub">Fill your marketplace upload template from your master sheet: '
                'upload, let the rules and Claude do the work, answer what is left, download.</p></div>',
                unsafe_allow_html=True)


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
