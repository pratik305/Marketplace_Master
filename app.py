"""Marketplace Template Filler - Streamlit entry point: five short steps."""
import streamlit as st

from src.questions import SKIP, build_queue, resolve_all
from src.result import build_rows
from src.xlsm_writer import WriterError, fill_template
from ui import (answer_sheet, layout, mapping_page, product_strip, question_page, review_page, rules_page,
                upload_page, validation_page)

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
layout.summary_line([(len(master), "rows"), (len(rule_res.values) if rule_res else 0, "columns filled by rules"),
                     (len(mapping), "mapped from the master"), (f"{done} of {len(queue)}", "answers given")])
parent_flags = rule_res.is_parent if rule_res else None

if step in (2, 3):
    product_strip.render(tpl, master, None, parent_flags)

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
    layout.nav(back_to=2, next_to=4, next_label="Continue to check")

else:
    rows = build_rows(tpl, master, mapping, resolve_all(answers, master), rule_res.values if rule_res else None)

    def download_block(key):
        try:
            out = fill_template(ss["template_bytes"], tpl.data_row, rows)
            st.download_button("Download filled template", out, key=key,
                               file_name="filled_" + ss.get("template_name", "template.xlsm"),
                               mime="application/vnd.ms-excel.sheet.macroEnabled.12", use_container_width=True)
            st.caption("Same file type and layout as your template, with the data filled in.")
        except WriterError as err:
            st.error(str(err))

    product_strip.render(tpl, master, rows, parent_flags, detail=True)
    if step == 4:
        layout.help_text("Check what is left. You can download now, or run the AI review first.")
        validation_page.render(tpl, master, mapping, rows)
        st.markdown("#### Download")
        download_block("download_check")
        layout.nav(back_to=3, next_to=5, next_label="Continue to the AI review")
    else:
        review_page.render(tpl, master, mapping, rows)
        st.markdown("#### Download")
        download_block("download_final")
        layout.nav(back_to=4)
