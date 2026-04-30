# Terrain-Aware AUV Bathymetry Benchmark

This public repository contains the manuscript-specific code, derived data, figures, and LaTeX artifacts for:

**Terrain-Aware AUV Survey-Line Planning for Multibeam Bathymetric Mapping Using Public Bathymetry Benchmarks**

The study is framed as a public-bathymetry numerical benchmark for AUV-assisted multibeam survey-line planning. It does not claim sea-trial validation, mission-log validation, hydrographic-survey certification, or navigation-safety readiness.

## Contents

- `geo_public_bathy_benchmark.py`: main public-bathymetry benchmark runner.
- `make_*.py`: figure, sensitivity, uncertainty replay, turning-aware, coarse-prior replay, PSO baseline, and manifest scripts.
- `run_5/`: latest validated benchmark outputs used as the main evidence source.
- `sensitivity/`: beam-angle, overlap-target, prior-depth, prior-relief, grid-resolution, and objective penalty-weight diagnostics.
- `uncertainty_replay/`: execution-uncertainty replay outputs.
- `survey_grade_extension_usgs_cascadia/`: independent USGS Southern Cascadia 30 m public-grid extension.
- `coarse_prior_replay/`: coarse-prior to fine-grid replay outputs.
- `pso_baseline/`: equal-budget PSO local-refinement diagnostic.
- `public_bathy/processed/`: small processed GEBCO scene caches used by the benchmark.
- `manuscript/mdpi_jmse/`: MDPI/JMSE draft source and compiled PDF.
- `manuscript/latex/`: working manuscript source and compiled PDF.
- `audit/`: revision logs, data-boundary notes, reference checks, and reviewer-risk notes.
- `reproducibility_manifest.json`: SHA-256 manifest for manuscript-specific artifacts.

## Data Provenance

Primary public source data:

- GEBCO 2025 Grid, DOI: `10.5285/37c52e96-24ea-67ce-e063-7086abc05f29`.
- USGS Southern Cascadia 30 m composite bathymetry, DOI: `10.5066/P9C5DBMR`.

Large raw bathymetry archives are not committed to this repository. The repository includes small processed GEBCO caches and derived CSV/JSON outputs. Re-download the raw GEBCO/USGS products from the official DOI landing pages if rerunning raw-data ingestion.

## Reproduction

The local drafting environment used a Conda environment named `uu`. A minimal equivalent environment should include Python, NumPy, pandas, matplotlib, Pillow, requests, and rasterio.

Typical commands from the repository root:

```bash
conda activate uu
python geo_public_bathy_benchmark.py
python make_public_bootstrap_ci.py
python make_turning_aware_posteval.py
python make_sensitivity_study.py
python make_penalty_weight_sensitivity.py
python make_uncertainty_replay.py
python make_survey_grade_extension.py
python make_coarse_prior_replay.py
python make_pso_baseline.py
python make_journal_figures.py
python make_reproducibility_manifest.py
```

Compile the MDPI/JMSE manuscript:

```bash
cd manuscript/mdpi_jmse
xelatex -interaction=nonstopmode template.tex
xelatex -interaction=nonstopmode template.tex
```

## Current Evidence Boundary

The latest validated run is `run_5`. The strongest supported claim is that terrain-aware spacing with a small local GA refinement improves overlap discipline and repeatability for offline fixed-pattern survey-line planning on public bathymetry benchmarks. Public GEBCO route shortening is modest; the main public-scene result is excess-overlap suppression. Higher-complexity USGS and coarse-prior replay diagnostics are used as public-grid stress checks, not as sea-trial evidence.

## Archive Status

GitHub release repository: <https://github.com/poboll/geo-auv-bathymetry-benchmark>.

A Zenodo DOI should be minted from this GitHub repository before final journal submission, then inserted into the manuscript Data Availability statement.
