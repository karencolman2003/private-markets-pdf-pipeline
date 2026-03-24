from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from utils import EXTRACTED_DIR, RAW_PDF_DIR, ensure_project_dirs, page_keyword_score, read_json, save_dataframe, write_json

try:
    import camelot
except Exception:  # pragma: no cover
    camelot = None


def candidate_pages_for_pdf(pdf_path: Path, fallback: str = "all", max_pages: int = 25) -> str:
    text_payload = read_json(EXTRACTED_DIR / f"{pdf_path.stem}_text.json", default={"pages": []})
    def is_candidate(page: dict) -> bool:
        text = str(page.get("text", ""))
        score = max(int(page.get("keyword_score", 0)), page_keyword_score(text))
        if pdf_path.stem == "annual-investment-report-fy-2024":
            lowered = text.lower()
            return "private equity" in lowered and (
                "security name" in lowered or "book value" in lowered or "market value" in lowered
            )
        return score >= 2

    candidate_pages = [
        str(page["page_number"])
        for page in text_payload.get("pages", [])
        if is_candidate(page)
    ]
    if not candidate_pages:
        return fallback
    return ",".join(candidate_pages[:max_pages])


def extract_tables_from_pdf(pdf_path: Path, pages: str | None = None) -> dict:
    results: list[dict] = []
    if camelot is None:
        payload = {
            "source_file": pdf_path.name,
            "tables": [],
            "notes": "Camelot import failed. Install system dependencies and camelot extras for full table extraction.",
        }
        write_json(EXTRACTED_DIR / f"{pdf_path.stem}_tables.json", payload)
        return payload

    selected_pages = pages or candidate_pages_for_pdf(pdf_path)
    for flavor in ("lattice", "stream"):
        try:
            tables = camelot.read_pdf(str(pdf_path), pages=selected_pages, flavor=flavor)
        except Exception as exc:
            results.append(
                {
                    "flavor": flavor,
                    "page": None,
                    "table_index": None,
                    "accuracy": None,
                    "whitespace": None,
                    "shape": None,
                    "records": [],
                    "error": str(exc),
                }
            )
            continue

        for idx, table in enumerate(tables):
            df = table.df.fillna("")
            csv_path = EXTRACTED_DIR / f"{pdf_path.stem}_{flavor}_table_{idx}.csv"
            save_dataframe(df, csv_path)
            parsing_report = getattr(table, "parsing_report", {}) or {}
            results.append(
                {
                    "flavor": flavor,
                    "page": parsing_report.get("page"),
                    "table_index": idx,
                    "accuracy": parsing_report.get("accuracy"),
                    "whitespace": parsing_report.get("whitespace"),
                    "shape": list(df.shape),
                    "records": df.to_dict(orient="records"),
                    "csv_path": str(csv_path),
                }
            )

    payload = {"source_file": pdf_path.name, "tables": results}
    write_json(EXTRACTED_DIR / f"{pdf_path.stem}_tables.json", payload)
    return payload


def combine_table_summaries(pdf_paths: list[Path]) -> pd.DataFrame:
    summary_rows: list[dict[str, object]] = []
    for pdf_path in pdf_paths:
        payload = extract_tables_from_pdf(pdf_path)
        for table in payload.get("tables", []):
            summary_rows.append(
                {
                    "source_file": pdf_path.name,
                    "flavor": table.get("flavor"),
                    "page": table.get("page"),
                    "table_index": table.get("table_index"),
                    "accuracy": table.get("accuracy"),
                    "whitespace": table.get("whitespace"),
                    "shape": table.get("shape"),
                    "csv_path": table.get("csv_path"),
                    "error": table.get("error"),
                }
            )
    df = pd.DataFrame(summary_rows)
    if not df.empty:
        save_dataframe(df, EXTRACTED_DIR / "table_extraction_summary.csv")
    return df


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract tables from local PDFs with Camelot.")
    parser.add_argument("--pdf", type=str, default=None, help="Optional single PDF path.")
    parsed = parser.parse_args(args=args)
    ensure_project_dirs()
    pdf_paths = [Path(parsed.pdf)] if parsed.pdf else sorted(RAW_PDF_DIR.glob("*.pdf"))
    df = combine_table_summaries(pdf_paths)
    print(f"Table extraction finished for {len(pdf_paths)} PDFs. Summary rows: {len(df)}")


if __name__ == "__main__":
    main()
