"""Mapping step: show the proposed pairs and let the user correct them."""
import pandas as pd
import streamlit as st

from src.ai import AIUnavailable, get_client, propose_mapping
from src.mapper import name_match

BLANK = ""
MIN_CONFIDENCE = 0.5      # AI pairs below this are shown as suggestions, never applied automatically


def init_mapping(tpl, master):
    """Start with name-matched pairs the first time files are read."""
    if "mapping" not in st.session_state:
        st.session_state["mapping"] = name_match(tpl.columns, master.columns)
        st.session_state["mapping_source"] = {i: "name" for i in st.session_state["mapping"]}
        st.session_state["mapping_conf"] = {}


def ensure(tpl, master):
    """The current mapping, created from name matching the first time (no screen output)."""
    init_mapping(tpl, master)
    return st.session_state["mapping"]


def render(tpl, master):
    init_mapping(tpl, master)
    mapping, source, conf = (st.session_state["mapping"], st.session_state["mapping_source"],
                             st.session_state["mapping_conf"])

    st.subheader("Column mapping")
    st.caption("Check each pair. Change any wrong one, or clear it to leave that column for the questions.")
    if st.button("Ask Claude to map the rest"):
        try:
            with st.spinner("Claude is reading the column names..."):
                found = propose_mapping(get_client(), tpl.columns, master, mapping)
            applied = {i: v for i, v in found.items() if v[1] >= MIN_CONFIDENCE}
            for idx, (col, c) in applied.items():
                mapping[idx], source[idx], conf[idx] = col, "AI", c
            st.success(f"Claude proposed {len(found)} more pairs; {len(applied)} applied.")
            unsure = {i: v for i, v in found.items() if v[1] < MIN_CONFIDENCE}
            if unsure:
                by = {c.index: c for c in tpl.columns}
                st.info("Not applied (low confidence, check by hand if you want them): " + "; ".join(
                    f"{by[i].label} <- {col} ({c:.2f})" for i, (col, c) in unsure.items()))
        except AIUnavailable as err:
            st.warning(f"{err} Name matching is still in use.")

    shown = [c for c in tpl.columns if c.must_address or c.index in mapping]
    options = [BLANK] + [str(c) for c in master.columns]
    table = pd.DataFrame([{
        "Column": c.letter, "Template column": c.label, "Requirement": c.requirement,
        "Master column": mapping.get(c.index, BLANK),
        "Proposed by": source.get(c.index, ""),
        "Confidence": conf.get(c.index) if c.index in conf else None,
    } for c in shown])
    edited = st.data_editor(
        table, hide_index=True, use_container_width=True, key="mapping_editor",
        disabled=["Column", "Template column", "Requirement", "Proposed by", "Confidence"],
        column_config={"Master column": st.column_config.SelectboxColumn(
            "Master column", options=options, required=False)})
    for c, new in zip(shown, edited["Master column"]):
        new = new or BLANK
        if new == BLANK:
            if c.index in mapping:
                del mapping[c.index]
                source.pop(c.index, None)
        elif mapping.get(c.index) != new:
            mapping[c.index], source[c.index] = new, "you"
            conf.pop(c.index, None)
    return mapping
