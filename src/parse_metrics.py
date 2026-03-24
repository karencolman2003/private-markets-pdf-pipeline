from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber

from utils import (
    EXTRACTED_DIR,
    RAW_PDF_DIR,
    coerce_money,
    coerce_multiple,
    coerce_percent,
    ensure_project_dirs,
    first_non_null,
    normalize_whitespace,
    page_keyword_score,
    parse_date_from_text,
    plausible_vintage_year,
    read_json,
    save_dataframe,
)

MONEY_LABELS = {
    "committed_capital": ["commit", "commitment", "committed"],
    "contributed_capital": ["contribut", "paid in", "paid-in", "invested"],
    "distributed_capital": ["distribut", "returned"],
    "nav": ["nav", "residual value", "fair value", "ending value"],
}

MULTIPLE_LABELS = {
    "tvpi": ["tvpi", "total value", "t.v.p.i"],
    "dpi": ["dpi", "distributed to paid in", "d.p.i"],
}

PERCENT_LABELS = {
    "irr": ["irr", "internal rate", "net irr", "gross irr"],
}


def page_is_candidate(text: str, source_file: str) -> bool:
    lowered = text.lower()
    if source_file == "annual-investment-report-fy-2024.pdf":
        return "private equity" in lowered and (
            "security name" in lowered or "book value" in lowered or "market value" in lowered
        )
    return page_keyword_score(text) >= 2


def parse_table_record(
    row: dict[str, Any],
    source_file: str,
    page_number: int | None,
    extraction_method: str,
) -> dict[str, Any]:
    values = [normalize_whitespace(str(value)) for value in row.values() if str(value).strip()]
    raw_row_text = " | ".join(values)
    normalized_row = {
        "source_file": source_file,
        "page_number": page_number,
        "raw_row_text": raw_row_text,
        "extraction_method": extraction_method,
        "report_date": parse_date_from_text(raw_row_text),
        "fund_name": first_non_null(values[:2]),
        "vintage_year": None,
        "committed_capital": None,
        "contributed_capital": None,
        "distributed_capital": None,
        "nav": None,
        "tvpi": None,
        "dpi": None,
        "irr": None,
        "currency": "USD",
        "confidence_flag": "medium",
        "notes": "",
    }
    for value in values:
        if normalized_row["vintage_year"] is None:
            normalized_row["vintage_year"] = plausible_vintage_year(value)
        if normalized_row["tvpi"] is None and ("x" in value.lower() or "tvpi" in value.lower()):
            normalized_row["tvpi"] = coerce_multiple(value)
        if normalized_row["dpi"] is None and "dpi" in value.lower():
            normalized_row["dpi"] = coerce_multiple(value)
        if normalized_row["irr"] is None and "%" in value:
            normalized_row["irr"] = coerce_percent(value)

    numeric_candidates = [coerce_money(value) for value in values]
    numeric_candidates = [value for value in numeric_candidates if value is not None and value >= 0]
    if len(numeric_candidates) >= 4:
        normalized_row["committed_capital"] = numeric_candidates[0] if len(numeric_candidates) > 0 else None
        normalized_row["contributed_capital"] = numeric_candidates[1] if len(numeric_candidates) > 1 else None
        normalized_row["distributed_capital"] = numeric_candidates[2] if len(numeric_candidates) > 2 else None
        normalized_row["nav"] = numeric_candidates[3] if len(numeric_candidates) > 3 else None
    elif len(numeric_candidates) == 1:
        normalized_row["nav"] = numeric_candidates[0]
        normalized_row["notes"] = "single_money_value_mapped_to_nav"
    elif len(numeric_candidates) in {2, 3}:
        normalized_row["notes"] = "ambiguous_money_columns_not_mapped"
    return normalized_row


