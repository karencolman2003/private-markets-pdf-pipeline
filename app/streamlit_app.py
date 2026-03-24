from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "normalized" / "dashboard_records.csv"
SUMMARY_PATH = PROJECT_ROOT / "data" / "normalized" / "dashboard_summary.json"

st.set_page_config(page_title="Private Markets PDF Pipeline", layout="wide")
st.title("Private Markets PDF Extraction & Normalization Pipeline")
st.caption("Public-data reconstruction of a private-markets data-ops workflow using CalPERS PDFs.")

if not DATA_PATH.exists():
    st.warning("No dashboard dataset found yet. Run `python src/build_dashboard_data.py --run-all` first.")
    st.stop()

df = pd.read_csv(DATA_PATH)
summary = {}
if SUMMARY_PATH.exists():
    summary = pd.read_json(SUMMARY_PATH, typ="series").to_dict()

col1, col2, col3 = st.columns(3)
col1.metric("Records", len(df))
col2.metric("Sources", df["source_file"].nunique() if "source_file" in df else 0)
col3.metric("Funds", df["fund_name"].dropna().nunique() if "fund_name" in df else 0)

source_options = sorted(df["source_file"].dropna().unique().tolist()) if "source_file" in df else []
selected_sources = st.sidebar.multiselect("Source files", source_options, default=source_options)
selected_fund = st.sidebar.text_input("Fund name contains", "")

filtered = df.copy()
if selected_sources:
    filtered = filtered[filtered["source_file"].isin(selected_sources)]
if selected_fund:
    filtered = filtered[filtered["fund_name"].fillna("").str.contains(selected_fund, case=False)]

st.subheader("Normalized Records")
st.dataframe(filtered, use_container_width=True, hide_index=True)

st.subheader("Missingness")
missingness = filtered.isna().mean().sort_values(ascending=False).reset_index()
missingness.columns = ["field", "missing_rate"]
st.dataframe(missingness, use_container_width=True, hide_index=True)

metrics = ["nav", "tvpi", "dpi", "irr"]
available_metrics = [metric for metric in metrics if metric in filtered.columns and filtered[metric].notna().any()]
for metric in available_metrics:
    chart_df = filtered.dropna(subset=[metric])
    if chart_df.empty:
        continue
    fig = px.histogram(chart_df, x=metric, nbins=20, title=f"{metric.upper()} distribution")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Provenance")
provenance_cols = [col for col in ["source_name", "source_file", "page_number", "extraction_method", "raw_row_text", "notes"] if col in filtered.columns]
st.dataframe(filtered[provenance_cols], use_container_width=True, hide_index=True)

