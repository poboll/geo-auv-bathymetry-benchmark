# Side-specific Footprint Validity Audit

This directory records the planning-evaluator validity audit added for the v25 manuscript revision.

## Purpose

The main manuscript evaluator uses a total-width raster proxy for predicted MBES coverage and adjacent-spacing overlap. This audit checks whether preserving separate port and starboard footprint reach estimates changes the benchmark interpretation on representative layouts.

The audit is a planning-layer check. It is not beam-level acoustic ray tracing, raw MBES line-product validation, a deployment, or hydrographic quality assurance.

## Command

Run from the repository root:

```bash
conda run -n uu python make_footprint_validity_audit.py
```

## Inputs

- `geo_public_bathy_benchmark.py`: core scene loaders, planner variants, and total-width evaluator.
- `make_threshold_local_failure_extension.py`: shared scene loading for the two GEBCO public scenes and the USGS high-complexity crop.

## Outputs

- `footprint_validity_raw.csv`: row-level proxy-vs-side-specific metrics for Fixed-Spacing, Adaptive Spacing without GA, and representative seed-0 Hybrid layouts.
- `footprint_validity_summary.json`: aggregate summary used by the manuscript.
- `journal_footprint_validity_audit.png`: compact figure copied into both manuscript figure directories.

## Key Result

Across nine representative scene-method layouts, preserving port/starboard reach asymmetry causes zero changes in the declared `C97/O3` feasibility decision. The maximum absolute coverage difference is 0.50 percentage points, and the maximum absolute mean excess-overlap difference is 1.217 percentage points. The largest local cell-count disagreement appears on the USGS high-complexity crop, reaching 10.42% for Fixed-Spacing and 7.66--8.31% for the terrain-aware layouts.

The intended interpretation is therefore bounded: the benchmark conclusion is stable under this stronger planning-layer footprint check, but the evaluator still does not replace beam-level, attitude-aware, sound-speed-aware, or raw-MBES product QA.
