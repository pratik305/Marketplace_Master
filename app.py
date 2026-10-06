"""Marketplace Template Filler - Streamlit entry point."""
import streamlit as st

from src.master_reader import MasterError, read_master
from src.result import build_rows
from src.template_reader import TemplateError, read_template
from src.xlsm_writer import WriterError, fill_template
from src.questions import resolve_all
from ui import mapping_page, question_page, validation_page

st.set_page_config(page_title="Marketplace Template Filler", layout="wide")
st.title("Marketplace Template Filler")
st.caption("Upload your master sheet and the marketplace template. The tool maps columns, "
           "asks about what is missing, and gives you the filled template back.")

left, right = st.columns(2)
master_file = left.file_uploader("Master sheet (.xlsx)", type=["xlsx"], key="master_upload")
template_file = right.file_uploader("Template file (.xlsm)", type=["xlsm", "xlsx"], key="template_upload")

start = st.button("Read files", type="primary", disabled=not (master_file and template_file))
if not (master_file and template_file):
    st.info("Add both files to continue.")

if start:
    try:
        st.session_state["master"] = read_master(master_file.getvalue())
        st.session_state["template_bytes"] = template_file.getvalue()
        st.session_state["template_name"] = template_file.name
        st.session_state["template"] = read_template(st.session_state["template_bytes"])
        for k in ("mapping", "mapping_source", "mapping_conf", "answers", "q_index", "q_error", "q_warned", "q_extra"):
            st.session_state.pop(k, None)
    except (MasterError, TemplateError) as err:
        st.session_state.pop("template", None)
        st.error(str(err))

if "template" in st.session_state and "master" in st.session_state:
    tpl, master = st.session_state["template"], st.session_state["master"]
    st.subheader("What the tool understood")
    a, b, c, d = st.columns(4)
    a.metric("Master rows", len(master))
    b.metric("Master columns", len(master.columns))
    c.metric("Template columns", len(tpl.columns))
    d.metric("Required / conditionally required", f"{len(tpl.required_columns())} / {len(tpl.must_address()) - len(tpl.required_columns())}")
    st.caption(f"{len(tpl.dropdown_columns())} template columns have dropdown lists. "
               f"Data starts at row {tpl.data_row}.")
    with st.expander("Required and conditionally required template columns", expanded=True):
        st.dataframe(
            [{"Column": c.letter, "Name": c.label, "Group": c.group,
              "Requirement": c.requirement,
              "Dropdown": "yes" if c.has_dropdown else ""} for c in tpl.must_address()],
            use_container_width=True, hide_index=True)
    with st.expander("Master preview"):
        st.dataframe(master.head(20), use_container_width=True)

    mapping = mapping_page.render(tpl, master)
    question_page.render(tpl, master, mapping)
    rows = build_rows(tpl, master, mapping, resolve_all(st.session_state.get("answers", {}), master))
    validation_page.render(tpl, master, mapping, rows)
    st.subheader("Download")
    st.caption(f"{len(mapping)} template columns are mapped to a master column. "
               "Defaults pre-filled in the template are kept.")
    try:
        out = fill_template(st.session_state["template_bytes"], tpl.data_row, rows)
        st.download_button("Download filled template", out,
                           file_name="filled_" + st.session_state.get("template_name", "template.xlsm"),
                           mime="application/vnd.ms-excel.sheet.macroEnabled.12")
    except WriterError as err:
        st.error(str(err))
