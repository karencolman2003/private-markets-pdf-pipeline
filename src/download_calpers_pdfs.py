from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from utils import DOCS_DIR, LOGS_DIR, RAW_PDF_DIR, REFERENCE_DIR, ensure_project_dirs, safe_slug, write_json


CALPERS_SOURCES = [
    {
        "source_name": "CalPERS Private Equity Program Fund Performance",
        "category": "fund_performance_page",
        "url": "https://www.calpers.ca.gov/investments/about-investment-office/investment-organization/pep-fund-performance",
        "filename": "calpers_private_equity_program_fund_performance_page.html",
        "manual_steps": "Open the page in a browser and look for linked PDF or print/download content related to fund performance.",
    },
    {
        "source_name": "CalPERS Private Equity Program Fund Performance Print",
        "category": "fund_performance_print",
        "url": "https://www.calpers.ca.gov/investments/about-investment-office/investment-organization/pep-fund-performance-print",
        "filename": "calpers_private_equity_program_fund_performance_print.html",
        "manual_steps": "Open the print page and save the relevant PDF or print content if direct downloads are blocked.",
    },
    {
        "source_name": "CalPERS June 2024 Private Equity Item 05B-01-A",
        "category": "annual_program_review",
        "url": "https://www.calpers.ca.gov/documents/202406-invest-item05b-01-a/download",
        "filename": "202406-invest-item05b-01-a.pdf",
        "manual_steps": "If blocked, paste the URL into a browser and use the site download button to save the PDF into data/raw_pdfs/.",
    },
    {
        "source_name": "CalPERS June 2025 Private Equity Item 06C-01",
        "category": "annual_program_review",
        "url": "https://www.calpers.ca.gov/documents/202506-invest-agenda-item06c-01/download?inline=",
        "filename": "202506-invest-agenda-item06c-01.pdf",
        "manual_steps": "If blocked, open the agenda item in a browser and save the PDF manually into data/raw_pdfs/.",
    },
    {
        "source_name": "CalPERS 2023-24 Annual Investment Report",
        "category": "investment_reporting",
        "url": "https://www.calpers.ca.gov/documents/annual-investment-report-fy-2024/download?inline",
        "filename": "annual-investment-report-fy-2024.pdf",
        "manual_steps": "If blocked, open the Investment and Financial Reports page and download the 2023-24 Annual Investment Report into data/raw_pdfs/.",
    },
    {
        "source_name": "CalPERS Investment and Financial Reports Page",
        "category": "reports_landing_page",
        "url": "https://www.calpers.ca.gov/investments/about-investment-office/investment-financial-reports",
        "filename": "calpers_investment_financial_reports_page.html",
        "manual_steps": "Open the page and identify private-equity-related PDFs to download manually if automation fails.",
    },
]


@dataclass
class DownloadResult:
    source_name: str
    category: str
    url: str
    local_path: str | None
    status: str
    content_type: str | None
    http_status: int | None
    notes: str
    manual_steps: str


def fetch_url(url: str, timeout: int = 60) -> requests.Response:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; portfolio-project-bot/1.0)",
        "Accept": "application/pdf,text/html,application/xhtml+xml",
    }
    response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response


def save_response_content(response: requests.Response, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(response.content)


def download_sources(limit: int | None = None) -> list[DownloadResult]:
    ensure_project_dirs()
    selected_sources = CALPERS_SOURCES[:limit] if limit else CALPERS_SOURCES
    results: list[DownloadResult] = []
    for source in selected_sources:
        local_path: Path | None = None
        status = "failed"
        notes = ""
        content_type = None
        http_status = None
        try:
            response = fetch_url(source["url"])
            content_type = response.headers.get("Content-Type", "")
            http_status = response.status_code
            suffix = ".pdf" if "pdf" in content_type.lower() or source["filename"].endswith(".pdf") else ".html"
            filename = source["filename"]
            if not filename.endswith(suffix):
                filename = f"{safe_slug(source['source_name'])}{suffix}"
            local_path = RAW_PDF_DIR / filename
            save_response_content(response, local_path)
            status = "downloaded"
            notes = "Downloaded successfully."
        except Exception as exc:
            status = "manual_download_needed"
            notes = f"Automatic download failed: {exc}"
        results.append(
            DownloadResult(
                source_name=source["source_name"],
                category=source["category"],
                url=source["url"],
                local_path=str(local_path) if local_path else None,
                status=status,
                content_type=content_type,
                http_status=http_status,
                notes=notes,
                manual_steps=source["manual_steps"],
            )
        )
    return results


def write_inventory(results: list[DownloadResult]) -> None:
    records = [asdict(result) for result in results]
    df = pd.DataFrame(records)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(REFERENCE_DIR / "pdf_inventory.csv", index=False)
    write_json(LOGS_DIR / "download_log.json", records)

    lines = [
        "# Source Inventory",
        "",
        "This inventory is generated from `src/download_calpers_pdfs.py`.",
        "",
        "| Source | Category | URL | Status | Local Path | Notes | Manual Steps |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| {record['source_name']} | {record['category']} | {record['url']} | "
            f"{record['status']} | {record['local_path'] or ''} | {record['notes']} | {record['manual_steps']} |"
        )
    (DOCS_DIR / "source_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download a small starter set of public CalPERS PDFs.")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for the number of starter URLs.")
    parsed = parser.parse_args(args=args)
    results = download_sources(limit=parsed.limit)
    write_inventory(results)
    downloaded = sum(1 for result in results if result.status == "downloaded")
    print(f"Completed download pass. Successful files: {downloaded}/{len(results)}")


if __name__ == "__main__":
    main()
