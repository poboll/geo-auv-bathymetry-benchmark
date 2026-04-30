# v0.1.0 - Pre-submission reproducibility package

This release packages the manuscript-specific code, derived outputs, figures, and LaTeX artifacts for the Geo/JMSE draft:

**Terrain-Aware AUV Survey-Line Planning for Multibeam Bathymetric Mapping Using Public Bathymetry Benchmarks**

## Included Evidence

- Main `run_5` public GEBCO benchmark outputs.
- Supplemental four-window GEBCO scene-expansion check.
- Independent USGS Southern Cascadia 30 m public-grid extension.
- Coarse-prior to fine-grid replay.
- Execution-uncertainty replay.
- Equal-budget PSO local-refinement diagnostic.
- Turning-aware post-evaluation.
- Bootstrap confidence intervals.
- Objective penalty-weight sensitivity.
- MDPI/JMSE LaTeX draft and compiled PDFs.
- SHA-256 reproducibility manifest.

## Evidence Boundary

This is a public-bathymetry numerical benchmark and reproducibility package. It does not claim sea-trial validation, mission-log validation, hydrographic survey certification, or navigation-safety readiness.

## Source Data

- GEBCO 2025 Grid, DOI: `10.5285/37c52e96-24ea-67ce-e063-7086abc05f29`.
- USGS Southern Cascadia 30 m composite bathymetry, DOI: `10.5066/P9C5DBMR`.

Large raw source bathymetry archives are not committed; the release includes small processed caches and derived CSV/JSON outputs.
