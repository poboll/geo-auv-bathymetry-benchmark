# run_5 metric verification

- Verified at: 2026-04-25 00:08:28 CST
- Workspace: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`
- Evidence directory: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2/run_5`
- Conclusion: the model has numerical benchmark results on public gridded bathymetry and synthetic terrains; it does not have sea-trial or field-validation results.

## Source files checked

- `benchmark_results.csv`: 36347 bytes
- `benchmark_method_statistics.csv`: 10018 bytes
- `benchmark_results.json`: 95961 bytes
- `benchmark_summary.json`: 41137 bytes
- `public_scene_manifest.json`: 2010 bytes
- `implementation_details.json`: 1274 bytes

## Public-scene table values

| Scene | Method | Path km | Coverage % | Excess overlap % | Time s | Lines |
|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | Fixed-Spacing | 15166.71 | 100.00 | 0.798519 | 0.07 | 117 |
| GEBCO Cascadia Margin | Adaptive Spacing w/o GA | 15038.22 | 99.33 | 0.000000 | 0.75 | 116 |
| GEBCO Cascadia Margin | Full Geometry-Aware Hybrid GA | 15038.16 | 98.97 | 0.105520 | 0.69 | 116 |
| GEBCO Monterey Canyon | Fixed-Spacing | 6700.52 | 99.33 | 0.814815 | 0.04 | 73 |
| GEBCO Monterey Canyon | Adaptive Spacing w/o GA | 6656.62 | 100.00 | 0.000000 | 1.89 | 59 |
| GEBCO Monterey Canyon | Full Geometry-Aware Hybrid GA | 6656.57 | 99.63 | 0.084863 | 0.32 | 59 |

## Recomputed public aggregates

- GEBCO Cascadia Margin: fixed-to-hybrid path gain = 0.847593%
- GEBCO Monterey Canyon: fixed-to-hybrid path gain = 0.655803%
- Public mean path shortening = 0.751697859513%
- Hybrid public coverage range = 98.97%--99.63%
- Hybrid public mean coverage = 99.295833333333%
- Fixed public mean excess overlap = 0.806666666667%
- Hybrid public mean excess overlap = 0.095191510331%
- Mean excess-overlap reduction = 0.711475156335 percentage points

## Synthetic hybrid checks

| Scene | Path gain % | Coverage % | Excess overlap % | Feasible |
|---|---:|---:|---:|---:|
| Flat Seafloor | 3.556952 | 98.866667 | 0.000000 | 1.0 |
| Uniform Slope | 7.691173 | 99.998889 | 0.043747 | 1.0 |
| Complex Terrain | 25.774366 | 96.821111 | 7.175263 | 0.0 |

## Seed repeatability

| Scene | Seeds | Heading mode | Line-count mode | Path SD km | Coverage SD pp | Excess-overlap SD pp |
|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | 20 | 0 deg (20/20) | 116 (20/20) | 0.074267558737 | 0.340278523689 | 0.126784311111 |
| GEBCO Monterey Canyon | 20 | 90 deg (20/20) | 59 (20/20) | 0.053236830248 | 0.425348154612 | 0.115407556130 |

## SCI re-audit addendum

- Rechecked at: 2026-04-26 CST.
- Command evidence: Python read of `run_5/benchmark_method_statistics.csv` and `run_5/public_scene_manifest.json`.
- Public GEBCO evidence remains real public gridded bathymetry input, not AUV sea-trial telemetry.

### Public-scene recomputation

| Scene | Fixed-to-Hybrid gain % | Hybrid coverage % | Fixed excess overlap % | Hybrid excess overlap % | Hybrid lines |
|---|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | 0.847593 | 98.966667 | 0.798519 | 0.105520 | 116 |
| GEBCO Monterey Canyon | 0.655803 | 99.625000 | 0.814815 | 0.084863 | 59 |

- Public mean path shortening: `0.7516978595129359%`.
- Public mean Fixed-Spacing excess-overlap violation: `0.8066666666666665%`.
- Public mean Hybrid GA excess-overlap violation: `0.0951915103314442%`.
- Hybrid public predicted coverage range: `98.96666666666668%`--`99.625%`.

### Public-data provenance check

| Scene | Source | Bounds | Resolution | Depth range | Valid-cell handling |
|---|---|---|---:|---:|---|
| GEBCO Cascadia Margin | GEBCO 2025 global bathymetry subset | lon -126.8 to -125.2; lat 43.2 to 44.8; EPSG:4326 | 1195.383 m | 1009--3101 m | valid fraction 1.0; no filled cells |
| GEBCO Monterey Canyon | GEBCO 2025 global bathymetry subset | lon -123.3 to -122.3; lat 35.3 to 36.3; EPSG:4326 | 758.720 m | 892--3982 m | valid fraction 1.0; no filled cells |
