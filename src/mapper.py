"""Match master columns to template columns."""
import re
from collections import defaultdict


def _norm(name: str) -> str:
    """Lower-case, drop pandas-style '.1' suffixes and punctuation, so near-identical names match."""
    name = re.sub(r"\.\d+$", "", str(name).strip())
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def name_match(template_columns, master_columns) -> dict:
    """Return {template column index: master column name} for columns whose names match.

    Repeated names (e.g. four 'Bullet Point' columns) are paired in order of appearance.
    """
    pool = defaultdict(list)
    for m in master_columns:
        pool[_norm(m)].append(m)
    used = defaultdict(int)
    mapping = {}
    for col in template_columns:
        key = _norm(col.label)
        n = used[key]
        if key and n < len(pool.get(key, [])):
            mapping[col.index] = pool[key][n]
            used[key] += 1
    return mapping
