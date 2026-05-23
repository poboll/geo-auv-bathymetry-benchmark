# Execution-risk-aware Refinement

This diagnostic moves part of the current/heading/footprint execution risk into candidate-layout refinement rather than using it only as post-hoc replay.

ER-Hybrid should be treated as a numerical stress-objective check. It does not model closed-loop control, hydrodynamics, sound-speed uncertainty, or mission logs.

## Selected Layouts

| Scene | Heading | Lines | Path km | Nominal coverage | Nominal excess overlap | Stress min coverage | Stress max overlap |
|---|---:|---:|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | 0.0 | 116 | 15038.15 | 99.33 | 0.02 | 97.87 | 0.01 |
| GEBCO Monterey Canyon | 75.0 | 72 | 6319.00 | 100.00 | 0.00 | 98.51 | 0.04 |
| USGS Cascadia 30 m High | 135.0 | 13 | 73.77 | 99.24 | 1.65 | 97.80 | 1.57 |

## Current Replay Summary

| Scene | Scenario | Method | Feasible | P05 coverage margin pp | P95 excess overlap | Path cost vs Hybrid |
|---|---|---:|---:|---:|---:|---:|
| GEBCO Cascadia Margin | Mild | Hybrid | 1.00 | +1.67 | 0.06 | +0.00 |
| GEBCO Cascadia Margin | Cross | Hybrid | 1.00 | +1.67 | 0.40 | +0.00 |
| GEBCO Cascadia Margin | Adverse | Hybrid | 0.98 | +0.31 | 1.91 | +0.00 |
| GEBCO Cascadia Margin | Mild | UA-Hybrid | 1.00 | +1.67 | 0.00 | +0.00 |
| GEBCO Cascadia Margin | Cross | UA-Hybrid | 1.00 | +1.67 | 0.16 | +0.00 |
| GEBCO Cascadia Margin | Adverse | UA-Hybrid | 0.99 | +0.46 | 1.77 | +0.00 |
| GEBCO Cascadia Margin | Mild | CA-Hybrid | 1.00 | +1.67 | 0.00 | +0.00 |
| GEBCO Cascadia Margin | Cross | CA-Hybrid | 1.00 | +1.67 | 0.16 | +0.00 |
| GEBCO Cascadia Margin | Adverse | CA-Hybrid | 0.99 | +0.46 | 1.77 | +0.00 |
| GEBCO Cascadia Margin | Mild | ER-Hybrid | 1.00 | +1.67 | 0.06 | +0.00 |
| GEBCO Cascadia Margin | Cross | ER-Hybrid | 1.00 | +1.67 | 0.40 | +0.00 |
| GEBCO Cascadia Margin | Adverse | ER-Hybrid | 0.98 | +0.31 | 1.91 | +0.00 |
| GEBCO Monterey Canyon | Mild | Hybrid | 1.00 | +2.12 | 0.00 | +0.00 |
| GEBCO Monterey Canyon | Cross | Hybrid | 1.00 | +1.60 | 0.18 | +0.00 |
| GEBCO Monterey Canyon | Adverse | Hybrid | 0.91 | -0.23 | 1.91 | +0.00 |
| GEBCO Monterey Canyon | Mild | UA-Hybrid | 1.00 | +2.99 | 0.02 | -5.07 |
| GEBCO Monterey Canyon | Cross | UA-Hybrid | 1.00 | +2.93 | 0.03 | -5.07 |
| GEBCO Monterey Canyon | Adverse | UA-Hybrid | 0.94 | -0.10 | 0.75 | -5.07 |
| GEBCO Monterey Canyon | Mild | CA-Hybrid | 1.00 | +2.99 | 0.02 | -5.07 |
| GEBCO Monterey Canyon | Cross | CA-Hybrid | 1.00 | +2.93 | 0.03 | -5.07 |
| GEBCO Monterey Canyon | Adverse | CA-Hybrid | 0.94 | -0.10 | 0.75 | -5.07 |
| GEBCO Monterey Canyon | Mild | ER-Hybrid | 1.00 | +2.99 | 0.02 | -5.07 |
| GEBCO Monterey Canyon | Cross | ER-Hybrid | 1.00 | +2.93 | 0.03 | -5.07 |
| GEBCO Monterey Canyon | Adverse | ER-Hybrid | 0.94 | -0.10 | 0.75 | -5.07 |
| USGS Cascadia 30 m High | Mild | Hybrid | 1.00 | +1.46 | 1.71 | +0.00 |
| USGS Cascadia 30 m High | Cross | Hybrid | 1.00 | +1.15 | 2.22 | +0.00 |
| USGS Cascadia 30 m High | Adverse | Hybrid | 0.84 | +0.23 | 4.12 | +0.00 |
| USGS Cascadia 30 m High | Mild | UA-Hybrid | 1.00 | +1.63 | 1.86 | -0.63 |
| USGS Cascadia 30 m High | Cross | UA-Hybrid | 1.00 | +1.29 | 2.15 | -0.63 |
| USGS Cascadia 30 m High | Adverse | UA-Hybrid | 0.87 | -0.03 | 3.29 | -0.63 |
| USGS Cascadia 30 m High | Mild | CA-Hybrid | 1.00 | +1.76 | 1.49 | -1.04 |
| USGS Cascadia 30 m High | Cross | CA-Hybrid | 1.00 | +1.48 | 1.89 | -1.04 |
| USGS Cascadia 30 m High | Adverse | CA-Hybrid | 0.87 | +0.18 | 3.62 | -1.04 |
| USGS Cascadia 30 m High | Mild | ER-Hybrid | 1.00 | +2.15 | 1.80 | +1.23 |
| USGS Cascadia 30 m High | Cross | ER-Hybrid | 1.00 | +1.93 | 2.31 | +1.23 |
| USGS Cascadia 30 m High | Adverse | ER-Hybrid | 0.86 | +0.99 | 4.07 | +1.23 |

## Interpretation

- GEBCO Cascadia Margin: adverse-current feasible-rate change versus Hybrid is +0.000, P95 overlap change is +0.00 percentage points, and path-cost change is +0.00 percent.
- GEBCO Monterey Canyon: adverse-current feasible-rate change versus Hybrid is +0.027, P95 overlap change is -1.16 percentage points, and path-cost change is -5.07 percent.
- USGS Cascadia 30 m High: adverse-current feasible-rate change versus Hybrid is +0.027, P95 overlap change is -0.05 percentage points, and path-cost change is +1.23 percent.

Manuscript decision rule: promote ER-Hybrid only if it improves adverse-current feasibility or lower-tail coverage without violating the 3 percent overlap gate or adding more than 2 percent path cost. Otherwise retain it as supplemental negative/boundary evidence that true execution-aware planning needs controller or mission-log data.
