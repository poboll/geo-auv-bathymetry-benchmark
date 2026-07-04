# Submission Boundary Diagnostics

This diagnostic is a submission-facing audit, not a replacement for the main benchmark. It reruns the two primary GEBCO scenes and the USGS high-complexity crop under alternative declared swath-width caps and summarizes whether raw Hybrid GA refinements would pass a conservative operational acceptance gate against the deterministic Adaptive Spacing baseline.

- Hybrid seeds per scene/cap: 0--19
- Swath-width caps tested: 1200, 1800, and 2400 m.
- Gate diagnostic: accept raw Hybrid only if it is feasible, no worse than Adaptive by 0.05 pp in coverage and excess overlap, and no longer in path length; otherwise fall back to Adaptive.

## Wmax sensitivity summary for Hybrid GA

| Scene | Wmax (m) | Feas. rate | Path (km) | Coverage (%) | Excess overlap (%) | Lines |
|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia | 1200 | 1.00 | 22528.10 | 99.84 | 1.214 | 166.0 |
| GEBCO Cascadia | 1800 | 1.00 | 15038.16 | 98.97 | 0.106 | 116.0 |
| GEBCO Cascadia | 2400 | 1.00 | 11322.07 | 99.10 | 0.104 | 87.0 |
| GEBCO Monterey | 1200 | 1.00 | 9884.86 | 98.58 | 0.248 | 88.0 |
| GEBCO Monterey | 1800 | 1.00 | 6656.57 | 99.63 | 0.085 | 59.0 |
| GEBCO Monterey | 2400 | 1.00 | 4983.59 | 98.33 | 0.025 | 54.0 |
| USGS High | 1200 | 1.00 | 84.48 | 98.81 | 1.049 | 12.0 |
| USGS High | 1800 | 1.00 | 72.90 | 98.44 | 1.732 | 12.0 |
| USGS High | 2400 | 0.00 | 73.00 | 98.81 | 6.391 | 12.0 |

## Adaptive-vs-Hybrid practical significance and gate diagnostic

| Scene | Seeds | Median path gain vs Adaptive (%) | Median coverage delta (pp) | Median overlap delta (pp) | Score-better rate | Gate accept rate |
|---|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia | 20 | 0.0003 | -0.6667 | 0.0750 | 0.10 | 0.35 |
| GEBCO Monterey | 20 | 0.0004 | 0.0000 | 0.0219 | 0.10 | 0.40 |
| USGS High | 20 | 1.3684 | -0.1167 | -0.5157 | 1.00 | 0.30 |

## Reviewer-facing interpretation

- Changing the declared Wmax cap changes absolute line density and path totals, so the cap must remain a declared evaluator parameter.
- The qualitative regime interpretation is the main object of this audit: GEBCO remains a low-overlap public-prior benchmark, whereas USGS High remains the overlap-stressed transfer case.
- The conservative gate generally prevents raw GA seeds from being interpreted as operationally superior unless their route reduction is not purchased by lower coverage or higher overlap.
- These outputs should be cited as reproducibility artifacts and boundary diagnostics, not as deployment validation.