def parse_text_line(line: str, source_file: str, page_number: int) -> dict[str, Any] | None:
    text = normalize_whitespace(line)
    if not text:
        return None
    if source_file == "annual-investment-report-fy-2024.pdf":
        if text in {
            "CalPERS 2023-2024 Annual Investment Report",
            "Private Equity",
            "Security Name Book Value Market Value",
        }:
            return None
        if text.startswith("Page "):
            return None
        annual_match = re.match(
            r"^(?P<fund>.+?)\s(?P<book>\d{1,3}(?:,\d{3})+|0)\s(?P<market>\d{1,3}(?:,\d{3})+|0)$",
            text,
        )
        if not annual_match:
            return None
        fund_name = annual_match.group("fund").strip()
        if fund_name.upper() == "TOTAL":
            return None
        return {
            "source_file": source_file,
            "page_number": page_number,
            "raw_row_text": text,
            "extraction_method": "pdfplumber_text",
            "report_date": "2024-06-30",
            "fund_name": fund_name,
            "vintage_year": plausible_vintage_year(fund_name),
            "committed_capital": None,
            "contributed_capital": None,
            "distributed_capital": None,
            "nav": coerce_money(annual_match.group("market")),
            "tvpi": None,
            "dpi": None,
            "irr": None,
            "currency": "USD",
            "confidence_flag": "high",
            "notes": "annual_report_market_value_mapped_to_nav",
        }
    if len(text.split()) < 3:
        return None
    if any(token in text.lower() for token in ["agenda item", "page ", "private equity annual program review as of"]):
        return None
    numbers = re.findall(r"[$(]?\d[\d,]*(?:\.\d+)?%?x?[)]?", text)
    if len(numbers) < 2:
        return None

    fund_name = re.split(r"\s{2,}|\t|\$", text)[0].strip()

    row = {
        "source_file": source_file,
        "page_number": page_number,
        "raw_row_text": text,
        "extraction_method": "pdfplumber_text",
        "report_date": parse_date_from_text(text),
        "fund_name": fund_name,
        "vintage_year": plausible_vintage_year(text),
        "committed_capital": None,
        "contributed_capital": None,
        "distributed_capital": None,
        "nav": None,
        "tvpi": None,
        "dpi": None,
        "irr": None,
        "currency": "USD",
        "confidence_flag": "low",
        "notes": "",
    }

    money_values = [coerce_money(match) for match in numbers if "%" not in match and "x" not in match.lower()]
    multiple_values = [coerce_multiple(match) for match in numbers if "x" in match.lower()]
    percent_values = [coerce_percent(match) for match in numbers if "%" in match]

    if len(money_values) >= 4:
        row["committed_capital"] = money_values[0] if len(money_values) > 0 else None
        row["contributed_capital"] = money_values[1] if len(money_values) > 1 else None
        row["distributed_capital"] = money_values[2] if len(money_values) > 2 else None
        row["nav"] = money_values[3] if len(money_values) > 3 else None
    elif len(money_values) == 1:
        row["nav"] = money_values[0]
        row["notes"] = "single_money_value_mapped_to_nav"
    elif len(money_values) in {2, 3}:
        row["notes"] = "ambiguous_money_columns_not_mapped"
    if multiple_values:
        row["tvpi"] = multiple_values[0]
        row["dpi"] = multiple_values[1] if len(multiple_values) > 1 else None
    if percent_values:
        row["irr"] = percent_values[0]

    has_business_metric = any(
        row[field] is not None
        for field in ["committed_capital", "contributed_capital", "distributed_capital", "nav", "tvpi", "dpi", "irr"]
    )
    if not has_business_metric:
        return None
    return row


def parse_all_candidates(raw_pdf_dir: Path = RAW_PDF_DIR) -> pd.DataFrame:
    ensure_project_dirs()
    parsed_rows: list[dict[str, Any]] = []

    for pdf_path in sorted(raw_pdf_dir.glob("*.pdf")):
        text_payload = read_json(EXTRACTED_DIR / f"{pdf_path.stem}_text.json", default={"pages": []})
        table_payload = read_json(EXTRACTED_DIR / f"{pdf_path.stem}_tables.json", default={"tables": []})
        candidate_page_numbers = {
            int(page.get("page_number"))
            for page in text_payload.get("pages", [])
            if page_is_candidate(str(page.get("text", "")), pdf_path.name)
        }

        for table in table_payload.get("tables", []):
            if pdf_path.name == "annual-investment-report-fy-2024.pdf":
                continue
            if table.get("error"):
                continue
            page_number = int(table["page"]) if table.get("page") else None
            if candidate_page_numbers and page_number and page_number not in candidate_page_numbers:
                continue
            for record in table.get("records", []):
                row = parse_table_record(
                    record,
                    source_file=pdf_path.name,
                    page_number=page_number,
                    extraction_method=f"camelot_{table.get('flavor')}",
                )
                if row["raw_row_text"]:
                    parsed_rows.append(row)

        page_line_lookup: dict[int, list[str]] = {}
        for page in text_payload.get("pages", []):
            page_number = int(page.get("page_number"))
            page_lines = page.get("lines") or re.split(r"\n+", page.get("raw_text", ""))
            page_lines = [normalize_whitespace(line) for line in page_lines if normalize_whitespace(line)]
            if page_lines:
                page_line_lookup[page_number] = page_lines

        missing_pages = sorted(candidate_page_numbers - set(page_line_lookup))
        if missing_pages:
            with pdfplumber.open(pdf_path) as pdf:
                for page_number in missing_pages:
                    raw_text = pdf.pages[page_number - 1].extract_text() or ""
                    lines = [normalize_whitespace(line) for line in raw_text.splitlines() if normalize_whitespace(line)]
                    page_line_lookup[page_number] = lines

        for page_number in sorted(candidate_page_numbers):
            for line in page_line_lookup.get(page_number, []):
                candidate = parse_text_line(line, pdf_path.name, page_number)
                if candidate:
                    parsed_rows.append(candidate)

    df = pd.DataFrame(parsed_rows)
    if not df.empty:
        save_dataframe(df, EXTRACTED_DIR / "parsed_candidates.csv")
    return df


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Parse candidate fund-level metrics from extracted text and tables.")
    parser.parse_args(args=args)
    df = parse_all_candidates()
    print(f"Parsed {len(df)} candidate rows")


if __name__ == "__main__":
    main()
