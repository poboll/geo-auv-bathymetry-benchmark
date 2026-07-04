# Terrain-Aware MBES Survey-Line Planning Benchmark

This repository supports the manuscript:

**Terrain-Aware MBES Survey-Line Planning with Public Bathymetric Priors: A Pre-Mission Ocean-Engineering Numerical Benchmark**

For the current JMSE two-author submission package, use the clean reviewer-facing release directory:

<https://github.com/poboll/geo-auv-bathymetry-benchmark/tree/main/reviewer_release/jmse_20260704>

## Scope

The study is a planning-stage numerical benchmark for depth-referenced multibeam echo sounder (MBES) fixed-line survey planning from public bathymetric priors. It evaluates line orientation, spacing, overlap control, local refinement, and stress-case repair within a reproducible public-grid setting.

The manuscript is intentionally scoped to pre-mission line-layout evidence. Execution-stage vehicle validation, controller-level transfer, and charting-product assessment are outside the claims of this repository release.

## Current Submission Package

The current reviewer package contains:

- current two-author manuscript PDF,
- LaTeX source ZIP with figures and template files,
- JMSE cover-letter text,
- SHA-256 checksums.

## Public Source Data

Primary public source data:

- GEBCO 2025 Grid, DOI: `10.5285/37c52e96-24ea-67ce-e063-7086abc05f29`.
- USGS Southern Cascadia 30 m composite bathymetry, DOI: `10.5066/P9C5DBMR`.

Large raw bathymetry archives are not committed to this repository. Re-download the raw products from the official DOI landing pages if rerunning raw-data ingestion.

## Reproducibility Archive

The DOI-bearing reproducibility archive series is hosted on Zenodo:

- Concept DOI: <https://doi.org/10.5281/zenodo.19919505>
- Version DOI: <https://doi.org/10.5281/zenodo.19919506>

The current LaTeX submission source is supplied to the journal through the source ZIP in the reviewer release directory.

## Citation

Use `CITATION.cff` for software/package citation metadata. The repository name is historical; the submitted paper frames the package as an MBES fixed-line planning benchmark.
