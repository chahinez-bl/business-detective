"""Regenerates the three synthetic sample files in data/samples (dates are relative to today). Run from backend/:  python scripts/make_samples.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests import synthetic as syn  # noqa: E402

out = Path(__file__).resolve().parents[2] / "data" / "samples"
out.mkdir(parents=True, exist_ok=True)
(out / "sample_a_sales.csv").write_bytes(syn.to_csv_bytes(syn.dataset_a()))
(out / "sample_b_ventes_fr.csv").write_bytes(syn.to_csv_bytes(syn.dataset_b(), sep=";", encoding="cp1252"))
(out / "sample_c_orders.xlsx").write_bytes(syn.to_xlsx_bytes(syn.dataset_c()))
print("Wrote samples to", out)
