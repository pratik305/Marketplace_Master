"""Three looks for the site. Each is a set of colours, fonts and shapes fed into one stylesheet."""

DEFAULT_THEME = "Boutique"

# bg, panel, ink, muted, line, accent, accent_ink, radius, head font, body font, note font
THEMES = {
    "Boutique": {
        "about": "Ivory and ink with a thin gold detail, serif headings",
        "bg": "#faf7f2", "panel": "#fffdf9", "ink": "#1f1d1a", "muted": "#6b665c", "line": "#ded6c6",
        "accent": "#1f1d1a", "accent_ink": "#faf7f2", "detail": "#9c7a2e", "radius": "2px",
        "head": "'Cormorant Garamond', 'Playfair Display', Georgia, serif",
        "body": "'Inter', 'Segoe UI', system-ui, sans-serif", "note": "'Inter', 'Segoe UI', system-ui, sans-serif",
        "fonts": "family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600",
        "title_size": "2.5rem", "density": "1",
        "tints": {"red": ("#f9ece8", "#8c2f22", "#e9c9c2"), "amber": ("#f8f0dc", "#7a5a10", "#e6d6a8"),
                  "green": ("#ecf2e4", "#3b5a22", "#cfdcbc"), "blue": ("#f1eee6", "#4a4538", "#ddd5c3"),
                  "gray": ("#f3efe7", "#5c574b", "#e1d9c8")},
    },
    "Sheet": {
        "about": "Compact and grid-like, like the spreadsheets your team works in",
        "bg": "#f3f6f4", "panel": "#ffffff", "ink": "#1b2a22", "muted": "#5d6f64", "line": "#c9d5cd",
        "accent": "#1e7145", "accent_ink": "#ffffff", "detail": "#1e7145", "radius": "0px",
        "head": "'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif",
        "body": "'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif",
        "note": "'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif",
        "fonts": "family=IBM+Plex+Sans:wght@400;500;600;700",
        "title_size": "1.7rem", "density": "0.7",
        "tints": {"red": ("#fbe9e7", "#8c2f22", "#efc3bd"), "amber": ("#fdf4d8", "#7a5a10", "#ecd99a"),
                  "green": ("#e3f1e8", "#1e5c38", "#b8d9c4"), "blue": ("#e8f0ee", "#2f4f45", "#c4d6cf"),
                  "gray": ("#eef1ef", "#4f5f56", "#d3dbd6")},
    },
    "Workshop": {
        "about": "Warm paper tones, deep green, a hand-written note here and there",
        "bg": "#f6efe4", "panel": "#fffaf2", "ink": "#2b2420", "muted": "#6f6254", "line": "#dccfb9",
        "accent": "#2f4a3a", "accent_ink": "#fffaf2", "detail": "#7a2e3a", "radius": "6px",
        "head": "'Fraunces', 'Georgia', serif", "body": "'Karla', 'Segoe UI', system-ui, sans-serif",
        "note": "'Caveat', 'Karla', cursive",
        "fonts": "family=Fraunces:wght@500;600;700&family=Karla:wght@400;500;700&family=Caveat:wght@500;600",
        "title_size": "2.2rem", "density": "1",
        "tints": {"red": ("#f7e6e1", "#842c25", "#e6c4bb"), "amber": ("#f9ecd0", "#775410", "#e8d3a2"),
                  "green": ("#e6eedb", "#35502b", "#c8d9b8"), "blue": ("#ece6d8", "#4c4332", "#d9ceb4"),
                  "gray": ("#efe7d9", "#5f5445", "#ddd1ba")},
    },
}


def get(name):
    return THEMES.get(name) or THEMES[DEFAULT_THEME]


def css(name) -> str:
    t = get(name)
    gap = "0.55rem" if t["density"] != "1" else "1rem"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?{t["fonts"]}&display=swap');
:root {{--bg:{t["bg"]}; --panel:{t["panel"]}; --ink:{t["ink"]}; --muted:{t["muted"]}; --line:{t["line"]};
        --accent:{t["accent"]}; --accent-ink:{t["accent_ink"]}; --detail:{t["detail"]}; --radius:{t["radius"]};}}
.stApp {{background: var(--bg); color: var(--ink); font-family: {t["body"]};}}
.stApp p, .stApp label, .stApp span, .stApp li, .stApp div {{font-family: {t["body"]};}}
.block-container {{max-width: 1120px; padding-top: 3.4rem; padding-bottom: 4rem;}}
div[data-testid="stVerticalBlock"] {{gap: {gap};}}
footer {{visibility: hidden;}}
h1, h2, h3, h4, h5, h1 *, h2 *, h3 *, h4 *, h5 * {{font-family: {t["head"]} !important; color: var(--ink);
    letter-spacing: -0.005em; font-weight: 600;}}
a {{color: var(--detail);}}

