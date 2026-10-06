"""Read the master product sheet (.xlsx) into a table of values."""
import io

import openpyxl
import pandas as pd


class MasterError(Exception):
    """Raised with a plain message when the master can't be read."""


def read_master(data: bytes) -> pd.DataFrame:
    try:
        ws = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True).worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
    except Exception as exc:
        raise MasterError(f"The master file could not be opened: {exc}") from exc
    if len(rows) < 2:
        raise MasterError("The master sheet has no rows.")
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    keep = [i for i, h in enumerate(header) if h]
    names = [header[i] for i in keep]
    body = [[r[i] if i < len(r) else None for i in keep] for r in rows[1:]]
    body = [r for r in body if any(v not in (None, "") for v in r)]
    if not body:
        raise MasterError("The master sheet has no rows.")
    return pd.DataFrame(body, columns=names, dtype=object)
