# Vehicle-Aware Post-Evaluation

This diagnostic converts planned line-family outputs into a first-order vehicle-execution proxy. It adds semicircular line-change arcs for declared minimum turn radii and converts distance into time using 1.5 m/s for survey/transit distance and 0.75 m/s for turn arcs. The diagnostic is not a Dubins controller, current model, SLAM replay, or sea-trial validation.

## Selected R=100 m Results

| Evidence block | Scene | Method | Runs | Feasible | Lines | Turn changes | Effective length (km) | Mission time (h) | Time gain vs Fixed (%) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| main_benchmark | GEBCO Cascadia Margin | Adaptive Spacing w/o GA | 1 | 1.00 | 116.0 | 115.0 | 15074.35 | 2798.24 | 0.85 |
| main_benchmark | GEBCO Cascadia Margin | Fixed-Spacing | 1 | 1.00 | 117.0 | 116.0 | 15203.15 | 2822.15 | 0.00 |
| main_benchmark | GEBCO Cascadia Margin | Full Geometry-Aware Hybrid GA | 50 | 1.00 | 116.0 | 115.0 | 15074.28 | 2798.22 | 0.85 |
| main_benchmark | GEBCO Monterey Canyon | Adaptive Spacing w/o GA | 1 | 1.00 | 59.0 | 58.0 | 6674.84 | 1239.46 | 0.78 |
| main_benchmark | GEBCO Monterey Canyon | Fixed-Spacing | 1 | 1.00 | 73.0 | 72.0 | 6723.14 | 1249.21 | 0.00 |
| main_benchmark | GEBCO Monterey Canyon | Full Geometry-Aware Hybrid GA | 50 | 1.00 | 59.0 | 58.0 | 6674.79 | 1239.45 | 0.78 |
| segmented_diagnostic | Complex Terrain | Full Geometry-Aware Hybrid GA | 30 | 0.00 | 40.0 | 39.0 | 266.39 | 51.60 | 24.69 |
| segmented_diagnostic | Complex Terrain | Transition-Aware Segmented Hybrid | 30 | 1.00 | 100.0 | 96.0 | 295.50 | 60.37 | 11.89 |
| usgs_extension | USGS Cascadia 30 m High | Adaptive Spacing w/o GA | 1 | 1.00 | 12.0 | 11.0 | 77.35 | 14.96 | 22.43 |
| usgs_extension | USGS Cascadia 30 m High | Fixed-Spacing | 1 | 0.00 | 12.0 | 11.0 | 100.71 | 19.29 | 0.00 |
| usgs_extension | USGS Cascadia 30 m High | Full Geometry-Aware Hybrid GA | 20 | 1.00 | 12.0 | 11.0 | 76.36 | 14.78 | 23.38 |

## Interpretation

- GEBCO public-scene gains remain modest under the turn-radius proxy, which is consistent with the paper's bounded public-grid claim.
- Monterey benefits slightly more after adding turn arcs because the terrain-aware layouts use fewer lines than Fixed-Spacing.
- The USGS high-complexity crop retains a large mission-time proxy gain because terrain-aware planning removes the high-overlap fixed-spacing burden.
- The transition-aware segmented synthetic-complex repair improves feasibility and is selected with the same first-order mission-time proxy used in this post-evaluation, but it should remain framed as a numerical repair direction until a full vehicle-dynamics route builder is added.
