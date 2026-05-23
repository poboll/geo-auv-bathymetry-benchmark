# Threshold and Local-failure Diagnostics

This extension rebuilds the two primary GEBCO scenes and the USGS high-complexity public-grid crop, then evaluates whether scene-level means hide stricter threshold or local failure modes.

- Hybrid GA seeds: 0--19
- Coverage thresholds: 95%, 97%, 98%, 99%, 99.5%
- Mean-excess-overlap gates: 1%, 2%, 3%, 5%
- Local metrics: uncovered components, largest uncovered patch, p95/p99/max cellwise excess overlap.

| Scene | Method | C mean (%) | O mean (%) | C99/O2 pass rate | Largest gap (%) | p99 cell excess (%) |
|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia | Fixed | 100.00 | 0.799 | 1.00 | 0.000 | 59.89 |
| GEBCO Cascadia | Adaptive | 99.33 | 0.000 | 1.00 | 0.667 | 0.00 |
| GEBCO Cascadia | Hybrid | 98.97 | 0.106 | 0.45 | 0.667 | 2.71 |
| GEBCO Monterey | Fixed | 99.33 | 0.815 | 1.00 | 0.667 | 30.56 |
| GEBCO Monterey | Adaptive | 100.00 | 0.000 | 1.00 | 0.000 | 0.00 |
| GEBCO Monterey | Hybrid | 99.63 | 0.085 | 1.00 | 0.375 | 2.64 |
| USGS High | Fixed | 97.20 | 29.960 | 0.00 | 0.661 | 58.45 |
| USGS High | Adaptive | 98.55 | 2.237 | 0.00 | 0.583 | 25.26 |
| USGS High | Hybrid | 98.44 | 1.732 | 0.00 | 0.555 | 26.03 |

## Interpretation

- The default 97%/3% benchmark gate is not equivalent to a stricter hydrographic acceptance rule.
- The USGS high-complexity crop remains the strongest positive case because Fixed-Spacing carries a very large overlap burden while Hybrid remains feasible under the default gate.
- Under stricter 99%/2% screening, the GEBCO Hybrid layouts are not uniformly accepted, which should be reported as margin limitation rather than hidden.
- Largest uncovered-patch and p99-overlap metrics help expose local failure that scene-level means can obscure; they remain numerical raster-evaluator diagnostics, not survey-grade QA.
