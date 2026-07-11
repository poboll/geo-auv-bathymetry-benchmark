# v0.1.0 - Public-bathymetry benchmark package

This release records the code, derived outputs, and figure-generation workflow
for the terrain-aware fixed-line MBES planning benchmark.

## Included evidence

- Primary and expanded public GEBCO benchmark outputs.
- USGS Southern Cascadia 30 m public-grid extension.
- Coarse-prior/fine-grid and structured prior-error replays.
- Execution-uncertainty, current-drift, and margin-selection diagnostics.
- Equal-budget optimization and turning-cost diagnostics.
- Threshold, local-failure, and segmented-decision audits.
- Beam-angle, overlap-target, grid-resolution, and penalty-weight sensitivity.

## Evidence boundary

This package supports planning-stage numerical evidence for fixed-line MBES
survey layouts. It does not establish realized survey execution performance,
raw MBES product validity, hydrographic certification, or operational readiness.

## Source data

- GEBCO 2025 Grid: `10.5285/37c52e96-24ea-67ce-e063-7086abc05f29`.
- USGS Southern Cascadia 30 m composite bathymetry: `10.5066/P9C5DBMR`.

Large raw source bathymetry archives are not committed; the release retains
small processed caches and derived CSV/JSON outputs required for traceability.
