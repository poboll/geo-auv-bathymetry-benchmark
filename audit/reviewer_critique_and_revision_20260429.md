# Reviewer-Style Critique and Revision Record, 2026-04-29

## If I Were a Reviewer

### Major Concern 1: The study is still a numerical benchmark, not field validation.

**Likely criticism.** The paper uses public gridded bathymetry and synthetic terrains, but does not execute AUV missions, replay mission logs, or validate against raw MBES survey tracks.

**Revision made.**

- The manuscript explicitly states that the contribution is a public-bathymetry numerical benchmark, not a sea-trial or operational validation study.
- The Discussion and risk matrix now distinguish public-grid evidence, survey-grade data needs, mission-log replay, and execution uncertainty.

**Residual risk.** This cannot be fully solved without real survey-grade data or mission logs. The paper is now honest and defensible, but not equivalent to field validation.

### Major Concern 2: Only two primary public GEBCO scenes may look thin for a Q2 journal.

**Likely criticism.** Two public scenes cannot establish geographic representativeness.

**Revision made.**

- The paper now foregrounds that the GEBCO pair is the primary public-bathymetry benchmark, while synthetic terrains isolate mechanism and failure mode.
- The separate USGS Southern Cascadia 30 m extension is now explicitly framed as an independent public-grid check that changes data source, grid resolution, coordinate processing, and crop selection.
- The risk matrix now states that the study makes no representativeness claim across all seabed types.

**Residual risk.** A reviewer may still request more public scenes. The most valuable future experiment is adding 3--5 more public bathymetry regions from different geomorphic settings.

### Major Concern 3: Baseline comparison is narrow.

**Likely criticism.** The manuscript does not directly compare against online SLAM planners, cooperative multi-AUV CPP, or energy/dynamics-aware planners.

**Revision made.**

- A new comparator-scope paragraph was added to the evaluation protocol.
- The paper now explains that the comparator ladder is deliberately constrained to fixed-pattern line-layout variants evaluated by the same terrain-aware MBES model, so the ablation isolates spacing, heading, and GA-refinement effects.
- The risk matrix now includes `Comparator scope is narrow`.

**Residual risk.** The paper should not claim superiority over broader autonomy stacks. A future Q1-level version would need mission-level baselines.

### Major Concern 4: Sensor and planning parameters may be overfit.

**Likely criticism.** Results might depend on the chosen MBES opening angle, overlap margin, public-grid resolution, or prior-map assumptions.

**Revision made.**

- Added a public-scene sensitivity diagnostics table covering:
  - MBES opening angle \(100^\circ\)--\(130^\circ\);
  - target-overlap margin 10--20%;
  - native/\(2\times\)/\(3\times\) public-grid resolution;
  - simple global prior depth bias and relief scaling.
- Updated Methods, Results, Discussion, Conclusion, and risk matrix to reference these diagnostics.

**Residual risk.** The diagnostics still do not model spatially structured prior-map error, navigation drift, sound-speed uncertainty, or vehicle dynamics.

### Major Concern 5: Algorithmic novelty may be seen as incremental.

**Likely criticism.** The GA mostly refines adaptive spacing and does not provide the main path-length gain.

**Revision made.**

- The paper no longer oversells GA as the sole novelty.
- The novelty is framed as a controlled geometry-aware fixed-pattern benchmark: terrain-aware MBES swath modeling + orientation scan + adaptive spacing + GA refinement + public-grid evidence + failure-boundary analysis.
- Results state that adaptive spacing provides most public path shortening, while GA improves residual-overlap cleanup and seed-level layout stability.

**Residual risk.** The method novelty is sufficient for a careful Q2 attempt if the benchmark story is accepted, but it is not a strong algorithm-theory novelty paper.

## Implemented Files

- `latex/template.tex`
- `latex/template.pdf`
- `paper_refined.pdf`
- `geo_public_bathy_rebuild.pdf`
- `geo_next_round_checklist_log.md`

## Verification

- LaTeX build: `compile_after_sensitivity_table_20260429_pass2.log`
- Build output: `template.pdf (28 pages)` in the compile log.
- Warning scan: only the XeLaTeX `inputenc` warning remained.
- Citation count: 41 `\bibitem` entries.

## Current Submission Readiness Judgment

The manuscript is now a defensible public-bathymetry numerical benchmark paper. It is stronger than a pure synthetic simulation paper because it uses real public gridded bathymetry, an independent USGS public-grid extension, sensitivity diagnostics, and explicit failure analysis. However, it remains weaker than a survey-grade or field-validated AUV paper.

**Practical target:** Applied Ocean Research as the balanced Q2 attempt; Ocean Engineering as a higher-risk Q2 attempt.
