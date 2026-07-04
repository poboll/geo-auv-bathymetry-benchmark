# Segmented-heading extension

This diagnostic targets the main algorithmic weakness exposed by the current manuscript: a single-heading fixed-pattern lawnmower can remain infeasible in complex relief. The segmented variant keeps the method auditable by splitting the survey domain into a small number of y-blocks, choosing a terrain-aware heading inside each block, and adding a conservative inter-block transit term to the reported path length.

- Scenes: synthetic_complex, gebco_monterey_canyon_complex, gebco_mariana_trench_complex, gebco_puerto_rico_trench_complex, usgs_southern_cascadia_30m_high
- Hybrid seeds: 0--29
- Segment counts: 2, 3, 4, 5
- Segment candidate top-k per block: 4
- Minimum turn radius used for transition scoring: 100.0 m
- Acceptance gate: global coverage >= 97%, global excess overlap <= 3%, and no coverage regression relative to the single-heading Hybrid GA unless segmentation changes an infeasible single-heading layout into a feasible one.
- Coverage-preserving selector after the acceptance gate: choose the lower path-plus-overlap score, `L + 3 O_ex`, between the single-heading layout and accepted segmented candidates.
- Transition-aware selector after the acceptance gate: choose the lower mission-time proxy at `R_min=100 m`, including survey/transit distance at 1.5 m/s, heading-change arcs and line-change arcs at 0.75 m/s, plus a small overlap tie-breaker.
- Boundary: numerical geometry diagnostic, not AUV controller validation or deployment evidence.

## Summary

