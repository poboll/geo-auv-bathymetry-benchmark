# Structured Prior-error Replay

This diagnostic plans on spatially perturbed prior bathymetry and replays the same line family on the truth grid.

- Seeds per scenario: 20
- USGS high-complexity crop included: True
- Scenarios: nominal, correlated low-frequency bias, slope-amplified bias, localized canyon-wall bias.

| Scene | Scenario | Method | Feasible | Coverage margin pp | Excess overlap % | Path gain vs truth Fixed % | Prior RMSE m |
|---|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | Nominal | Fixed | 1.00 | +3.00 | 0.80 | 0.00 | 0.0 |
| GEBCO Cascadia Margin | Nominal | Adaptive | 1.00 | +2.33 | 0.00 | 0.85 | 0.0 |
| GEBCO Cascadia Margin | Nominal | Hybrid | 1.00 | +1.97 | 0.11 | 0.85 | 0.0 |
| GEBCO Cascadia Margin | Correlated bias | Fixed | 1.00 | +3.00 | 0.80 | 0.00 | 35.0 |
| GEBCO Cascadia Margin | Correlated bias | Adaptive | 1.00 | +2.33 | 0.00 | 0.85 | 35.0 |
| GEBCO Cascadia Margin | Correlated bias | Hybrid | 1.00 | +1.97 | 0.11 | 0.85 | 35.0 |
| GEBCO Cascadia Margin | Slope amplified | Fixed | 1.00 | +3.00 | 0.80 | 0.00 | 28.2 |
| GEBCO Cascadia Margin | Slope amplified | Adaptive | 1.00 | +2.33 | 0.00 | 0.85 | 28.2 |
| GEBCO Cascadia Margin | Slope amplified | Hybrid | 1.00 | +1.97 | 0.11 | 0.85 | 28.2 |
| GEBCO Cascadia Margin | Local wall bias | Fixed | 1.00 | +3.00 | 0.80 | 0.00 | 24.1 |
| GEBCO Cascadia Margin | Local wall bias | Adaptive | 1.00 | +2.33 | 0.00 | 0.85 | 24.1 |
| GEBCO Cascadia Margin | Local wall bias | Hybrid | 1.00 | +1.97 | 0.11 | 0.85 | 24.1 |
| GEBCO Monterey Canyon | Nominal | Fixed | 1.00 | +2.33 | 0.81 | 0.00 | 0.0 |
| GEBCO Monterey Canyon | Nominal | Adaptive | 1.00 | +3.00 | 0.00 | 0.66 | 0.0 |
| GEBCO Monterey Canyon | Nominal | Hybrid | 1.00 | +2.63 | 0.08 | 0.66 | 0.0 |
| GEBCO Monterey Canyon | Correlated bias | Fixed | 1.00 | +2.33 | 0.81 | 0.00 | 35.0 |
| GEBCO Monterey Canyon | Correlated bias | Adaptive | 1.00 | +3.00 | 0.00 | 0.66 | 35.0 |
| GEBCO Monterey Canyon | Correlated bias | Hybrid | 1.00 | +2.63 | 0.08 | 0.66 | 35.0 |
| GEBCO Monterey Canyon | Slope amplified | Fixed | 1.00 | +2.33 | 0.81 | 0.00 | 30.9 |
| GEBCO Monterey Canyon | Slope amplified | Adaptive | 1.00 | +3.00 | 0.00 | 0.66 | 30.9 |
| GEBCO Monterey Canyon | Slope amplified | Hybrid | 1.00 | +2.63 | 0.08 | 0.66 | 30.9 |
| GEBCO Monterey Canyon | Local wall bias | Fixed | 1.00 | +2.33 | 0.81 | 0.00 | 27.2 |
| GEBCO Monterey Canyon | Local wall bias | Adaptive | 1.00 | +3.00 | 0.00 | 0.66 | 27.2 |
| GEBCO Monterey Canyon | Local wall bias | Hybrid | 1.00 | +2.63 | 0.08 | 0.66 | 27.2 |
| USGS Cascadia 30 m High | Nominal | Fixed | 0.00 | +0.20 | 29.96 | 0.00 | 0.0 |
| USGS Cascadia 30 m High | Nominal | Adaptive | 1.00 | +1.55 | 2.24 | 24.02 | 0.0 |
| USGS Cascadia 30 m High | Nominal | Hybrid | 1.00 | +1.44 | 1.73 | 25.04 | 0.0 |
| USGS Cascadia 30 m High | Correlated bias | Fixed | 0.00 | -0.22 | 27.35 | 4.23 | 35.0 |
| USGS Cascadia 30 m High | Correlated bias | Adaptive | 0.95 | +1.88 | 2.18 | 23.74 | 35.0 |
| USGS Cascadia 30 m High | Correlated bias | Hybrid | 1.00 | +1.73 | 1.53 | 24.90 | 35.0 |
| USGS Cascadia 30 m High | Slope amplified | Fixed | 0.00 | +0.25 | 30.28 | -1.15 | 34.4 |
| USGS Cascadia 30 m High | Slope amplified | Adaptive | 0.90 | +1.84 | 2.34 | 23.83 | 34.4 |
| USGS Cascadia 30 m High | Slope amplified | Hybrid | 1.00 | +1.70 | 1.61 | 24.94 | 34.4 |
| USGS Cascadia 30 m High | Local wall bias | Fixed | 0.00 | +0.10 | 29.59 | 0.39 | 28.6 |
| USGS Cascadia 30 m High | Local wall bias | Adaptive | 0.95 | +1.91 | 2.51 | 23.28 | 28.6 |
| USGS Cascadia 30 m High | Local wall bias | Hybrid | 1.00 | +1.82 | 1.76 | 24.38 | 28.6 |

Interpretation: this is a prior-map robustness stress test, not a field validation. It is intended to identify whether the geometry-aware line family survives spatially structured map error before stronger mission-log or simulator evidence is available.
