from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from utils import RAW_PDF_DIR, REFERENCE_DIR, ensure_project_dirs


def discover_pdfs(pdf_dir: Path = RAW_PDF_DIR) -> pd.DataFrame:
    ensure_project_dirs()
    records: list[dict[str, object]] = []
    for path in sorted(pdf_dir.glob("*.pdf")):
        records.append(
            {
                "source_file": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
        )
    df = pd.DataFrame(records)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(REFERENCE_DIR / "local_pdf_manifest.csv", index=False)
    return df


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Discover PDFs in data/raw_pdfs.")
    parser.parse_args(args=args)
    df = discover_pdfs()
    print(f"Discovered {len(df)} PDF files in {RAW_PDF_DIR}")


if __name__ == "__main__":
    main()

