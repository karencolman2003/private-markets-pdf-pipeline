from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

from utils import NORMALIZED_DIR, ensure_project_dirs, save_dataframe, write_json

PIPELINE_STEPS = [
    "download_calpers_pdfs.py",
    "discover_pdfs.py",
    "extract_tables.py",
    "extract_text.py",
    "parse_metrics.py",
    "normalize_schema.py",
    "validate_records.py",
]


def run_all_steps() -> None:
    src_dir = Path(__file__).resolve().parent
    for step in PIPELINE_STEPS:
        subprocess.run([sys.executable, str(src_dir / step)], check=True)


def build_dashboard_data() -> tuple[pd.DataFrame, dict]:
    ensure_project_dirs()
    source_path = NORMALIZED_DIR / "fund_records_validated.csv"
    if not source_path.exists():
        fallback = NORMALIZED_DIR / "fund_records.csv"
        source_path = fallback if fallback.exists() else source_path
    if not source_path.exists():
        return pd.DataFrame(), {}

    df = pd.read_csv(source_path)
    save_dataframe(df, NORMALIZED_DIR / "dashboard_records.csv")
    summary = {
        "record_count": int(len(df)),
        "source_count": int(df["source_file"].nunique()) if "source_file" in df else 0,
        "fund_count": int(df["fund_name"].dropna().nunique()) if "fund_name" in df else 0,
        "missingness": df.isna().mean().round(4).to_dict(),
    }
    write_json(NORMALIZED_DIR / "dashboard_summary.json", summary)
    return df, summary


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build dashboard-ready datasets and optionally run the full pipeline.")
    parser.add_argument("--run-all", action="store_true", help="Run the full pipeline before building outputs.")
    parsed = parser.parse_args(args=args)
    if parsed.run_all:
        run_all_steps()
    df, summary = build_dashboard_data()
    print(f"Prepared dashboard data for {len(df)} records. Sources: {summary.get('source_count', 0)}")


if __name__ == "__main__":
    main()

