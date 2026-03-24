from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

from utils import LOGS_DIR, NORMALIZED_DIR, ValidationIssue, ensure_project_dirs, save_dataframe


def validate_records() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_project_dirs()
    path = NORMALIZED_DIR / "fund_records.csv"
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()

    df = pd.read_csv(path)
    issues: list[ValidationIssue] = []
    current_year = datetime.now().year

    for idx, row in df.iterrows():
        row_id = f"{row.get('source_file')}::p{row.get('page_number')}::{idx}"
        notes: list[str] = []

        vintage = row.get("vintage_year")
        if pd.notna(vintage) and not (1980 <= int(vintage) <= current_year + 1):
            issues.append(ValidationIssue(row_id, "warning", "Vintage year outside plausible range"))
            notes.append("vintage_year_out_of_range")

        for field in ["committed_capital", "contributed_capital", "distributed_capital", "nav"]:
            value = row.get(field)
            if pd.notna(value) and float(value) < 0:
                issues.append(ValidationIssue(row_id, "warning", f"{field} is negative"))
                notes.append(f"{field}_negative")

        irr = row.get("irr")
        if pd.notna(irr) and not (-1.0 <= float(irr) <= 5.0):
            issues.append(ValidationIssue(row_id, "review", "IRR outside sanity range"))
            notes.append("irr_outlier")

        for field in ["tvpi", "dpi"]:
            value = row.get(field)
            if pd.notna(value) and float(value) > 10.0:
                issues.append(ValidationIssue(row_id, "review", f"{field} unusually high"))
                notes.append(f"{field}_outlier")

        if pd.isna(row.get("fund_name")) or not str(row.get("fund_name")).strip():
            issues.append(ValidationIssue(row_id, "review", "Missing fund name"))
            notes.append("missing_fund_name")

        existing_notes = str(row.get("notes") or "").strip()
        if existing_notes.lower() == "nan":
            existing_notes = ""
        merged_notes = ", ".join(filter(None, [existing_notes, ";".join(notes)]))
        df.at[idx, "notes"] = merged_notes
        if notes and str(row.get("confidence_flag", "")) == "high":
            df.at[idx, "confidence_flag"] = "review"

    validated_issues = pd.DataFrame([issue.__dict__ for issue in issues])
    save_dataframe(df, NORMALIZED_DIR / "fund_records_validated.csv")
    if not validated_issues.empty:
        save_dataframe(validated_issues, LOGS_DIR / "validation_issues.csv")
    return df, validated_issues


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate normalized fund records and emit issue logs.")
    parser.parse_args(args=args)
    df, issues = validate_records()
    print(f"Validated {len(df)} records with {len(issues)} issues")


if __name__ == "__main__":
    main()
