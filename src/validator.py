"""Check every row against the template's rules and list what is still wrong."""
from dataclasses import dataclass, field

REQUIRED_MISSING = "required"          # a strictly required column is empty -> must fix
INVALID = "invalid"                    # a value is not in the template's suggested list -> check (the lists are approximate)
CONDITIONAL_MISSING = "conditional"    # a conditionally required column is empty -> check, may not apply

# Amazon parent listings are only containers for their variations: they carry no product id.
PARENT_EXEMPT_LABELS = ("Product Id Type", "Product Id")

SEVERITY_ORDER = {REQUIRED_MISSING: 0, INVALID: 1, CONDITIONAL_MISSING: 2}
BLOCKING = (REQUIRED_MISSING,)


@dataclass
class Issue:
    col: object
    severity: str
    rows: list = field(default_factory=list)       # template row numbers affected
    examples: list = field(default_factory=list)   # offending values, for "invalid"

    @property
    def message(self) -> str:
        if self.severity == INVALID:
            return "Not in the template's dropdown list (check it): " + ", ".join(f"'{e}'" for e in self.examples)
        if self.severity == REQUIRED_MISSING:
            return "Required column is empty"
        return "Conditionally required column is empty (check whether it applies)"


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def validate(info, rows: list) -> list:
    """Return issues, most serious first. `rows` is the list of {column index: value} to be written."""
    issues = []
    parentage = next((c.index for c in info.columns if c.label == "Parentage Level"), None)
    is_parent = [parentage is not None and _text(r.get(parentage)).lower() == "parent" for r in rows]
    for col in info.columns:
        values = [_text(r.get(col.index)) for r in rows]
        if col.must_address:
            skip_parents = col.label in PARENT_EXEMPT_LABELS
            empty = [info.data_row + i for i, v in enumerate(values)
                     if not v and not (skip_parents and is_parent[i])]
            if empty:
                sev = REQUIRED_MISSING if col.required else CONDITIONAL_MISSING
                issues.append(Issue(col, sev, empty))
        if col.allowed:
            allowed = {a.lower() for a in col.allowed}
            bad = [(info.data_row + i, v) for i, v in enumerate(values) if v and v.lower() not in allowed]
            if bad:
                distinct = list(dict.fromkeys(v for _, v in bad))
                issues.append(Issue(col, INVALID, [r for r, _ in bad], distinct[:5]))
    return sorted(issues, key=lambda i: (SEVERITY_ORDER[i.severity], i.col.index))


def blocking(issues) -> list:
    """Issues that must be fixed before the file is ready.

    Dropdown mismatches and conditionally required columns are 'check this' items: the dropdown lists
    read from the template are approximate (a file Amazon accepts trips a few of them), and a
    conditional column may legitimately not apply.
    """
    return [i for i in issues if i.severity in BLOCKING]
