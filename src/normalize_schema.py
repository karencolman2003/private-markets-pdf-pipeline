from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict

from utils import EXTRACTED_DIR, NORMALIZED_DIR, REFERENCE_DIR, ensure_project_dirs, read_json, save_dataframe


class FundRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_name: str | None = None
    source_file: str
    report_date: str | None = None
    page_number: int | None = None
    fund_name: str | None = None
    vintage_year: int | None = None
    committed_capital: float | None = None
    contributed_capital: float | None = None
    distributed_capital: float | None = None
    nav: float | None = None
    tvpi: float | None = None
    dpi: float | None = None
    irr: float | None = None
    currency: str = "USD"
    raw_row_text: str
    extraction_method: str
    confidence_flag: str = "review"
    notes: str = ""


BAD_FUND_NAMES = {
    "contents",
    "program overview",
    "market environment",
    "key initiatives",
    "investment section",
    "private equity",
    "beliefs",
    "investment",
    "role",
    "key metrics",
}


def is_likely_record(row: dict) -> bool:
    metric_fields = [
        "committed_capital",
        "contributed_capital",
        "distributed_capital",
        "nav",
        "tvpi",
        "dpi",
        "irr",
    ]
    if not any(pd.notna(row.get(field)) for field in metric_fields):
        return False

    fund_name = str(row.get("fund_name") or "").strip()
    if not fund_name:
        return False
    lowered = fund_name.lower()
    if lowered in BAD_FUND_NAMES:
        return False
    if lowered in {"•", "-", "--"}:
        return False
    if not any(char.isalpha() for char in fund_name):
        return False

    raw_row_text = str(row.get("raw_row_text") or "")
    if "Agenda Item" in raw_row_text or "Page " in raw_row_text:
        return False

    if str(row.get("source_file")) == "annual-investment-report-fy-2024.pdf":
        page_number = row.get("page_number")
        if pd.isna(page_number) or int(page_number) < 300:
            return False

    return True


def load_source_lookup() -> dict[str, str]:
    inventory_path = REFERENCE_DIR / "pdf_inventory.csv"
    if not inventory_path.exists():
        return {}
    inventory = pd.read_csv(inventory_path)
    lookup: dict[str, str] = {}
    for _, row in inventory.dropna(subset=["local_path"]).iterrows():
        filename = Path(str(row["local_path"])).name
        lookup[filename] = str(row["source_name"])
    return lookup


def normalize_records() -> pd.DataFrame:
    ensure_project_dirs()
    parsed_path = EXTRACTED_DIR / "parsed_candidates.csv"
    if not parsed_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(parsed_path)
    df = df[df.apply(lambda row: is_likely_record(row.to_dict()), axis=1)].copy()
    source_lookup = load_source_lookup()
    records: list[dict] = []
    for row in df.to_dict(orient="records"):
        cleaned_row = {
            key: (None if isinstance(value, float) and math.isnan(value) else value)
            for key, value in row.items()
        }
        row = cleaned_row
        row["notes"] = row.get("notes") or ""
        row["confidence_flag"] = row.get("confidence_flag") or "review"
        row["source_name"] = source_lookup.get(str(row["source_file"]), str(row["source_file"]))
        record = FundRecord(**row)
        records.append(record.model_dump())
    normalized = pd.DataFrame(records)
    if not normalized.empty:
        save_dataframe(normalized, NORMALIZED_DIR / "fund_records.csv")
        save_dataframe(normalized.head(100), Path("outputs/samples/normalized_sample.csv"))
    return normalized


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Normalize parsed candidate rows into the standard fund schema.")
    parser.parse_args(args=args)
    df = normalize_records()
    print(f"Normalized {len(df)} records")


if __name__ == "__main__":
    main()
