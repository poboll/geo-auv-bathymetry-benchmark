# USGS Southern Cascadia 30 m Multi-crop Extension

- Date: 2026-04-27 CST
- Workspace: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`
- Status: successful independent public-grid extension; added to the manuscript as a bounded numerical check, not as `run_5` replacement or sea-trial validation.

## Checklist

【x】Expanded the single-crop USGS ingestion pilot to three automatically selected public-grid crops.

Evidence:

- Script: `make_survey_grade_extension.py`
- Output directory: `survey_grade_extension_usgs_cascadia/`
- Selection quantiles: `0.25,0.55,0.80`
- Hybrid GA seeds: `0--19`
- Source raster: `public_bathy/raw/usgs/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2.tif`

【x】Ran the multi-crop extension in the Conda `uu` environment.

Command:

```bash
cd /Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python make_survey_grade_extension.py > survey_grade_extension_usgs_cascadia_20260427_v3.log 2>&1
```

Log evidence:

- `survey_grade_extension_usgs_cascadia_20260427_v3.log`
- Log reports three scene runs:
  - `running usgs_southern_cascadia_30m_low`
  - `running usgs_southern_cascadia_30m_medium`
  - `running usgs_southern_cascadia_30m_high`

【x】Wrote complete extension artifacts.

Files:

- `survey_grade_extension_usgs_cascadia/benchmark_method_statistics.csv`
- `survey_grade_extension_usgs_cascadia/benchmark_results.csv`
- `survey_grade_extension_usgs_cascadia/benchmark_results.json`
- `survey_grade_extension_usgs_cascadia/benchmark_summary.json`
- `survey_grade_extension_usgs_cascadia/public_scene_manifest.json`
- `survey_grade_extension_usgs_cascadia/README.md`
- `survey_grade_extension_usgs_cascadia/survey_grade_extension_journal.png`
- `latex/pic/journal_usgs_extension.png`

【x】Rebuilt the extension figure in journal style.

Reason:

- The first preview (`survey_grade_extension_layouts.png`) was a debug-style 3 x 3 hard collage with crowded titles.
- The revised figure uses a terrain-strip plus metric-column layout and is copied into the LaTeX figure directory.

Visual QA:

- Standalone PNG: `latex/pic/journal_usgs_extension.png`
- Rendered PDF page: `/tmp/geo_usgs_extension_page_20.png`

【x】Integrated the extension into the manuscript with cautious scope.

Manuscript edits:

- `latex/template.tex`
  - Abstract now mentions the USGS extension as a separate public-grid check.
  - Results evidence map now includes the higher-resolution public-grid extension.
  - Added subsection: `Independent USGS 30 m Public-grid Extension`.
  - Added Figure `fig:usgs_extension`.
  - Discussion and Conclusion now state what the extension supports and what it does not support.
  - Data availability now cites GEBCO and the USGS data release.
  - Added BibTeX-style embedded reference key `dartnell2026southerncascadia`.

Boundary:

- The extension is explicitly not mixed into `run_5`.
- The extension is not described as field validation, sea trial, mission-log replay, navigation-grade validation, or operational deployment proof.

【x】Compiled and checked the manuscript after integration.

Command:

```bash
cd /Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2/latex
xelatex -interaction=nonstopmode template.tex > compile_after_usgs_extension_final_20260427_pass1.log 2>&1
xelatex -interaction=nonstopmode template.tex > compile_after_usgs_extension_final_20260427_pass2.log 2>&1
```

Compile result:

- `compile_after_usgs_extension_final_20260427_pass2.log`
- Output: `Output written on template.pdf (25 pages).`
- Citation/reference check:
  - 25 citation keys, 25 bibitems, no missing cite keys, no unused bibitems.
  - 22 refs, no missing refs.
- Warning check:
  - no undefined citations/references.
  - no overfull/underfull boxes reported by `rg`.
  - only routine XeLaTeX warning: `inputenc package ignored with utf8 based engines`.

Synced PDFs:

- `latex/template.pdf`
- `paper_refined.pdf`
- `geo_public_bathy_rebuild.pdf`

## Numeric Results From CSV

From `survey_grade_extension_usgs_cascadia/benchmark_method_statistics.csv`:

| Scene | Method | Path km | Path gain vs Fixed | Coverage % | Excess overlap % | Feasible |
|---|---|---:|---:|---:|---:|---:|
| Low crop | Fixed-Spacing | 51.93 | 0.00% | 100.00 | 1.633 | 1.0 |
| Low crop | Adaptive Spacing w/o GA | 52.11 | -0.35% | 100.00 | 0.000 | 1.0 |
| Low crop | Full Geometry-Aware Hybrid GA | 51.97 | -0.08% | 98.90 | 0.000 | 1.0 |
| Medium crop | Fixed-Spacing | 51.93 | 0.00% | 100.00 | 1.633 | 1.0 |
| Medium crop | Adaptive Spacing w/o GA | 52.11 | -0.35% | 100.00 | 0.000 | 1.0 |
| Medium crop | Full Geometry-Aware Hybrid GA | 51.97 | -0.08% | 98.90 | 0.000 | 1.0 |
| High crop | Fixed-Spacing | 97.25 | 0.00% | 97.20 | 29.960 | 0.0 |
| High crop | Adaptive Spacing w/o GA | 73.89 | 24.02% | 98.55 | 2.237 | 1.0 |
| High crop | Full Geometry-Aware Hybrid GA | 72.90 | 25.04% | 98.44 | 1.732 | 1.0 |

## Interpretation

The extension strengthens the manuscript in a narrow, defensible way. It shows that the planner can ingest an independent 30 m public bathymetry product and that terrain-aware spacing can rescue a high-complexity public-grid crop where Fixed-Spacing violates the overlap feasibility rule. It also prevents overclaiming: on easier low- and medium-complexity crops, route shortening is negligible or slightly negative, and the benefit is mainly overlap removal.

Safe manuscript claim:

- "A separate USGS 30 m public-grid extension reproduces the overlap-control pattern on a high-complexity crop while showing negligible route shortening on lower-complexity crops."

Unsafe claims to avoid:

- "validated at sea"
- "survey-grade mission validation"
- "navigation-grade planning proof"
- "universal route shortening"
- "operational deployment guarantee"
