# Normalized Schema

This project normalizes heterogeneous private-equity PDF content into a single fund-level schema.

## Fields

| Field | Type | Description |
| --- | --- | --- |
| `source_name` | string | Human-readable source label from the downloader inventory |
| `source_file` | string | Local PDF filename used during extraction |
| `report_date` | string or null | Report date detected from metadata, filename, or page text |
| `page_number` | integer | 1-based page number for provenance |
| `fund_name` | string or null | Parsed fund name |
| `vintage_year` | integer or null | Parsed vintage year if plausible |
| `committed_capital` | float or null | Commitment amount with currency symbols removed |
| `contributed_capital` | float or null | Contribution amount with currency symbols removed |
| `distributed_capital` | float or null | Distribution amount with currency symbols removed |
| `nav` | float or null | Net asset value |
| `tvpi` | float or null | Total value to paid-in |
| `dpi` | float or null | Distributed to paid-in |
| `irr` | float or null | Internal rate of return |
| `currency` | string | Currency code or symbol inference, default `USD` |
| `raw_row_text` | string | Original extracted row text before normalization |
| `extraction_method` | string | `camelot_lattice`, `camelot_stream`, `pdfplumber_text`, or similar |
| `confidence_flag` | string | `high`, `medium`, `low`, or `review` |
| `notes` | string | Free-text notes about parsing assumptions or validation flags |

## Normalization rules

- Currency strings remove `$`, commas, spaces, and footnote markers before numeric coercion
- Percent values are normalized to decimal fractions
- Multiples such as `1.25x` are stored as numeric `1.25`
- Missing values remain `null`
- Original row text is always preserved in `raw_row_text`
- Provenance fields are mandatory even when business metrics are missing

## Validation checks

- `vintage_year` should fall between 1980 and the current year plus 1
- `nav`, `committed_capital`, `contributed_capital`, and `distributed_capital` must be non-negative when present
- `irr` outside `-1.0` to `5.0` is flagged for review
- `tvpi` and `dpi` above `10.0` are flagged for review

