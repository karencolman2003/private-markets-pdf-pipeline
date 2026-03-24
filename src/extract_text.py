from __future__ import annotations

import argparse
from pathlib import Path

import pdfplumber

from utils import EXTRACTED_DIR, RAW_PDF_DIR, ensure_project_dirs, normalize_whitespace, page_keyword_score, write_json


def extract_pdf_text(pdf_path: Path) -> dict:
    pages: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text = page.extract_text() or ""
            lines = [normalize_whitespace(line) for line in raw_text.splitlines() if normalize_whitespace(line)]
            normalized = normalize_whitespace(raw_text)
            pages.append(
                {
                    "page_number": page.page_number,
                    "keyword_score": page_keyword_score(normalized),
                    "text": normalized,
                    "raw_text": raw_text,
                    "lines": lines,
                    "width": page.width,
                    "height": page.height,
                }
            )
    payload = {"source_file": pdf_path.name, "pages": pages}
    write_json(EXTRACTED_DIR / f"{pdf_path.stem}_text.json", payload)
    return payload


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract page text from local PDFs with pdfplumber.")
    parser.add_argument("--pdf", type=str, default=None, help="Optional single PDF path.")
    parsed = parser.parse_args(args=args)
    ensure_project_dirs()
    pdf_paths = [Path(parsed.pdf)] if parsed.pdf else sorted(RAW_PDF_DIR.glob("*.pdf"))
    for pdf_path in pdf_paths:
        extract_pdf_text(pdf_path)
        print(f"Extracted text from {pdf_path.name}")


if __name__ == "__main__":
    main()
