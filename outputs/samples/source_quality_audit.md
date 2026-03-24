# Source Quality Audit

Cleanest current fund-level source: `annual-investment-report-fy-2024.pdf`.

## Summary

| source_file                          |   record_count |   unique_fund_names |   high_confidence_rows |   medium_confidence_rows |   low_confidence_rows |   flagged_review_rows |   report_date_populated_rate |   fund_name_populated_rate |   vintage_year_populated_rate |   committed_capital_populated_rate |   contributed_capital_populated_rate |   distributed_capital_populated_rate |   nav_populated_rate |   tvpi_populated_rate |   dpi_populated_rate |   irr_populated_rate | cleanest_source_now   |
|:-------------------------------------|---------------:|--------------------:|-----------------------:|-------------------------:|----------------------:|----------------------:|-----------------------------:|---------------------------:|------------------------------:|-----------------------------------:|-------------------------------------:|-------------------------------------:|---------------------:|----------------------:|---------------------:|---------------------:|:----------------------|
| 202406-invest-item05b-01-a.pdf       |             59 |                  49 |                      0 |                       30 |                    29 |                     7 |                    0.20339   |                   0.949153 |                    0.322034   |                           0.135593 |                             0.135593 |                             0.135593 |             0.677966 |             0.0338983 |                    0 |             0.59322  | False                 |
| 202506-invest-agenda-item06c-01.pdf  |            162 |                 139 |                      0 |                       81 |                    81 |                    10 |                    0.0864198 |                   0.987654 |                    0.222222   |                           0.283951 |                             0.283951 |                             0.283951 |             0.58642  |             0.0555556 |                    0 |             0.641975 | False                 |
| annual-investment-report-fy-2024.pdf |            418 |                 418 |                    418 |                        0 |                     0 |                     0 |                    1         |                   1        |                    0.00239234 |                           0        |                             0        |                             0        |             1        |             0         |                    0 |             0        | True                  |

## Interpretation

- The annual investment report is currently the cleanest source because its private-equity holdings section follows a stable `Security Name / Book Value / Market Value` layout.
- The two annual program review PDFs still produce useful extraction artifacts and some aggregate metrics, but they remain noisier and require more analyst review.
- High-confidence rows are concentrated in the annual investment report; flagged review rows are concentrated in the annual program review sources.
