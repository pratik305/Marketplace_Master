"""Rules step: what the built-in listing rules fill, before any question is asked."""
import streamlit as st

from src.rules import RulesError, apply_rules, load_rules


def render(tpl, master):
    """Show the rules summary. Returns the RuleResult, or None when the rules are switched off or unusable."""
    ss = st.session_state
    st.subheader("Built-in listing rules")
    on = st.checkbox("Apply the built-in jewellery rules (parent/child, product type, metal, units, fixed values)",
                     value=True, key="rules_on")
    ss["rule_covered"], ss["rule_parent_blank"] = set(), set()
    if not on:
        st.caption("Rules are off: every column comes from the mapping and your answers.")
        return None
    try:
        res = apply_rules(tpl, master, load_rules())
    except RulesError as err:
        st.warning(f"{err} Continuing without rules.")
        return None
    ss["rule_covered"], ss["rule_parent_blank"] = res.covered(), set(res.child_only)
    parents = sum(res.is_parent)
    a, b, c = st.columns(3)
    a.metric("Columns filled by rules", len(res.values))
    b.metric("Parent / child rows", f"{parents} / {len(master) - parents}")
    c.metric("Rule values to check", len(res.problems))
    st.caption("Rules fill what your team already knows. The questions below only cover what is left.")
    with st.expander("What the rules filled"):
        st.dataframe([{"Column": label, "Rule": kind, "Rows filled": n} for label, kind, n in res.applied],
                     use_container_width=True, hide_index=True)
    if res.problems:
        with st.expander(f"Rule values the template's dropdown would not accept ({len(res.problems)})", expanded=True):
            for label, value, why in res.problems[:40]:
                st.markdown(f"- **{label}**: '{value}' {why}")
    if res.skipped:
        with st.expander(f"Rules that could not run on these files ({len(res.skipped)})"):
            for label, why in res.skipped:
                st.markdown(f"- {label}: {why}")
    return res
