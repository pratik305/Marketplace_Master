"""Slice 1: the readers understand the real sample files (skipped if sample/ is absent)."""
from pathlib import Path

import pytest

from src.master_reader import MasterError, read_master
from src.template_reader import TemplateError, read_template

SAMPLE = Path(__file__).resolve().parent.parent / "sample"
TEMPLATE = SAMPLE / "RING (6).xlsm"
MASTER = SAMPLE / "Master_Arias_Ring_LOT3_v2.xlsx"
have_samples = TEMPLATE.exists() and MASTER.exists()


@pytest.mark.skipif(not have_samples, reason="sample/ files not present")
def test_template_structure():
    info = read_template(TEMPLATE.read_bytes())
    assert (info.label_row, info.key_row, info.data_row) == (4, 5, 8)
    assert len(info.columns) == 383
    assert len(info.required_columns()) == 9
    assert len(info.must_address()) == 130
    brand = next(c for c in info.columns if c.label == "Brand Name")
    assert brand.required
    sku = info.columns[0]
    assert (sku.letter, sku.label) == ("A", "SKU")


@pytest.mark.skipif(not have_samples, reason="sample/ files not present")
def test_master_rows():
    df = read_master(MASTER.read_bytes())
    assert len(df) == 608
    assert "Sku Code" in df.columns


def test_bad_files_give_plain_errors():
    with pytest.raises(TemplateError):
        read_template(b"not an excel file")
    with pytest.raises(MasterError):
        read_master(b"not an excel file")
