# Data Sources and Reproduction

[SEC Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets) provide quarterly ZIPs containing filing metadata and XBRL facts. The optional acquisition notebook covers 2013–2024. See the [SEC field documentation](https://www.sec.gov/files/fsds.pdf) for `qtrs`, taxonomy versions and filing identifiers.

FRED series: [FEDFUNDS](https://fred.stlouisfed.org/series/FEDFUNDS), [CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL), [INDPRO](https://fred.stlouisfed.org/series/INDPRO). Annual CPI inflation and industrial-production growth compare adjacent calendar-year averages. Values are contemporaneous, not lagged, and are not historical vintages.

## Processed-data route

The repository includes `processed/company_year_panel.csv` and `processed/model_scores.csv`. Start at Notebook 03 to reproduce the main analysis. CIK is a ten-character zero-padded string; specify `dtype={"cik": str}` when reading it in pandas. Preserve CIK as text in Tableau and SQLite.

## Optional raw rebuild

Raw ZIPs total several GB and are ignored. Do not download them just to inspect the main results. If rebuilding, set `SEC_USER_AGENT` in your local environment to a descriptive project name and a contact email you control. Never put its actual value in a tracked file or notebook output. Notebook 01 raises a clear error if it is absent or contains a placeholder.

PowerShell, prompting locally without placing the value in the command history:

```powershell
$env:SEC_USER_AGENT = Read-Host "Project name and SEC contact email"
python -m jupyterlab
```

macOS/Linux:

```bash
read -r -p "Project name and SEC contact email: " SEC_USER_AGENT
export SEC_USER_AGENT
python -m jupyterlab
```

Run 01 then 02 only when the complete raw sources are available. Notebook 01 preserves existing ZIPs and writes downloads atomically. Notebook 02 uses current-period consolidated USD values, strict annual/instant durations, deterministic tag priorities and latest annual filing selection. Conflicting best-priority values become missing. Fallback tag scopes differ and should be reviewed before substantive use.

## Verification boundary

Raw SEC ZIPs, FRED files and `company_year_panel_raw.csv` were absent during this release's validation. Notebook 01–02 therefore received static checks only. Existing panel ratios, adjacent-year changes, volatility and target alignment were checked; source extraction and completeness could not be independently rebuilt. Revised extraction rules may change results in a future full rebuild.

`raw/`, the raw intermediate, SQLite files, caches and environments are excluded from upload. The 2024 panel contains only 280 observations because source filing coverage ends in 2024; it is not a full 2024 reporting cohort.