/* masthead: a title and a hairline, no banner */
.masthead {{border-bottom: 1px solid var(--line); padding: 0 0 .7rem 0; margin-bottom: .9rem;}}
.stApp .mast-title {{font-family: {t["head"]}; font-size: {t["title_size"]}; font-weight: 700; margin: 0; color: var(--ink); line-height: 1.1;}}
.mast-sub {{color: var(--muted); margin: .25rem 0 0 0; font-size: .95rem;}}
.stApp .step-help {{color: var(--muted); margin: .1rem 0 .6rem 0; font-family: {t["note"]}; font-size: {"1.25rem" if t["note"].startswith("'Caveat'") else ".95rem"};}}
.summary {{color: var(--muted); font-size: .92rem; margin: .1rem 0 .4rem 0;}}
.summary b {{color: var(--ink);}}
.summary .dot {{color: var(--line); margin: 0 .55rem;}}

/* buttons: flat; the main action is solid, everything else is a hairline */
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button,
button[kind="primaryFormSubmit"], button[kind="secondaryFormSubmit"] {{
    border-radius: var(--radius); min-height: 2.6rem; font-weight: 600; background: transparent; color: var(--ink);
    border: 1px solid var(--line); box-shadow: none;}}
div[data-testid="stButton"] > button:hover {{border-color: var(--ink); color: var(--ink);}}
div[data-testid="stButton"] > button[kind="primary"], div[data-testid="stDownloadButton"] > button,
button[kind="primaryFormSubmit"] {{background: var(--accent); color: var(--accent-ink); border-color: var(--accent);}}
div[data-testid="stButton"] > button[kind="primary"]:hover, div[data-testid="stDownloadButton"] > button:hover {{
    filter: brightness(1.12); color: var(--accent-ink);}}
div[data-testid="stButton"] > button[kind="primary"] p, div[data-testid="stDownloadButton"] > button p {{color: var(--accent-ink);}}

/* containers, metrics, expanders: hairlines instead of cards and shadows */
div[data-testid="stVerticalBlockBorderWrapper"] {{border-radius: var(--radius);}}
div[data-testid="stMetric"] {{background: transparent; border: none; border-top: 1px solid var(--line); border-radius: 0; padding: .5rem 0 0 0;}}
div[data-testid="stMetricLabel"] {{color: var(--muted); text-transform: uppercase; font-size: .72rem; letter-spacing: .06em;}}
div[data-testid="stMetricValue"] {{color: var(--ink); font-family: {t["head"]};}}
details {{background: var(--panel); border: 1px solid var(--line) !important; border-radius: var(--radius);}}
button[data-baseweb="tab"] {{font-weight: 600; color: var(--muted);}}
button[data-baseweb="tab"][aria-selected="true"] {{color: var(--ink);}}
div[data-baseweb="tab-highlight"] {{background: var(--detail);}}
section[data-testid="stFileUploaderDropzone"], div[data-testid="stFileUploaderDropzone"] {{
    background: var(--panel); border: 1px dashed var(--detail); border-radius: var(--radius);}}
input, textarea, div[data-baseweb="select"] > div {{border-radius: var(--radius) !important;}}
.stProgress > div > div > div > div {{background: var(--detail);}}

/* question cards and notes */
.q-card {{background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--detail);
          border-radius: var(--radius); padding: 14px 18px; margin: 6px 0 12px 0;}}
.stApp .q-title {{font-family: {t["head"]}; font-size: 1.4rem; font-weight: 700; color: var(--ink); margin: 2px 0;}}
.q-meta {{font-size: .82rem; color: var(--muted);}}
.q-desc {{font-size: .92rem; color: var(--muted); margin-top: 4px;}}
.q-note {{border-radius: var(--radius); padding: 9px 13px; margin: 6px 0; border: 1px solid; font-size: .92rem;}}
.q-pill, .chip {{display: inline-block; border: 1px solid; padding: 1px 9px; font-size: .75rem; font-weight: 600;
                 letter-spacing: .02em; margin-right: 6px; border-radius: var(--radius);}}

/* product strip: the real product, always in view */
.product {{display: flex; gap: 16px; align-items: flex-start; border: 1px solid var(--line); background: var(--panel);
           padding: 12px 14px; border-radius: var(--radius); margin: 6px 0 4px 0;}}
.product img {{width: 92px; height: 92px; object-fit: cover; border: 1px solid var(--line); border-radius: var(--radius); background: var(--bg);}}
.product .noimg {{width: 92px; height: 92px; border: 1px dashed var(--line); display: flex; align-items: center;
                  justify-content: center; color: var(--muted); font-size: .72rem; text-align: center;}}
.stApp .product .ptitle {{font-family: {t["head"]}; font-size: 1.15rem; font-weight: 700; color: var(--ink); line-height: 1.25;}}
.product .psub {{color: var(--muted); font-size: .85rem; margin-top: 2px;}}
.product .pattr {{margin-top: 6px; font-size: .85rem; color: var(--ink);}}
.product .pattr span {{margin-right: 14px;}}
.product .pattr em {{color: var(--muted); font-style: normal; margin-right: 4px;}}
.product ul {{margin: 6px 0 0 16px; padding: 0; color: var(--muted); font-size: .84rem;}}
</style>
"""


def tint(name, which):
    return get(name)["tints"][which]
