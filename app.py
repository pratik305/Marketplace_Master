"""Marketplace Template Filler - Streamlit entry point: four short steps."""
import streamlit as st

from src.questions import SKIP, build_queue, resolve_all
from src.result import build_rows
from src.xlsm_writer import WriterError, fill_template
from ui import (answer_sheet, layout, mapping_page, question_page, rules_page, upload_page,
                validation_page)

st.set_page_config(page_title="Marketplace Template Filler", layout="wide")
layout.inject()
layout.hero()

ss = st.session_state
ready = "template" in ss and "master" in ss
if not ready:
    ss["step"] = 1
ss.setdefault("step", 1)
layout.step_bar(ready)
step = ss["step"]

if step == 1 or not ready:
    upload_page.render()
    st.stop()

tpl, master = ss["template"], ss["master"]
rule_res = rules_page.compute(tpl, master)
mapping = mapping_page.ensure(tpl, master)
answers = ss.setdefault("answers", {})

queue = build_queue(tpl, mapping, master, ss.get("include_optional", False), ss.get("q_extra", set()),
                    ss.get("rule_covered", ()))
done = sum(1 for c in queue if answers.get(c.index) and answers[c.index].mode != SKIP)
st.markdown(layout.chip(f"{len(master)} rows", "gray")
            + layout.chip(f"{len(rule_res.values) if rule_res else 0} columns filled by rules", "green")
            + layout.chip(f"{len(mapping)} mapped from the master", "blue")
            + layout.chip(f"{done} of {len(queue)} answers given", "amber" if done < len(queue) else "green"),
            unsafe_allow_html=True)

if step == 2:
    layout.help_text("The rules and the column mapping run first, so you only answer what is left. "
                     "Check the mapping, or let Claude map the rest.")
    tab_rules, tab_map = st.tabs(["Built-in rules", "Column mapping"])
    with tab_rules:
        rules_page.render(tpl, master, rule_res)
    with tab_map:
        mapping_page.render(tpl, master)
    layout.nav(back_to=1, next_to=3, next_label="Continue to answers")

elif step == 3:
    layout.help_text("Fill in what is still missing. Rows are pre-filled where possible; nothing counts until you "
                     "press Apply all answers.")
    style_choice = st.radio("How do you want to answer?", ["Answer sheet", "One at a time"], horizontal=True,
                            key="answer_style")
    (answer_sheet if style_choice == "Answer sheet" else question_page).render(tpl, master, mapping)
    layout.nav(back_to=2, next_to=4, next_label="Continue to check & download")

else:
    layout.help_text("Check what is left, then download your filled template.")
    rows = build_rows(tpl, master, mapping, resolve_all(answers, master), rule_res.values if rule_res else None)
    validation_page.render(tpl, master, mapping, rows)
    st.markdown("#### Download")
    try:
        out = fill_template(ss["template_bytes"], tpl.data_row, rows)
        st.download_button("Download filled template", out, file_name="filled_" + ss.get("template_name", "template.xlsm"),
                           mime="application/vnd.ms-excel.sheet.macroEnabled.12", use_container_width=True)
        st.caption("Same file type and layout as your template, with the data filled in.")
    except WriterError as err:
        st.error(str(err))
    layout.nav(back_to=3)
