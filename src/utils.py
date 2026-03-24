from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_PDF_DIR = DATA_DIR / "raw_pdfs"
EXTRACTED_DIR = DATA_DIR / "extracted"
NORMALIZED_DIR = DATA_DIR / "normalized"
REFERENCE_DIR = DATA_DIR / "reference"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = OUTPUTS_DIR / "logs"
SAMPLES_DIR = OUTPUTS_DIR / "samples"
DOCS_DIR = PROJECT_ROOT / "docs"


def ensure_project_dirs() -> None:
    for path in [
        RAW_PDF_DIR,
        EXTRACTED_DIR,
        NORMALIZED_DIR,
        REFERENCE_DIR,
        LOGS_DIR,
        SAMPLES_DIR,
        OUTPUTS_DIR / "figures",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "document"


def parse_date_from_text(text: str) -> str | None:
    patterns = [
        r"(20\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01]))",
        r"((January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2})",
        r"((January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1)
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%B %Y"):
                try:
                    return datetime.strptime(candidate, fmt).date().isoformat()
                except ValueError:
                    continue
    return None


def coerce_money(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "n/a", "--", "-"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", text.replace(",", ""))
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        number = float(cleaned)
        return -number if negative and number > 0 else number
    except ValueError:
        return None


def coerce_multiple(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("x", "")
    return coerce_money(text)


def coerce_percent(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text or text in {"nan", "none", "null", "n/a", "--", "-"}:
        return None
    number = coerce_money(text.replace("%", ""))
    if number is None:
        return None
    return number / 100.0


def plausible_vintage_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"(19\d{2}|20\d{2})", str(value))
    if not match:
        return None
    year = int(match.group(1))
    current_year = datetime.now().year
    if 1980 <= year <= current_year + 1:
        return year
    return None


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_non_null(values: Iterable[Any]) -> Any | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, float) and pd.isna(value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


@dataclass
class ValidationIssue:
    row_id: str
    severity: str
    message: str


PERFORMANCE_KEYWORDS = [
    "private equity",
    "fund",
    "vintage",
    "nav",
    "irr",
    "tvpi",
    "dpi",
    "distributed",
    "contributed",
    "commitment",
    "book value",
    "market value",
    "security name",
    "performance",
]


def page_keyword_score(text: str) -> int:
    lowered = text.lower()
    return sum(1 for keyword in PERFORMANCE_KEYWORDS if keyword in lowered)