| Scene | Method | Segments | Runs | Path km | Mission proxy h | Coverage % | Excess overlap % | Feasible rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GEBCO Mariana Trench | Coverage-Preserving Segmented Hybrid | 1 | 30 | 31797.61 | 5905.20 | 99.02 | 0.126 | 1.00 |
| GEBCO Mariana Trench | Full Geometry-Aware Hybrid GA | 1 | 30 | 31797.61 | 5905.20 | 99.02 | 0.126 | 1.00 |
| GEBCO Mariana Trench | Segmented Adaptive | 2 | 1 | 26021.39 | 4838.56 | 95.32 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Segmented Adaptive | 3 | 1 | 26120.75 | 4860.21 | 95.93 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Segmented Adaptive | 4 | 1 | 26219.36 | 4881.73 | 95.28 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Segmented Adaptive | 5 | 1 | 26318.98 | 4903.56 | 96.83 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Segmented Hybrid GA | 2 | 30 | 26021.39 | 4838.56 | 95.32 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Segmented Hybrid GA | 3 | 30 | 26120.75 | 4860.21 | 95.93 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Segmented Hybrid GA | 4 | 30 | 26219.32 | 4881.73 | 95.28 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Segmented Hybrid GA | 5 | 30 | 26318.98 | 4903.56 | 96.83 | 0.000 | 0.00 |
| GEBCO Mariana Trench | Transition-Aware Segmented Hybrid | 1 | 30 | 31797.61 | 5905.20 | 99.02 | 0.126 | 1.00 |
| GEBCO Monterey Canyon | Coverage-Preserving Segmented Hybrid | 1 | 16 | 6656.58 | 1239.45 | 99.74 | 0.091 | 1.00 |
| GEBCO Monterey Canyon | Coverage-Preserving Segmented Hybrid | 2 | 5 | 5787.72 | 1081.57 | 100.00 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Coverage-Preserving Segmented Hybrid | 3 | 3 | 5860.07 | 1096.37 | 99.77 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Coverage-Preserving Segmented Hybrid | 4 | 3 | 5897.54 | 1101.69 | 99.55 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Coverage-Preserving Segmented Hybrid | 5 | 3 | 6003.59 | 1125.74 | 99.44 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Full Geometry-Aware Hybrid GA | 1 | 30 | 6656.58 | 1239.45 | 99.56 | 0.082 | 1.00 |
| GEBCO Monterey Canyon | Segmented Adaptive | 2 | 1 | 5787.72 | 1081.57 | 100.00 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Segmented Adaptive | 3 | 1 | 5862.08 | 1096.74 | 100.00 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Segmented Adaptive | 4 | 1 | 5900.26 | 1102.19 | 100.00 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Segmented Adaptive | 5 | 1 | 6010.80 | 1127.07 | 100.00 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Segmented Hybrid GA | 2 | 30 | 5779.60 | 1080.07 | 98.42 | 0.001 | 1.00 |
| GEBCO Monterey Canyon | Segmented Hybrid GA | 3 | 30 | 5851.20 | 1094.72 | 98.55 | 0.002 | 1.00 |
| GEBCO Monterey Canyon | Segmented Hybrid GA | 4 | 30 | 5891.85 | 1100.63 | 98.89 | 0.002 | 1.00 |
| GEBCO Monterey Canyon | Segmented Hybrid GA | 5 | 30 | 5997.04 | 1124.53 | 98.94 | 0.002 | 1.00 |
| GEBCO Monterey Canyon | Transition-Aware Segmented Hybrid | 1 | 16 | 6656.58 | 1239.45 | 99.74 | 0.091 | 1.00 |
| GEBCO Monterey Canyon | Transition-Aware Segmented Hybrid | 2 | 5 | 5787.72 | 1081.57 | 100.00 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Transition-Aware Segmented Hybrid | 3 | 3 | 5860.07 | 1096.37 | 99.77 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Transition-Aware Segmented Hybrid | 4 | 3 | 5897.54 | 1101.69 | 99.55 | 0.000 | 1.00 |
| GEBCO Monterey Canyon | Transition-Aware Segmented Hybrid | 5 | 3 | 6003.59 | 1125.74 | 99.44 | 0.000 | 1.00 |
| GEBCO Puerto Rico Trench | Coverage-Preserving Segmented Hybrid | 1 | 30 | 30709.66 | 5702.80 | 98.08 | 0.274 | 1.00 |
| GEBCO Puerto Rico Trench | Full Geometry-Aware Hybrid GA | 1 | 30 | 30709.66 | 5702.80 | 98.08 | 0.274 | 1.00 |
| GEBCO Puerto Rico Trench | Segmented Adaptive | 2 | 1 | 25089.89 | 4665.94 | 94.66 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Segmented Adaptive | 3 | 1 | 25186.16 | 4686.91 | 94.72 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Segmented Adaptive | 4 | 1 | 25279.23 | 4707.17 | 94.70 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Segmented Adaptive | 5 | 1 | 25619.37 | 4773.77 | 95.58 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Segmented Hybrid GA | 2 | 30 | 25089.89 | 4665.94 | 94.66 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Segmented Hybrid GA | 3 | 30 | 25186.16 | 4686.91 | 94.72 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Segmented Hybrid GA | 4 | 30 | 25279.23 | 4707.17 | 94.70 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Segmented Hybrid GA | 5 | 30 | 25619.37 | 4773.77 | 95.58 | 0.000 | 0.00 |
| GEBCO Puerto Rico Trench | Transition-Aware Segmented Hybrid | 1 | 30 | 30709.66 | 5702.80 | 98.08 | 0.274 | 1.00 |
| Complex Terrain | Coverage-Preserving Segmented Hybrid | 4 | 30 | 265.34 | 60.37 | 97.18 | 1.392 | 1.00 |
| Complex Terrain | Full Geometry-Aware Hybrid GA | 1 | 30 | 254.14 | 51.60 | 96.83 | 7.172 | 0.00 |
| Complex Terrain | Segmented Adaptive | 2 | 1 | 243.27 | 51.57 | 95.94 | 3.519 | 0.00 |
| Complex Terrain | Segmented Adaptive | 3 | 1 | 261.20 | 57.94 | 96.78 | 2.937 | 0.00 |
| Complex Terrain | Segmented Adaptive | 4 | 1 | 265.34 | 60.37 | 97.09 | 1.377 | 1.00 |
| Complex Terrain | Segmented Adaptive | 5 | 1 | 275.55 | 64.44 | 97.27 | 0.616 | 1.00 |
| Complex Terrain | Segmented Hybrid GA | 2 | 30 | 243.27 | 51.57 | 95.95 | 3.518 | 0.00 |
| Complex Terrain | Segmented Hybrid GA | 3 | 30 | 261.04 | 57.91 | 96.74 | 2.936 | 0.00 |
| Complex Terrain | Segmented Hybrid GA | 4 | 30 | 265.34 | 60.37 | 97.18 | 1.392 | 1.00 |
| Complex Terrain | Segmented Hybrid GA | 5 | 30 | 275.45 | 64.42 | 97.23 | 0.615 | 1.00 |
| Complex Terrain | Transition-Aware Segmented Hybrid | 4 | 30 | 265.34 | 60.37 | 97.18 | 1.392 | 1.00 |
| USGS Cascadia 30 m High | Coverage-Preserving Segmented Hybrid | 1 | 22 | 72.92 | 14.78 | 98.44 | 1.750 | 1.00 |
| USGS Cascadia 30 m High | Coverage-Preserving Segmented Hybrid | 2 | 8 | 76.24 | 15.42 | 98.61 | 0.449 | 1.00 |
| USGS Cascadia 30 m High | Full Geometry-Aware Hybrid GA | 1 | 30 | 72.91 | 14.78 | 98.42 | 1.752 | 1.00 |
| USGS Cascadia 30 m High | Segmented Adaptive | 2 | 1 | 76.96 | 15.55 | 98.75 | 0.899 | 1.00 |
| USGS Cascadia 30 m High | Segmented Adaptive | 3 | 1 | 82.78 | 16.87 | 98.56 | 0.431 | 1.00 |
| USGS Cascadia 30 m High | Segmented Adaptive | 4 | 1 | 93.91 | 19.28 | 98.72 | 0.329 | 1.00 |
| USGS Cascadia 30 m High | Segmented Adaptive | 5 | 1 | 107.62 | 22.29 | 98.72 | 0.346 | 1.00 |
| USGS Cascadia 30 m High | Segmented Hybrid GA | 2 | 30 | 75.78 | 15.33 | 98.28 | 0.461 | 1.00 |
| USGS Cascadia 30 m High | Segmented Hybrid GA | 3 | 30 | 81.73 | 16.67 | 98.03 | 0.209 | 1.00 |
| USGS Cascadia 30 m High | Segmented Hybrid GA | 4 | 30 | 91.83 | 18.90 | 97.88 | 0.013 | 1.00 |
| USGS Cascadia 30 m High | Segmented Hybrid GA | 5 | 30 | 106.12 | 22.02 | 97.95 | 0.060 | 1.00 |
| USGS Cascadia 30 m High | Transition-Aware Segmented Hybrid | 1 | 30 | 72.91 | 14.78 | 98.42 | 1.752 | 1.00 |
