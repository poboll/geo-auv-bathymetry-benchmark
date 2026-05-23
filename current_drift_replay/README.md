# Current-drift Replay

This diagnostic asks whether the fixed-line layouts retain coverage and overlap margin when a first-order current proxy is injected after planning.

The proxy does not claim hydrodynamic simulation. It maps current speed and direction into residual cross-track line drift, heading perturbation, low-frequency footprint variation, and terrain-coupled footprint shrinkage, then recomputes the same coverage and overlap metrics on the benchmark evaluator. For fair method comparison, each scene/scenario uses common random numbers across methods.

| Scene | Scenario | Method | Feasible | P05 coverage margin pp | P95 excess overlap | P95 residual drift (% spacing) |
|---|---|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | Mild | Fixed | 1.00 | +2.22 | 1.05 | 1.8 |
| GEBCO Cascadia Margin | Cross | Fixed | 1.00 | +1.83 | 1.29 | 7.0 |
| GEBCO Cascadia Margin | Adverse | Fixed | 0.96 | +0.68 | 2.86 | 17.0 |
| GEBCO Cascadia Margin | Mild | Hybrid | 1.00 | +1.67 | 0.06 | 1.8 |
| GEBCO Cascadia Margin | Cross | Hybrid | 1.00 | +1.67 | 0.36 | 7.0 |
| GEBCO Cascadia Margin | Adverse | Hybrid | 0.98 | +0.51 | 1.87 | 17.0 |
| GEBCO Cascadia Margin | Mild | UA-Hybrid | 1.00 | +1.67 | 0.00 | 1.8 |
| GEBCO Cascadia Margin | Cross | UA-Hybrid | 1.00 | +1.67 | 0.14 | 7.0 |
| GEBCO Cascadia Margin | Adverse | UA-Hybrid | 0.98 | +0.63 | 1.72 | 17.0 |
| GEBCO Monterey Canyon | Mild | Fixed | 1.00 | +2.12 | 0.88 | 1.8 |
| GEBCO Monterey Canyon | Cross | Fixed | 1.00 | +1.82 | 1.11 | 7.0 |
| GEBCO Monterey Canyon | Adverse | Fixed | 0.96 | +0.52 | 2.51 | 16.9 |
| GEBCO Monterey Canyon | Mild | Hybrid | 1.00 | +2.12 | 0.00 | 1.8 |
| GEBCO Monterey Canyon | Cross | Hybrid | 1.00 | +1.48 | 0.23 | 7.0 |
| GEBCO Monterey Canyon | Adverse | Hybrid | 0.90 | -0.55 | 1.80 | 17.0 |
| GEBCO Monterey Canyon | Mild | UA-Hybrid | 1.00 | +2.99 | 0.03 | 1.8 |
| GEBCO Monterey Canyon | Cross | UA-Hybrid | 1.00 | +2.92 | 0.04 | 7.0 |
| GEBCO Monterey Canyon | Adverse | UA-Hybrid | 0.96 | +0.37 | 0.91 | 17.0 |
| USGS Cascadia 30 m High | Mild | Fixed | 0.00 | -0.05 | 30.10 | 1.8 |
| USGS Cascadia 30 m High | Cross | Fixed | 0.00 | -0.36 | 30.58 | 7.0 |
| USGS Cascadia 30 m High | Adverse | Fixed | 0.00 | -1.29 | 31.68 | 16.9 |
| USGS Cascadia 30 m High | Mild | Hybrid | 1.00 | +1.45 | 1.69 | 1.8 |
| USGS Cascadia 30 m High | Cross | Hybrid | 1.00 | +1.21 | 2.11 | 7.0 |
| USGS Cascadia 30 m High | Adverse | Hybrid | 0.86 | +0.03 | 3.66 | 17.0 |
| USGS Cascadia 30 m High | Mild | UA-Hybrid | 1.00 | +1.62 | 1.83 | 1.8 |
| USGS Cascadia 30 m High | Cross | UA-Hybrid | 1.00 | +1.33 | 2.11 | 7.0 |
| USGS Cascadia 30 m High | Adverse | UA-Hybrid | 0.86 | -0.68 | 2.98 | 17.0 |

Interpretation: if the adverse-current cells remain bordered, the correct manuscript claim is not that the planner is field-ready. It is that the fixed-line geometry needs a current/controller-aware execution layer before operational deployment.
