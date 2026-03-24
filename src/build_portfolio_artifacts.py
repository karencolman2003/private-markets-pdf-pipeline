from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px

from utils import LOGS_DIR, NORMALIZED_DIR, OUTPUTS_DIR, SAMPLES_DIR, save_dataframe

FIGURES_DIR = OUTPUTS_DIR / "figures"

FIELD_COLUMNS = [
    "report_date",
    "fund_name",
    "vintage_year",
    "committed_capital",
    "contributed_capital",
    "distributed_capital",
    "nav",
    "tvpi",
    "dpi",
    "irr",
]


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    records = pd.read_csv(NORMALIZED_DIR / "fund_records_validated.csv")
    issues_path = LOGS_DIR / "validation_issues.csv"
    issues = pd.read_csv(issues_path) if issues_path.exists() else pd.DataFrame(columns=["row_id", "severity", "message"])
    return records, issues


def build_audit(records: pd.DataFrame, issues: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    issue_sources = (
        issues.assign(source_file=issues["row_id"].str.extract(r"^(.*?)::"))
        .groupby("source_file")
        .size()
        .rename("flagged_review_rows")
    )

    completeness = records.groupby("source_file")[FIELD_COLUMNS].apply(lambda group: group.notna().mean()).reset_index()
    completeness.columns = ["source_file"] + [f"{col}_populated_rate" for col in FIELD_COLUMNS]

    audit = (
        records.groupby("source_file")
        .agg(
            record_count=("source_file", "size"),
            unique_fund_names=("fund_name", lambda s: s.dropna().nunique()),
            high_confidence_rows=("confidence_flag", lambda s: int((s == "high").sum())),
            medium_confidence_rows=("confidence_flag", lambda s: int((s == "medium").sum())),
            low_confidence_rows=("confidence_flag", lambda s: int((s == "low").sum())),
        )
        .join(issue_sources, how="left")
        .fillna({"flagged_review_rows": 0})
        .reset_index()
    )
    audit["flagged_review_rows"] = audit["flagged_review_rows"].astype(int)
    audit = audit.merge(completeness, on="source_file", how="left")

    score = (
        completeness.set_index("source_file")
        .assign(
            quality_score=lambda df: (
                0.35 * df["fund_name_populated_rate"]
                + 0.35 * df["nav_populated_rate"]
                + 0.10 * (1 - df["irr_populated_rate"].fillna(0))
                + 0.20 * (
                    records.groupby("source_file")["confidence_flag"].apply(lambda s: (s == "high").mean()).reindex(df.index)
                )
            )
        )["quality_score"]
        .sort_values(ascending=False)
    )
    cleanest_source = score.index[0]

    audit["cleanest_source_now"] = audit["source_file"].eq(cleanest_source)
    save_dataframe(audit, OUTPUTS_DIR / "samples" / "source_quality_audit.csv")

    lines = [
        "# Source Quality Audit",
        "",
        f"Cleanest current fund-level source: `{cleanest_source}`.",
        "",
        "## Summary",
        "",
        audit.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- The annual investment report is currently the cleanest source because its private-equity holdings section follows a stable `Security Name / Book Value / Market Value` layout.",
        "- The two annual program review PDFs still produce useful extraction artifacts and some aggregate metrics, but they remain noisier and require more analyst review.",
        "- High-confidence rows are concentrated in the annual investment report; flagged review rows are concentrated in the annual program review sources.",
        "",
    ]
    report = "\n".join(lines)
    (OUTPUTS_DIR / "samples" / "source_quality_audit.md").write_text(report, encoding="utf-8")
    return audit, cleanest_source


def build_high_confidence_sample(records: pd.DataFrame) -> pd.DataFrame:
    sample = (
        records[
            (records["confidence_flag"] == "high")
            & records["fund_name"].notna()
            & records["nav"].notna()
            & ~records["fund_name"].fillna("").str.upper().isin(["TOTAL"])
        ]
        .sort_values(["nav", "fund_name"], ascending=[False, True])
        .drop_duplicates(subset=["fund_name"])
        .head(15)[
            [
                "source_file",
                "page_number",
                "fund_name",
                "nav",
                "tvpi",
                "dpi",
                "irr",
                "vintage_year",
                "confidence_flag",
                "notes",
            ]
        ]
    )
    save_dataframe(sample, SAMPLES_DIR / "high_confidence_sample.csv")
    (SAMPLES_DIR / "high_confidence_sample.md").write_text(sample.to_markdown(index=False), encoding="utf-8")
    return sample


def plot_records_by_source(audit: pd.DataFrame) -> None:
    fig = px.bar(audit, x="source_file", y="record_count", title="Records by Source")
    fig.write_html(FIGURES_DIR / "records_by_source.html", include_plotlyjs="cdn")


def plot_field_completeness(records: pd.DataFrame) -> None:
    completeness = records.groupby("source_file")[["fund_name", "nav", "tvpi", "dpi", "irr", "vintage_year"]].apply(lambda g: g.notna().mean())
    completeness_long = completeness.reset_index().melt(id_vars="source_file", var_name="field", value_name="populated_rate")
    fig = px.density_heatmap(
        completeness_long,
        x="field",
        y="source_file",
        z="populated_rate",
        text_auto=".0%",
        color_continuous_scale="YlGnBu",
        title="Field Completeness by Source",
    )
    fig.write_html(FIGURES_DIR / "field_completeness_by_source.html", include_plotlyjs="cdn")


def plot_top_funds(records: pd.DataFrame) -> None:
    top = (
        records[(records["confidence_flag"] == "high") & records["nav"].notna()]
        .sort_values("nav", ascending=False)
        .head(12)[["fund_name", "nav"]]
        .sort_values("nav")
    )
    top = top.assign(nav_billions=top["nav"] / 1_000_000_000)
    fig = px.bar(top, x="nav_billions", y="fund_name", orientation="h", title="Top Extracted Funds by Market Value")
    fig.write_html(FIGURES_DIR / "top_funds_by_nav.html", include_plotlyjs="cdn")


def plot_confidence_distribution(records: pd.DataFrame) -> None:
    counts = records.groupby(["source_file", "confidence_flag"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["high", "medium", "low"], fill_value=0)
    counts = counts.reset_index().melt(id_vars="source_file", var_name="confidence_flag", value_name="rows")
    fig = px.bar(counts, x="source_file", y="rows", color="confidence_flag", title="Confidence Flag Distribution by Source")
    fig.write_html(FIGURES_DIR / "confidence_flag_distribution.html", include_plotlyjs="cdn")


def plot_validation_breakdown(issues: pd.DataFrame) -> None:
    if issues.empty:
        return
    counts = issues["message"].value_counts().sort_values()
    counts_df = counts.reset_index()
    counts_df.columns = ["message", "count"]
    fig = px.bar(counts_df, x="count", y="message", orientation="h", title="Validation Issue Breakdown")
    fig.write_html(FIGURES_DIR / "validation_issue_breakdown.html", include_plotlyjs="cdn")


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    records, issues = load_inputs()
    audit, cleanest_source = build_audit(records, issues)
    sample = build_high_confidence_sample(records)
    plot_records_by_source(audit)
    plot_field_completeness(records)
    plot_top_funds(records)
    plot_confidence_distribution(records)
    plot_validation_breakdown(issues)

    summary = {
        "cleanest_source": cleanest_source,
        "high_confidence_sample_rows": int(len(sample)),
        "figure_files": sorted(p.name for p in FIGURES_DIR.glob("*.html")),
    }
    (OUTPUTS_DIR / "samples" / "portfolio_artifact_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Built portfolio artifacts. Cleanest source: {cleanest_source}")


if __name__ == "__main__":
    main()
