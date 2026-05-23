# External Survey-layout Heuristic Baseline Audit

This diagnostic responds to the reviewer risk that the manuscript only compares variants inside the same proposed family. It does not claim to reproduce complete field-ready coverage-path-planning systems. Instead, it implements three deterministic survey-layout heuristics under the same raster MBES evaluator and audits them against the paper's fixed/adaptive references.

## External heuristics

- **Min-Span Boustrophedon:** choose the 5-degree heading with minimum cross-track span, then use a scene-wide q0.30 fixed-width spacing.
- **Contour-Parallel Fixed-Width:** estimate the dominant contour-parallel heading from the bathymetric gradient, snap to 5 degrees, then use the same fixed-width spacing.
- **Geometry-Shortest Fixed-Width:** scan 5-degree headings and choose the shortest fixed-width lawnmower distance before auditing coverage and overlap.

## Summary

| Method | Feasible windows | Median path gain (%) | Median coverage (%) | Median excess overlap (%) | Median overlap cleanup (pp) |
|---|---:|---:|---:|---:|---:|
| Min-span | 6/9 | 0.350 | 99.17 | 0.801 | 0.126 |
| Contour | 6/9 | 0.128 | 99.99 | 0.439 | 0.619 |
| Geom-short | 8/9 | 0.398 | 99.99 | 0.226 | 0.514 |
| Adaptive | 9/9 | 0.681 | 99.33 | 0.000 | 0.799 |
| Hybrid s0 | 9/9 | 0.681 | 99.33 | 0.000 | 0.781 |

## Best external heuristic by scene

| Scene | Best external heuristic | Score | Coverage (%) | Excess overlap (%) | Path gain (%) |
|---|---|---:|---:|---:|---:|
| GEBCO Cascadia | Geom-short | 15066.12 | 100.00 | 0.093 | 0.665 |
| GEBCO Hawaii | Min-span | 30037.58 | 97.87 | 0.226 | 0.350 |
| GEBCO Mariana | Geom-short | 31935.69 | 99.99 | 0.060 | 0.251 |
| GEBCO Mid-Atlantic | Geom-short | 26412.82 | 99.99 | 0.025 | 0.398 |
| GEBCO Monterey | Min-span | 6657.27 | 99.18 | 0.301 | 0.659 |
| GEBCO Puerto Rico | Min-span | 30709.75 | 98.58 | 0.000 | 0.493 |
| USGS High | Min-span | 448.53 | 92.44 | 7.488 | 36.643 |
| USGS Low | Geom-short | 56.83 | 100.00 | 1.633 | 0.000 |
| USGS Medium | Geom-short | 56.83 | 100.00 | 1.633 | 0.000 |

## Interpretation boundary

- The audit is a compact external-style baseline layer; it is not an implementation of a full Zhao/Bai-style multi-objective, vehicle-dynamics, or field-validated planner.
- If an external heuristic wins a scene, that result should be reported rather than hidden; the manuscript claim is terrain-aware fixed-line spacing, not global SOTA dominance.
- The main comparator remains the deterministic Adaptive Spacing layout, with Hybrid GA treated as local seed-0 cleanup in this audit and as a 50-seed method in the main benchmark.
