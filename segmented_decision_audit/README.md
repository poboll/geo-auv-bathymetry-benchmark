# Segmented decision audit

This directory summarizes the gate-aware blockwise fixed-line extension from
`segmented_heading_extension/segmented_heading_raw.csv`. It does not rerun
the planner; it recomputes the decision logic that determines when a
segmented-heading layout is accepted, rejected, or used only as a
coverage-preserving but transition-cost-dominated alternative.

The audit is a public-grid numerical planning artifact. It is not an AUV
controller, Dubins planner, mission-log replay, sea/lake/field validation,
hydrographic QA, or navigation-safety result.

## Key results

| Scene | CP selected | TA selected | Feasibility repairs | TA C (%) | TA Oex (%) | TA time delta vs single (%) | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| Complex Terrain | 30/30 | 30/30 | 30/30 | 97.18 | 1.392 | 17.00 | blockwise repair required |
| GEBCO Monterey Canyon | 14/30 | 14/30 | 0/30 | 99.74 | 0.049 | -5.31 | select blockwise when gates justify |
| GEBCO Mariana Trench | 0/30 | 0/30 | 0/30 | 99.02 | 0.126 | 0.00 | reject blockwise due to coverage gate |
| GEBCO Puerto Rico Trench | 0/30 | 0/30 | 0/30 | 98.08 | 0.274 | 0.00 | reject blockwise due to coverage gate |
| USGS Cascadia 30 m High | 8/30 | 0/30 | 0/30 | 98.42 | 1.752 | 0.00 | coverage selector finds cleanup; transition gate retains single |

Regeneration command:

```bash
conda run -n uu python make_segmented_decision_audit.py
```
