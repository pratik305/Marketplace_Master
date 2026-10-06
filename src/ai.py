"""Claude API calls: column mapping suggestions (and, later, answer checks).

Everything here degrades gracefully: with no API key or a failed call, callers get an empty
result and a plain-language reason, and the app carries on with name matching only.
"""
import json
import os
import re

MODEL = "claude-sonnet-5-5"   # confirm the current model id in the Claude docs


class AIUnavailable(Exception):
    """Raised with a plain message when Claude can't be used."""


def get_client():
    """Return an Anthropic client, or None when no key is configured."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key)


def _json_from(text: str):
    """Pull the first JSON object out of a model reply, tolerating code fences."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start:end + 1])


def _ask(client, prompt: str, max_tokens: int = 4000) -> str:
    resp = client.messages.create(model=MODEL, max_tokens=max_tokens,
                                  messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def propose_mapping(client, template_columns, master, already: dict) -> dict:
    """Ask Claude which master column fills each still-unmapped template column.

    Returns {template column index: (master column, confidence)}. Only valid, existing
    columns are kept. Raises AIUnavailable with a plain message on any failure.
    """
    if client is None:
        raise AIUnavailable("No API key found. Add ANTHROPIC_API_KEY to a local .env file to use AI mapping.")
    master_cols = [str(c) for c in master.columns]
    samples = {}
    for c in master_cols:
        vals = [str(v) for v in master[c].dropna().unique()[:3]]
        samples[c] = [v[:60] for v in vals]
    targets = [t for t in template_columns if t.index not in already]
    lines = [f'{t.index} | {t.label} | {t.group} | {t.requirement} | {t.description[:80]}' for t in targets]
    prompt = (
        "You map columns of a product master sheet onto an Amazon listing template.\n"
        "MASTER columns with sample values (JSON):\n" + json.dumps(samples, ensure_ascii=False) + "\n\n"
        "TEMPLATE columns not yet mapped, one per line as: index | label | group | requirement | description\n"
        + "\n".join(lines) + "\n\n"
        "For each template column whose meaning clearly matches a master column, give the master column. "
        "Skip template columns with no good match; never guess. A master column may fill more than one "
        "template column if it truly applies. Reply with JSON only, shaped as "
        '{"mapping": {"<template index>": {"master": "<master column>", "confidence": <0..1>}}}.'
    )
    try:
        data = _json_from(_ask(client, prompt))["mapping"]
    except AIUnavailable:
        raise
    except Exception as exc:
        raise AIUnavailable(f"The AI mapping could not be completed ({type(exc).__name__}). "
                            "You can map the columns by hand.") from exc
    valid_idx = {t.index for t in targets}
    result = {}
    for k, v in data.items():
        try:
            idx = int(k)
            col = v["master"]
            conf = float(v.get("confidence", 0.5))
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        if idx in valid_idx and col in master_cols:
            result[idx] = (col, max(0.0, min(1.0, conf)))
    return result


def check_answers(client, col, values: list) -> list:
    """Ask Claude whether each free-text answer is sensible for a template column.

    Returns [(value, ok, reason)]. Raises AIUnavailable with a plain message on failure; callers
    treat that as "could not check" and accept the answer.
    """
    if client is None:
        raise AIUnavailable("No API key found, so answers are checked against the template rules only.")
    prompt = (
        "You are checking values a user typed for one column of an Amazon India jewelry listing template.\n"
        f"Column: {col.label} (group: {col.group}, {col.requirement})\n"
        f"Description: {col.description[:400]}\n"
        f"Example: {col.example[:120]}\n"
        "Values to check (JSON list): " + json.dumps(values, ensure_ascii=False) + "\n"
        "For each value say whether it is a sensible, correctly formatted value for this column. "
        "Be lenient: only reject a value that is clearly wrong for the column (wrong kind of data, "
        "wrong unit, wrong format). Reply with JSON only: "
        '{"results": [{"value": "<value>", "ok": true, "reason": "<short reason if not ok>"}]}'
    )
    try:
        data = _json_from(_ask(client, prompt, max_tokens=1000))["results"]
        return [(str(r["value"]), bool(r["ok"]), str(r.get("reason", ""))) for r in data]
    except Exception as exc:
        raise AIUnavailable(f"The AI answer check could not be completed ({type(exc).__name__}).") from exc
