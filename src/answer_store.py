"""Remember answers between runs, so the second run of a template needs almost no questions.

Answers are saved to a local JSON file (git-ignored, because it holds business details) keyed by the
template column's attribute key, which stays the same from one download of the template to the next.
"""
import json
import os
from pathlib import Path

from src.questions import CONST, LOOKUP, SKIP, Answer

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "answers" / "saved_answers.json"


def store_path() -> Path:
    return Path(os.environ.get("ANSWERS_FILE") or DEFAULT_PATH)


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_answers(tpl, answers: dict, path=None) -> int:
    """Save every real answer (not skipped ones). Returns how many were written."""
    path = Path(path) if path else store_path()
    data = _read(path)
    by_index = {c.index: c for c in tpl.columns}
    count = 0
    for idx, a in answers.items():
        col = by_index.get(idx)
        if col is None or a.mode == SKIP or not col.key:
            continue
        entry = {"label": col.label, "mode": a.mode}
        if a.mode == CONST:
            entry["value"] = a.value
        else:
            entry.update(by=a.by, table=a.table)
        data[col.key] = entry
        count += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return count


def load_answers(tpl, path=None) -> dict:
    """Saved answers for the columns of this template: {column index: Answer}."""
    data = _read(Path(path) if path else store_path())
    out = {}
    for col in tpl.columns:
        e = data.get(col.key)
        if not e or col.index in out:
            continue
        if e.get("mode") == CONST and e.get("value") not in (None, ""):
            out[col.index] = Answer(CONST, value=e["value"])
        elif e.get("mode") == LOOKUP and e.get("by") and e.get("table"):
            out[col.index] = Answer(LOOKUP, by=e["by"], table=dict(e["table"]))
    return out


def forget_all(path=None):
    p = Path(path) if path else store_path()
    if p.exists():
        p.unlink()
