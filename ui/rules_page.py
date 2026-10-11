"""Built-in listing rules: compute them for the app, and show what they filled."""
import streamlit as st

from src.rules import RulesError, apply_rules, load_rules


def compute(tpl, master):
    """Apply the rules (unless switched off) and remember which columns they fully cover.

    Runs on every step so the answer sheet and validation always know what the rules filled.
    Returns the RuleResult, or None when the rules are off or unusable.
    """
    ss = st.session_state
    ss["rule_covered"], ss["rule_parent_blank"], ss["rules_error"] = set(), set(), ""
    if not ss.get("rules_on", True):
        return None
    try:
        res = apply_rules(tpl, master, load_rules())
    except RulesError as err:
        ss["rules_error"] = str(err)
        return None
    ss["rule_covered"], ss["rule_parent_blank"] = res.covered(), set(res.child_only)
    return res


def render(tpl, master, res):
    """Show what the rules filled, with the on/off switch."""
    ss = st.session_state
    st.checkbox("Apply the built-in jewellery rules (parent/child, product type, metal, units, fixed values)",
                value=True, key="rules_on")
    if ss.get("rules_error"):
        st.warning(f"{ss['rules_error']} Continuing without rules.")
    if res is None:
        st.caption("Rules are off: every column comes from the mapping and your answers.")
        return
    parents = sum(res.is_parent)
    a, b, c = st.columns(3)
    a.metric("Columns filled by rules", len(res.values))
    b.metric("Parent / child rows", f"{parents} / {len(master) - parents}")
    c.metric("Rule values to check", len(res.problems))
    st.caption("Rules fill what your team already knows. The answer sheet only covers what is left.")
    with st.expander("What the rules filled"):
        st.dataframe([{"Column": label, "Rule": kind, "Rows filled": n} for label, kind, n in res.applied],
                     use_container_width=True, hide_index=True)
    if res.problems:
        with st.expander(f"Rule values the template's dropdown would not accept ({len(res.problems)})",
                         expanded=True):
            for label, value, why in res.problems[:40]:
                st.markdown(f"- **{label}**: '{value}' {why}")
    if res.skipped:
        with st.expander(f"Rules that could not run on these files ({len(res.skipped)})"):
            for label, why in res.skipped:
                st.markdown(f"- {label}: {why}")
