"""Step 1: upload the master sheet and the template, then read them."""
import streamlit as st

from src.master_reader import MasterError, read_master
from src.template_reader import TemplateError, read_template
from ui import layout

RESET_KEYS = ("mapping", "mapping_source", "mapping_conf", "answers", "q_index", "q_error", "q_warned", "q_extra",
              "saved_answers", "ai_proposals", "sheet_errors", "sheet_saved_count")


def _read_files():
    """Button callback: read both files, and move to the next step when they are fine."""
    ss = st.session_state
    master_file, template_file = ss.get("master_upload"), ss.get("template_upload")
    ss["read_error"] = ""
    try:
        master = read_master(master_file.getvalue())
        template_bytes = template_file.getvalue()
        template = read_template(template_bytes)
    except (MasterError, TemplateError) as err:
        ss["read_error"] = str(err)
        return
    ss["master"], ss["template_bytes"], ss["template"] = master, template_bytes, template
    ss["template_name"] = template_file.name
    for k in RESET_KEYS:
        ss.pop(k, None)
    for k in [k for k in ss if k.startswith(("sheet_", "mode_", "val_", "by_", "lk_"))]:
        ss.pop(k, None)
    ss["step"] = 2


def render():
    ss = st.session_state
    layout.help_text("Add the master sheet and the marketplace template, then press <b>Read files</b>.")
    left, right = st.columns(2)
    with left.container(border=True):
        st.markdown("**1. Master sheet**")
        st.caption("Your product data, one row per product or variant (.xlsx)")
        master_file = st.file_uploader("Master sheet (.xlsx)", type=["xlsx"], key="master_upload",
                                       label_visibility="collapsed")
    with right.container(border=True):
        st.markdown("**2. Marketplace template**")
        st.caption("The Amazon listing template you downloaded (.xlsm)")
        template_file = st.file_uploader("Template file (.xlsm)", type=["xlsm", "xlsx"], key="template_upload",
                                         label_visibility="collapsed")
    st.button("Read files", type="primary", disabled=not (master_file and template_file), on_click=_read_files,
              use_container_width=True)
    if not (master_file and template_file):
        st.caption("Add both files to continue.")
    if ss.get("read_error"):
        st.error(ss["read_error"])

    if "template" in ss and "master" in ss:
        tpl, master = ss["template"], ss["master"]
        st.markdown("#### What the tool understood")
        a, b, c, d = st.columns(4)
        a.metric("Master rows", len(master))
        b.metric("Master columns", len(master.columns))
        c.metric("Template columns", len(tpl.columns))
        d.metric("Required / conditional",
                 f"{len(tpl.required_columns())} / {len(tpl.must_address()) - len(tpl.required_columns())}")
        with st.expander("Master preview"):
            st.dataframe(master.head(20), use_container_width=True)
        layout.nav(next_to=2, next_label="Continue to prepare")
