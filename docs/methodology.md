# Methodology

## Why PDF extraction is hard in private markets

Private-markets performance data is commonly published for human review rather than machine ingestion. Even when the source is public, the operational problem remains:

- table boundaries are inconsistent
- column headers drift across reports
- the same PDF may mix narrative summaries and detailed schedules
- relevant rows can span multiple lines or use abbreviations
- machine-readable text still requires careful parsing and provenance

## Version 1 design choices

This project is intentionally scoped as a portfolio-quality, reproducible starter pipeline.

- Use a small CalPERS source set instead of claiming universal coverage
- Prefer recent machine-generated PDFs over OCR-heavy scans
- Preserve intermediate artifacts for transparency
- Keep source-specific heuristics explicit
- Fail loudly and log gaps instead of fabricating records

## Extraction flow

1. Download public CalPERS PDFs or record manual-download requirements
2. Create a local PDF manifest
3. Score pages for likely private-equity performance content
4. Run Camelot `lattice` and `stream` extraction on candidate pages
5. Run `pdfplumber` text extraction on all pages for fallback coverage
6. Build candidate rows from tables and text
7. Parse fields via regex and simple column heuristics
8. Normalize to the shared schema
9. Validate output and emit quality flags
10. Build a dashboard-ready subset and summary statistics

## Auditability principles

- every normalized row keeps `source_file`, `page_number`, and `extraction_method`
- original row text is retained
- validation concerns are attached as notes and separate logs
- intermediate JSON and CSV outputs make debugging reproducible

## Known limitations

- CalPERS reports may not expose every desired field at the fund level
- direct download links can change or require manual browser confirmation
- Camelot quality depends on PDF structure and local dependencies
- no OCR pipeline is included in v1

