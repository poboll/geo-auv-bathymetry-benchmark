# Uncertainty-aware Margin Replay

This experiment asks whether a declared execution-error envelope can be used to select an execution-aware pre-mission line-layout margin before field execution.

It does not claim closed-loop vehicle control. It selects target-overlap and swath-quantile margins, optionally accepting GA cleanup only when nominal coverage and overlap gates are preserved.

## Selected Margins

| Scene | Target overlap | Quantile | GA cleanup | Lines | Nominal coverage | Nominal excess overlap |
|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | 0.15 | 0.18 | 1 | 116 | 99.33 | 0.00 |
| GEBCO Monterey Canyon | 0.10 | 0.18 | 0 | 72 | 100.00 | 0.00 |
| USGS Cascadia 30 m High | 0.10 | 0.34 | 0 | 12 | 98.69 | 1.76 |

## Replay Summary

| Scene | Scenario | Method | Feasible | P05 coverage margin pp | P95 excess overlap | Path cost vs Hybrid |
|---|---|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | moderate_noise | Fixed | 0.98 | +1.80 | 2.66 | +0.85 |
| GEBCO Cascadia Margin | strong_noise | Fixed | 0.22 | -1.91 | 6.22 | +0.85 |
| GEBCO Cascadia Margin | moderate_noise | Adaptive | 1.00 | +1.57 | 1.72 | +0.00 |
| GEBCO Cascadia Margin | strong_noise | Adaptive | 0.40 | -2.40 | 5.40 | +0.00 |
| GEBCO Cascadia Margin | moderate_noise | Hybrid | 1.00 | +1.34 | 1.89 | +0.00 |
| GEBCO Cascadia Margin | strong_noise | Hybrid | 0.35 | -2.48 | 5.51 | +0.00 |
| GEBCO Cascadia Margin | moderate_noise | UA-Hybrid | 1.00 | +1.57 | 1.72 | +0.00 |
| GEBCO Cascadia Margin | strong_noise | UA-Hybrid | 0.40 | -2.40 | 5.40 | +0.00 |
| GEBCO Monterey Canyon | moderate_noise | Fixed | 0.99 | +1.69 | 2.48 | +0.66 |
| GEBCO Monterey Canyon | strong_noise | Fixed | 0.27 | -1.82 | 6.64 | +0.66 |
| GEBCO Monterey Canyon | moderate_noise | Adaptive | 1.00 | +1.48 | 1.68 | +0.00 |
| GEBCO Monterey Canyon | strong_noise | Adaptive | 0.35 | -2.54 | 5.04 | +0.00 |
| GEBCO Monterey Canyon | moderate_noise | Hybrid | 1.00 | +1.48 | 1.68 | +0.00 |
| GEBCO Monterey Canyon | strong_noise | Hybrid | 0.35 | -2.54 | 5.04 | +0.00 |
| GEBCO Monterey Canyon | moderate_noise | UA-Hybrid | 1.00 | +1.91 | 0.57 | -5.07 |
| GEBCO Monterey Canyon | strong_noise | UA-Hybrid | 0.58 | -3.19 | 3.25 | -5.07 |
| USGS Cascadia 30 m High | moderate_noise | Fixed | 0.00 | -0.58 | 32.27 | +33.46 |
| USGS Cascadia 30 m High | strong_noise | Fixed | 0.00 | -1.82 | 34.13 | +33.46 |
| USGS Cascadia 30 m High | moderate_noise | Adaptive | 0.68 | +0.82 | 4.18 | +1.40 |
| USGS Cascadia 30 m High | strong_noise | Adaptive | 0.34 | -0.87 | 6.77 | +1.40 |
| USGS Cascadia 30 m High | moderate_noise | Hybrid | 0.86 | +0.69 | 3.52 | +0.00 |
| USGS Cascadia 30 m High | strong_noise | Hybrid | 0.44 | -1.02 | 5.83 | +0.00 |
| USGS Cascadia 30 m High | moderate_noise | UA-Hybrid | 0.95 | +0.82 | 2.98 | -0.63 |
| USGS Cascadia 30 m High | strong_noise | UA-Hybrid | 0.47 | -2.11 | 4.92 | -0.63 |

Interpretation: useful if UA-Hybrid raises strong-noise feasibility without making moderate-noise overlap unsafe. If strong-noise cells remain bordered, that is an evidence boundary rather than a styling problem: it means the manuscript should call for vehicle/controller-level margins rather than claiming field readiness.
