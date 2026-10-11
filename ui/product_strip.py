"""The real product, always on screen: photo, title, SKU, price, key details, and prev / next to browse."""
import html

import streamlit as st

from src.result import clean
from src.rules import find_column


def _first(master, *names):
    """The first master column whose name matches one of `names` (exact first, then contains), or None."""
    cols = [str(c) for c in master.columns]
    for n in names:
        for c in cols:
            if c.lower() == n.lower():
                return c
    for n in names:
        for c in cols:
            if n.lower() in c.lower():
                return c
    return None


def _num(v):
    try:
        f = float(v)
        return f"{f:,.0f}" if abs(f - round(f)) < 0.005 else f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(v)


def describe_from_master(master, i):
    """What we know about product i from the master alone (before any rule or answer)."""
    def get(*names):
        c = _first(master, *names)
        v = clean(master.iloc[i][c]) if c else None
        return "" if v is None else str(v).strip()
    price = get("Selling Price", "MRP", "Price")
    attrs = [(label, get(*names)) for label, names in (
        ("Colour", ("Color",)), ("Size", ("Sku Size", "Ring Size")), ("Metal", ("Metal Stamp",)),
        ("Diamond", ("Diamond Weight",)), ("Weight", ("NET WEIGHT",)))]
    return {"image": get("Image Url 1", "Main Image"), "title": get("Sku Name", "Item Name", "Title"),
            "sku": get("Sku Code", "SKU"), "price": _num(price) if price else "",
            "attrs": [(k, v) for k, v in attrs if v], "bullets": [], "kind": ""}


def describe_from_rows(tpl, rows, i):
    """What will be written for product i: values by template column label."""
    def get(ref):
        col = find_column(tpl, ref)
        v = rows[i].get(col.index) if col else None
        return "" if v in (None, "") else str(v).strip()
    price = get("Your Price INR (Sell on Amazon, IN)")
    attrs = [(label, get(ref)) for label, ref in (
        ("Colour", "Color"), ("Ring size", "Ring Size"), ("Metal", "Metal Type#1"), ("Stamp", "Metal Stamp#1"),
        ("Diamond ct", "Total Diamond Weight"), ("Metal g", "Metal Weight"))]
    bullets = [b for b in (get(f"Bullet Point#{n}") for n in range(1, 6)) if b]
    return {"image": get("Main Image URL"), "title": get("Item Name"), "sku": get("SKU"),
            "price": _num(price) if price else "", "attrs": [(k, v) for k, v in attrs if v], "bullets": bullets,
            "kind": get("Parentage Level").lower()}


def _step(delta, n):
    ss = st.session_state
    ss["preview_no"] = max(1, min(n, int(ss.get("preview_no", 1)) + delta))


def _card_html(d, detail):
    img = (f'<img src="{html.escape(d["image"], quote=True)}" alt="product photo">' if d["image"]
           else '<div class="noimg">no photo<br>on this row</div>')
    tag = {"parent": " · parent listing", "child": " · variation"}.get(d["kind"], "")
    attrs = "".join(f"<span><em>{html.escape(k)}</em>{html.escape(v[:28])}</span>" for k, v in d["attrs"])
    bullets = ""
    if detail and d["bullets"]:
        bullets = "<ul>" + "".join(f"<li>{html.escape(b[:130])}</li>" for b in d["bullets"][:3]) + "</ul>"
    price = f" · Rs {html.escape(d['price'])}" if d["price"] else ""
    return (f'<div class="product">{img}<div><div class="ptitle">{html.escape(d["title"] or "Untitled product")}</div>'
            f'<div class="psub">{html.escape(d["sku"] or "no SKU")}{price}{tag}</div>'
            f'<div class="pattr">{attrs}</div>{bullets}</div></div>')


def render(tpl, master, rows=None, parent_flags=None, detail=False):
    """Show one product with prev / next. `rows` switches the card from the master to the finished listing."""
    ss = st.session_state
    n = len(master)
    if "preview_no" not in ss:
        first_child = next((i for i in range(n) if not (parent_flags and parent_flags[i])), 0)
        ss["preview_no"] = first_child + 1
    ss["preview_no"] = max(1, min(n, int(ss["preview_no"])))
    i = ss["preview_no"] - 1
    d = describe_from_rows(tpl, rows, i) if rows is not None else describe_from_master(master, i)
    if not d["image"] and d["kind"] == "parent" and i + 1 < n:            # a parent has no photo of its own
        nxt = describe_from_rows(tpl, rows, i + 1) if rows is not None else describe_from_master(master, i + 1)
        d["image"] = nxt["image"]
    st.markdown(_card_html(d, detail), unsafe_allow_html=True)
    a, b, c, _ = st.columns([1.5, 1.2, 1.6, 6])
    a.button("‹ Prev", key="prev_product", on_click=_step, args=(-1, n), disabled=i == 0,
             use_container_width=True)
    b.button("Next ›", key="next_product", on_click=_step, args=(1, n), disabled=i == n - 1,
             use_container_width=True)
    c.number_input("Product", min_value=1, max_value=n, key="preview_no", label_visibility="collapsed",
                   help=f"Product number, 1 to {n}")
