"""Built-in listing rules: the values a team already knows, so the tool never has to ask about them.

Rules come from a JSON file (see rules/amazon_in_jewellery.json). They fill columns from fixed values,
copies of master columns, value translations (e.g. "IGI Certificate" -> "IGI") and a few derivations
(parent/child, product type, metal, colour, browse node). Every rule value is checked against the template's
own dropdown list, and anything that does not fit is reported instead of written silently.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.questions import key_of

DEFAULT_RULES = Path(__file__).resolve().parent.parent / "rules" / "amazon_in_jewellery.json"


class RulesError(Exception):
    """Raised with a plain message when the rules file can't be used."""


@dataclass
class RuleResult:
    values: dict = field(default_factory=dict)       # template column index -> [value or None per master row]
    child_only: set = field(default_factory=set)     # column indexes that are intentionally blank on parent rows
    applied: list = field(default_factory=list)      # (label, kind, rows filled)
    problems: list = field(default_factory=list)     # (label, value, reason): rule values the template would not accept
    skipped: list = field(default_factory=list)      # (label, reason): rules that could not run on these files
    is_parent: list = field(default_factory=list)    # per master row: is it a parent row?

    def covered(self) -> set:
        """Columns the rules fill completely (every row, or every child row for child-only columns)."""
        out = set()
        for idx, vals in self.values.items():
            need = [i for i, p in enumerate(self.is_parent) if not (p and idx in self.child_only)]
            if all(vals[i] is not None for i in need):
                out.add(idx)
        return out


def load_rules(path=DEFAULT_RULES) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RulesError(f"The rules file could not be read: {exc}") from exc


def find_column(info, ref: str):
    """Find a template column by 'Label' or 'Label#n' (n-th column with that label, 1-based)."""
    label, _, nth = ref.partition("#")
    nth = int(nth) - 1 if nth else 0
    exact = [c for c in info.columns if c.label == label]
    if len(exact) > nth:
        return exact[nth]
    starts = [c for c in info.columns if c.label.startswith(label)]
    return starts[nth] if len(starts) > nth else None


def _first_word_upper(text: str) -> str:
    words = re.findall(r"[A-Za-z]+", text or "")
    return words[0].upper() if words else ""


def _norm_stamp(raw: str, aliases: dict) -> str:
    s = (raw or "").strip().upper().replace(" ", "")
    return aliases.get(s, s)


