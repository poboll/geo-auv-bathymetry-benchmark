# Terrain-Aware Multibeam Survey-Line Planning Benchmark

This repository contains the analysis code, benchmark definitions, and derived
outputs supporting the manuscript:

**Terrain-aware multibeam survey-line planning from public bathymetric priors**

## Scope

The study is a planning-stage numerical benchmark for depth-referenced
multibeam echosounder (MBES) fixed-line survey planning from public bathymetric
priors. It evaluates line orientation, nonuniform spacing, predicted coverage,
excess overlap, local refinement, and constrained stress-case repair within a
reproducible public-grid setting.

The evidence is intentionally limited to pre-mission line-layout analysis.
Realized survey execution, controller-level transfer, raw MBES product
validation, and charting-product assessment are outside the claims supported by
this repository.

## Repository contents

- `run_5/`: primary public-grid benchmark outputs.
- `sensitivity/`: beam-angle, overlap-target, prior-error, resolution, and
  penalty-weight diagnostics.
- `gebco_scene_expansion/` and `public_window_statistics/`: additional public
  GEBCO windows and scene statistics.
- `usgs_cascadia_extension/`: high-resolution Southern Cascadia public-grid
  extension.
- `coarse_prior_replay/`, `structured_prior_error_replay/`, and
  `uncertainty_replay/`: prior-resolution and perturbation checks.
- `uncertainty_margin_replay/`, `current_drift_replay/`, and
  `execution_risk_refinement/`: planning-to-execution stress diagnostics.
- `segmented_heading_extension/`, `segmented_decision_audit/`, and
  `threshold_local_failure_extension/`: constrained repair and failure-boundary
  tests.
- `make_*.py`: figure and analysis entry points for the corresponding outputs.

## Public source data

The benchmark uses the following public bathymetric products:

- GEBCO 2025 Grid: <https://doi.org/10.5285/37c52e96-24ea-67ce-e063-7086abc05f29>
- USGS Southern Cascadia 30 m composite bathymetry:
  <https://doi.org/10.5066/P9C5DBMR>

Large raw bathymetry archives are not committed. Re-download them from the
official DOI landing pages when rerunning raw-data ingestion.

## Environment and reproducibility

Create the recorded environment with:

```bash
conda env create -f environment.yml
conda activate geo-auv-benchmark
```

The derived CSV, JSON, and figure outputs are retained beside their generating
scripts so that numerical claims can be traced without treating the repository
as a survey-product archive.

## Citation

Use `CITATION.cff` for software citation metadata. The repository name is
historical; the manuscript and this README define the supported contribution as
a fixed-line MBES planning benchmark.
