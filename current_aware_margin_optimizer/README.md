# Current-aware Margin Optimizer

This experiment moves the current-drift proxy from post-hoc replay into pre-mission margin selection.

CA-Hybrid sweeps target-overlap and swath-quantile margins, scores each candidate under cross-current and adverse-current replay, then evaluates the selected layout with independent Monte Carlo seeds. It remains a margin selector, not closed-loop control or hydrodynamic simulation.

## UA/CA Convergence Check

With common random numbers across methods, the maximum absolute UA-Hybrid versus CA-Hybrid delta across feasible rate, P05 coverage, P95 excess overlap, path length, and path-cost metrics is 0.407653. The current-aware selector differs from the existing uncertainty-aware margin selector on at least one scene/scenario; manuscript integration should be based on whether the difference improves adverse-current feasibility without adding unacceptable path cost.

## Selected Margins

| Scene | Target overlap | Quantile | GA cleanup | Lines | Nominal coverage | Nominal excess overlap |
|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | 0.15 | 0.18 | 1 | 116 | 99.33 | 0.00 |
| GEBCO Monterey Canyon | 0.10 | 0.18 | 0 | 72 | 100.00 | 0.00 |
| USGS Cascadia 30 m High | 0.10 | 0.30 | 1 | 12 | 98.83 | 1.42 |

## Final Replay Summary

| Scene | Scenario | Method | Feasible | P05 coverage margin pp | P95 excess overlap | Path cost vs Hybrid |
|---|---|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | Mild | Fixed | 1.00 | +2.21 | 1.01 | +0.85 |
| GEBCO Cascadia Margin | Cross | Fixed | 1.00 | +1.91 | 1.30 | +0.85 |
| GEBCO Cascadia Margin | Adverse | Fixed | 0.93 | +0.49 | 2.89 | +0.85 |
| GEBCO Cascadia Margin | Mild | Hybrid | 1.00 | +1.67 | 0.06 | +0.00 |
| GEBCO Cascadia Margin | Cross | Hybrid | 1.00 | +1.67 | 0.36 | +0.00 |
| GEBCO Cascadia Margin | Adverse | Hybrid | 0.98 | +0.39 | 2.07 | +0.00 |
| GEBCO Cascadia Margin | Mild | UA-Hybrid | 1.00 | +1.67 | 0.00 | +0.00 |
| GEBCO Cascadia Margin | Cross | UA-Hybrid | 1.00 | +1.67 | 0.14 | +0.00 |
| GEBCO Cascadia Margin | Adverse | UA-Hybrid | 0.99 | +0.52 | 1.93 | +0.00 |
| GEBCO Cascadia Margin | Mild | CA-Hybrid | 1.00 | +1.67 | 0.00 | +0.00 |
| GEBCO Cascadia Margin | Cross | CA-Hybrid | 1.00 | +1.67 | 0.14 | +0.00 |
| GEBCO Cascadia Margin | Adverse | CA-Hybrid | 0.99 | +0.52 | 1.93 | +0.00 |
| GEBCO Monterey Canyon | Mild | Fixed | 1.00 | +2.12 | 0.88 | +0.66 |
| GEBCO Monterey Canyon | Cross | Fixed | 1.00 | +1.79 | 1.11 | +0.66 |
| GEBCO Monterey Canyon | Adverse | Fixed | 0.94 | +0.41 | 2.91 | +0.66 |
| GEBCO Monterey Canyon | Mild | Hybrid | 1.00 | +2.03 | 0.00 | +0.00 |
| GEBCO Monterey Canyon | Cross | Hybrid | 1.00 | +1.55 | 0.20 | +0.00 |
| GEBCO Monterey Canyon | Adverse | Hybrid | 0.92 | -0.45 | 2.06 | +0.00 |
| GEBCO Monterey Canyon | Mild | UA-Hybrid | 1.00 | +2.99 | 0.03 | -5.07 |
| GEBCO Monterey Canyon | Cross | UA-Hybrid | 1.00 | +2.92 | 0.03 | -5.07 |
| GEBCO Monterey Canyon | Adverse | UA-Hybrid | 0.96 | +0.13 | 0.86 | -5.07 |
| GEBCO Monterey Canyon | Mild | CA-Hybrid | 1.00 | +2.99 | 0.03 | -5.07 |
| GEBCO Monterey Canyon | Cross | CA-Hybrid | 1.00 | +2.92 | 0.03 | -5.07 |
| GEBCO Monterey Canyon | Adverse | CA-Hybrid | 0.96 | +0.13 | 0.86 | -5.07 |
| USGS Cascadia 30 m High | Mild | Fixed | 0.00 | -0.05 | 30.11 | +33.46 |
| USGS Cascadia 30 m High | Cross | Fixed | 0.00 | -0.44 | 30.54 | +33.46 |
| USGS Cascadia 30 m High | Adverse | Fixed | 0.00 | -1.53 | 32.28 | +33.46 |
| USGS Cascadia 30 m High | Mild | Hybrid | 1.00 | +1.44 | 1.69 | +0.00 |
| USGS Cascadia 30 m High | Cross | Hybrid | 1.00 | +1.13 | 2.11 | +0.00 |
| USGS Cascadia 30 m High | Adverse | Hybrid | 0.87 | +0.31 | 3.85 | +0.00 |
| USGS Cascadia 30 m High | Mild | UA-Hybrid | 1.00 | +1.61 | 1.84 | -0.63 |
| USGS Cascadia 30 m High | Cross | UA-Hybrid | 1.00 | +1.34 | 2.08 | -0.63 |
| USGS Cascadia 30 m High | Adverse | UA-Hybrid | 0.89 | +0.13 | 3.15 | -0.63 |
| USGS Cascadia 30 m High | Mild | CA-Hybrid | 1.00 | +1.77 | 1.48 | -1.04 |
| USGS Cascadia 30 m High | Cross | CA-Hybrid | 1.00 | +1.48 | 1.85 | -1.04 |
| USGS Cascadia 30 m High | Adverse | CA-Hybrid | 0.90 | +0.26 | 3.44 | -1.04 |

Interpretation: CA-Hybrid is useful only where it improves adverse-current feasibility or overlap tails without erasing coverage or path efficiency. In the present common-random-number run, it differs from UA-Hybrid only on the hardest USGS case and shows a mixed trade-off: slightly better adverse-current feasibility and coverage margin, but a worse overlap tail that still exceeds the 3 percent gate. This is supplemental trade-off evidence, not a new headline contribution. Negative or marginal cells should be reported as the boundary where current/controller-aware planning must replace fixed-line margin selection.