def apply_rules(info, master, rules: dict) -> RuleResult:
    """Compute rule values for every master row. Pure: nothing is written anywhere."""
    n = len(master)
    res = RuleResult()
    cols = set(str(c) for c in master.columns)

    def src(row_i, column):
        return key_of(master.iloc[row_i][column]) if column in cols else ""

    marker = rules.get("parent_marker", {})
    family_col = rules.get("family_column")
    is_parent = [bool(marker) and marker.get("column") in cols
                 and src(i, marker["column"]).upper() == str(marker.get("value", "")).upper() for i in range(n)]
    res.is_parent = is_parent
    family = [src(i, family_col) if family_col in cols else str(i) for i in range(n)]
    first_child = {}
    for i in range(n):
        if not is_parent[i]:
            first_child.setdefault(family[i], i)

    def put(ref, fn, kind, child_only=False):
        col = find_column(info, ref)
        if col is None:
            res.skipped.append((ref, "no such column in this template"))
            return
        vals = [None if (child_only and is_parent[i]) else fn(i) for i in range(n)]
        vals = [v if v not in ("", None) else None for v in vals]
        if not child_only and ref not in rules.get("no_parent_inherit", []):
            # parents take the first child's value when they have none
            for i in range(n):
                if vals[i] is None and is_parent[i] and family[i] in first_child:
                    vals[i] = vals[first_child[family[i]]]
        else:
            res.child_only.add(col.index)
        filled = sum(v is not None for v in vals)
        if filled:
            res.values[col.index] = vals
            res.applied.append((col.label, kind, filled))
        if col.allowed and ref not in rules.get("unchecked_dropdowns", {}).get("columns", []):
            allowed = {a.lower() for a in col.allowed}
            for v in dict.fromkeys(v for v in vals if v is not None):
                if str(v).lower() not in allowed:
                    res.problems.append((col.label, v, "not in the template's dropdown list"))

    def copy_rules(table, child_only):
        for ref, master_col in table.items():
            if master_col not in cols:
                res.skipped.append((ref, f"master has no column '{master_col}'"))
                continue
            put(ref, lambda i, c=master_col: src(i, c) or None, "copy", child_only)

    def const_rules(table, child_only):
        for ref, value in table.items():
            put(ref, lambda i, v=value: v, "fixed value", child_only)

    const_rules(rules.get("constants", {}), False)
    copy_rules(rules.get("copy", {}), False)
    const_rules(rules.get("child_only", {}).get("constants", {}), True)
    copy_rules(rules.get("child_only", {}).get("copy", {}), True)

    for ref, spec in rules.get("value_maps", {}).items():
        if spec["from"] not in cols:
            res.skipped.append((ref, f"master has no column '{spec['from']}'"))
            continue
        table = spec["map"]
        put(ref, lambda i, s=spec["from"], t=table: (t.get(src(i, s), src(i, s)) or None), "translated")

    # ---- derivations ----
    put("Parentage Level", lambda i: "parent" if is_parent[i] else "child", "parent/child")
    if family_col in cols:
        sku_col = (rules.get("copy", {}).get("SKU") or "Sku Code")
        parent_sku = {family[i]: src(i, sku_col) for i in range(n) if is_parent[i]}
        put("Parent SKU", lambda i: parent_sku.get(family[i]), "parent/child", child_only=True)

    cat_col = marker.get("column")
    if cat_col in cols:
        def family_category(i):
            j = i if not is_parent[i] else first_child.get(family[i])
            return _first_word_upper(src(j, cat_col)) if j is not None else ""
        ptypes = rules.get("product_types", {})
        put("Product Type", lambda i: ptypes.get(family_category(i)), "from category")
        kw = rules.get("browse_keywords", {})
        node_col = find_column(info, "Recommended Browse Nodes")
        gcol = rules.get("value_maps", {}).get("Target Gender", {}).get("from")

        def browse(i):
            word = kw.get(family_category(i))
            if not word or node_col is None:
                return None
            who = "Men" if src(i if not is_parent[i] else first_child.get(family[i], i), gcol or "") == "Men" else "Women"
            hits = [a for a in node_col.allowed if re.search(rf"\b{who}\b", a) and re.search(rf"\b{word}\b", a)]
            return hits[0] if hits else None
        put("Recommended Browse Nodes", browse, "from category")

    metal = rules.get("metal")
    if metal and metal["source"] in cols:
        aliases, silver = metal.get("stamp_aliases", {}), metal.get("silver_stamps", ["925"])
        ccol = metal.get("color")

        def stamp(i):
            return _norm_stamp(src(i, metal["source"]), aliases)

        def metal_type(i):
            s = stamp(i)
            if not s:
                return None
            if s in silver:
                return "Sterling Silver"
            color = src(i, ccol) if ccol in cols else ""
            return color if "gold" in color.lower() else f"{s} Gold"

        def material(i):
            s, t = stamp(i), metal_type(i)
            return None if not s else ("Sterling Silver" if s in silver else f"{s.lower()} {t}")

        put("Metal Type#1", metal_type, "from metal stamp")
        put("Metal Stamp#1", lambda i: stamp(i) or None, "from metal stamp")
        put("Material#1", material, "from metal stamp", child_only=True)
        if ccol in cols:
            put("Color Map", lambda i: re.sub(r"\s*gold\s*", "", src(i, ccol), flags=re.I).strip() or None, "from colour")
    return res
