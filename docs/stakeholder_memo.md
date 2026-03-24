# Stakeholder / Interview Memo

## What I attempted

I built a small, auditable pipeline around public CalPERS private-equity-related documents to simulate a real private-markets data-operations workflow:

- acquire source documents
- extract candidate rows from heterogeneous PDFs
- normalize outputs into a standard schema
- preserve provenance
- validate suspicious rows
- prepare downstream analytics outputs

The project intentionally uses public data, but the workflow is modeled on the same operational challenge that appears in private LP reporting environments.

## What the pipeline successfully automated

- Downloaded and inventoried a reproducible CalPERS starter dataset
- Extracted page text and table artifacts for transparency
- Identified the cleanest source layout in the set
- Parsed 418 high-confidence private-equity holdings rows from the 2023-24 Annual Investment Report
- Normalized outputs into a consistent schema with provenance fields
- Produced dashboard-ready records, audit outputs, validation logs, and representative samples

## What still needs analyst review

- The two annual program review PDFs remain only partially automated
- Aggregate program-review pages still generate ambiguous rows
- Some `tvpi` / `irr` candidates are chart-derived and need stricter source-specific parsing
- Certain rows are intentionally flagged for review rather than silently accepted

This is by design. The project favors auditability and honesty over overstating extraction quality.

## Why the project is still valuable

The value of the project is not that every source is solved. The value is that it demonstrates the real work required to turn unstructured reporting into a usable dataset:

- source acquisition
- layout-aware extraction
- schema normalization
- provenance preservation
- validation and exception handling

That is a realistic private-markets data-ops story, and it is a stronger portfolio signal than a polished dashboard built on already-clean data.
