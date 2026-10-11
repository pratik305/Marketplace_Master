"""AI review of the finished file against the template's own rules (and, clearly labelled, general knowledge).

Claude is given the template's rule text (the Data Definitions descriptions and the Instructions sheet), the
allowed values, per-column statistics of the rows about to be written, and a few sample rows. It returns
findings; each says where its rule comes from, so nothing is presented as law that the template did not say.
This is a second pair of eyes, not a guarantee: Amazon's own upload check is the final judge.
"""
import json
import re
from collections import Counter
from dataclasses import dataclass, field

from src.ai import AIUnavailable, _ask, _json_from, plain_error

MAX_INSTRUCTIONS_CHARS = 3500
MAX_FINDINGS = 20
MAX_TOKENS = 8000          # a long review must not be cut off mid-finding
SEVERITIES = ("high", "medium", "low")
SOURCES = ("template", "general")


@dataclass
class Finding:
    column: str                 # template column label ("" when the finding is about the file as a whole)
    severity: str               # high / medium / low
    issue: str
    suggestion: str = ""
    rule: str = ""              # the template text the finding relies on, when there is one
    source: str = "template"    # "template" or "general" (Claude's general knowledge: verify it)


@dataclass
class Review:
    findings: list = field(default_factory=list)
    summary: str = ""


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def build_context(info, rows: list) -> dict:
    """Everything Claude gets to see: rules, per-column statistics and sample rows. Kept compact."""
    n = len(rows)
    parentage = next((c.index for c in info.columns if c.label == "Parentage Level"), None)
    is_parent = [parentage is not None and _text(r.get(parentage)).lower() == "parent" for r in rows]
    columns = []
    for col in info.columns:
        vals = [_text(r.get(col.index)) for r in rows]
        filled = [v for v in vals if v]
        if not filled and not col.must_address:
            continue
        top = Counter(filled).most_common(5)
        entry = {"col": col.label, "letter": col.letter, "need": col.requirement,
                 "rule": col.description[:220], "filled": len(filled), "empty": n - len(filled),
                 "distinct": len(set(filled)), "top_values": [f"{v[:40]} x{c}" for v, c in top]}
        if col.allowed:
            entry["allowed"] = (col.allowed[:12] + [f"... {len(col.allowed)} in total"]
                                if len(col.allowed) > 12 else col.allowed)
        columns.append(entry)
    parents = [i for i, p in enumerate(is_parent) if p][:1]
    children = [i for i, p in enumerate(is_parent) if not p][:4]
    samples = [{c.label: _text(rows[i].get(c.index))[:70] for c in info.columns if _text(rows[i].get(c.index))}
               for i in parents + children]
    instructions = " ".join(info.instructions)[:MAX_INSTRUCTIONS_CHARS]
    return {"rows": n, "parent_rows": sum(is_parent), "child_rows": n - sum(is_parent),
            "instructions": instructions, "columns": columns, "sample_rows": samples}


def _prompt(ctx: dict) -> str:
    return (
        "You are reviewing a filled Amazon India jewellery listing file before upload. Below are the template's own "
        "rules (its instructions and per-column rule text), statistics about the values that will be written, and a "
        "few sample rows (the first is a parent row, the rest are children).\n\n"
        "Find problems a careful listing reviewer would catch: values that contradict the template's rule text or "
        "allowed values; required or conditionally required columns that are empty or filled with placeholders; "
        "inconsistent values across fields (for example metal stamp vs metal type, weights, prices vs MRP, size vs "
        "variation theme); suspicious or repeated values; missing compliance details that the template or Indian "
        "e-commerce practice expects (manufacturer / importer / packer details, country of origin, HSN, net weight).\n\n"
        "Rules for you: (1) Use only the information below; never invent data. (2) Every finding must say where it "
        "comes from: source \"template\" with a short quote of the template text in \"rule\", or source \"general\" "
        "when it is your general knowledge of marketplace or Indian regulations, which the user must verify. "
        "(3) Do not report something fine. If nothing is wrong, return an empty list. (4) Rank by severity: high = "
        "likely to make Amazon reject or the listing be non-compliant, medium = likely quality or consistency "
        "problem, low = minor. (5) At most %d findings, the most important first; keep every text field under 200 characters.\n\n"
        "Reply with JSON only: {\"summary\": \"<one or two sentences>\", \"findings\": [{\"column\": \"<template "
        "column label or empty>\", \"severity\": \"high|medium|low\", \"issue\": \"<what is wrong>\", "
        "\"suggestion\": \"<what to do>\", \"rule\": \"<quoted template text or empty>\", \"source\": "
        "\"template|general\"}]}\n\nFILE (JSON):\n" % MAX_FINDINGS
        + json.dumps(ctx, ensure_ascii=False))


def _salvage(text: str) -> dict:
    """Recover what we can from a reply that is not valid JSON, e.g. one cut off mid-finding.

    Keeps the summary and every finding object that is complete.
    """
    decoder = json.JSONDecoder()
    summary = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    start = re.search(r'"findings"\s*:\s*\[', text)
    found, pos = [], start.end() if start else len(text)
    while pos < len(text):
        brace = text.find("{", pos)
        if brace < 0:
            break
        try:
            obj, pos = decoder.raw_decode(text, brace)
        except ValueError:
            break                                    # the last, unfinished object
        if isinstance(obj, dict):
            found.append(obj)
    if not found and not summary:
        raise ValueError("no usable review in the reply")
    return {"summary": json.loads('"%s"' % summary.group(1)) if summary else "", "findings": found}


def parse_review(text: str) -> Review:
    try:
        data = _json_from(text)
    except ValueError:                               # includes JSONDecodeError
        data = _salvage(text)
    findings = []
    for f in data.get("findings", [])[:MAX_FINDINGS]:
        try:
            severity = str(f["severity"]).lower()
            issue = str(f["issue"]).strip()
        except (KeyError, TypeError):
            continue
        if severity not in SEVERITIES or not issue:
            continue
        source = str(f.get("source", "template")).lower()
        findings.append(Finding(column=str(f.get("column", "")).strip(), severity=severity, issue=issue,
                                suggestion=str(f.get("suggestion", "")).strip(),
                                rule=str(f.get("rule", "")).strip(),
                                source=source if source in SOURCES else "general"))
    findings.sort(key=lambda f: SEVERITIES.index(f.severity))
    return Review(findings=findings, summary=str(data.get("summary", "")).strip())


def run_review(client, info, rows: list) -> Review:
    """Review the rows that are about to be written. Raises AIUnavailable with a plain message on failure."""
    if client is None:
        raise AIUnavailable("No API key found. Add ANTHROPIC_API_KEY to a local .env file to use the AI review.")
    try:
        return parse_review(_ask(client, _prompt(build_context(info, rows)), max_tokens=MAX_TOKENS))
    except AIUnavailable:
        raise
    except Exception as exc:
        raise AIUnavailable(plain_error(exc, "AI review") + " The checks on the previous step still apply.") from exc


def fingerprint(rows: list) -> str:
    """A short fingerprint of the rows, to tell when a stored review no longer matches the data."""
    import hashlib
    h = hashlib.sha1()
    for r in rows:
        h.update(repr(sorted(r.items())).encode("utf-8"))
    return h.hexdigest()[:12]
