# External Heuristic Turning-cost Audit

This diagnostic extends the v28 external survey-layout audit with a simple execution-cost proxy. For each fixed-line layout, it adds a semicircular line-change penalty \((N-1)\pi R_{min}\) and converts the geometric path plus turn arcs into mission time using declared speeds.

## Assumptions

- Minimum-turn-radius values: 25, 50, 100, 200 m.
- Survey/transit speed: 1.50 m/s.
- Turn-arc speed: 0.75 m/s.
- Coverage and overlap feasibility are not recomputed because the line family is unchanged; this is a post-planning execution-cost audit only.
- The proxy is not a Dubins controller, hydrodynamic model, mission-log replay, field validation, or hydrographic QA.

## Summary at R100 and R200

| Method | Feasible windows | Median mission-time gain R100 (%) | Positive windows R100 | Median mission-time gain R200 (%) | Positive windows R200 | Median turn-arc share R100 (%) |
|---|---:|---:|---:|---:|---:|---:|
| Min-span | 6/9 | 0.654 | 8/9 | 0.787 | 8/9 | 0.173 |
| Contour | 6/9 | 0.050 | 5/9 | 0.000 | 4/9 | 0.219 |
| Geom-short | 8/9 | 0.434 | 7/9 | 0.471 | 7/9 | 0.194 |
| Adaptive | 9/9 | 0.682 | 7/9 | 0.682 | 7/9 | 0.240 |
| Hybrid s0 | 9/9 | 0.682 | 7/9 | 0.682 | 7/9 | 0.240 |
