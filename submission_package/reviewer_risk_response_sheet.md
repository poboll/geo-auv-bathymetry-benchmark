# Reviewer Risk Response Sheet

This sheet records likely reviewer objections and the manuscript locations that already address them. It is intended for pre-submission checking and later response-letter drafting.

## 1. “This is not a real AUV sea trial.”

Response:
The manuscript does not claim sea-trial validation. It is framed as a public-bathymetry numerical benchmark for pre-mission line-layout planning.

Where addressed:
- Abstract: public GEBCO, synthetic, USGS public-grid extension, coarse-prior replay, and execution-uncertainty replay are named as numerical evidence sources.
- Data provenance and benchmark protocol: GEBCO scenes are public gridded bathymetry inputs, not AUV mission logs or raw MBES returns.
- Discussion: public benchmark scope and deployment boundary sections explicitly separate public-grid benchmark evidence from mission-log transfer and field execution.

## 2. “The public route-length gain is only about 0.75%.”

Response:
The paper does not sell route shortening as the main public-scene result. The main public result is overlap discipline and stable layout regularization under a fixed lawnmower traversal.

Evidence:
- Fixed public-scene mean excess-overlap violation: about 0.8067%.
- Hybrid public-scene mean excess-overlap violation: about 0.0952%.
- Hybrid predicted coverage range on the two GEBCO scenes: 98.97--99.63%.
- Monterey shows structural rotation from 0 degrees to 90 degrees and line-count reduction from 73 to 59.

Where addressed:
- Abstract.
- Public GEBCO results section.
- Discussion: “Why the public gain is still meaningful.”
- Reviewer-risk matrix.

## 3. “The GA population and generation counts are too small.”

Response:
GA is not used as a blind global optimizer. The orientation scan and adaptive-spacing step already provide a strong base layout. GA is only a local refinement layer for residual-overlap cleanup and seed-level stabilization.

Evidence:
- Public-scene planning time remains in the sub-second to low-second offline-planning regime.
- 20-seed public runs converge to stable heading and line-count modes.
- Adaptive Spacing without GA captures nearly all public route shortening.

Where addressed:
- Methods: GA refinement subsection and planner settings table.
- Results: public-scene ablation and bootstrap CI.
- Discussion: “Baseline limitation and what the GA actually adds.”

## 4. “The method ignores AUV turning radius and vehicle dynamics.”

Response:
The core optimizer preserves a fixed line family and does not claim controller-level execution feasibility. A turning-aware post-evaluation is included to test whether public-scene gains disappear under a first-order line-change penalty.

Evidence:
- \(L_R=L+(N-1)\pi R_{\min}\) is evaluated for \(R_{\min}=25, 50, 100\) m.
- The result is framed as kinematic-aware post-evaluation, not Dubins/controller-level validation.

Where addressed:
- Methods: objective and line-change discussion.
- Results: turning-aware post-evaluation table.
- Discussion: deployment boundary and operation-relevant next steps.

## 5. “Only two GEBCO public scenes are not enough.”

Response:
The two GEBCO scenes remain the primary 20-seed public benchmark for consistency, but the manuscript adds scene-selection and transfer diagnostics without mixing them into the main average.

Evidence:
- Four supplemental GEBCO windows: Mariana Trench, Puerto Rico Trench, Mid-Atlantic Ridge, Hawaii Ridge.
- Independent USGS Southern Cascadia 30 m public-grid extension with low/medium/high complexity crops.
- Coarse-prior/fine-grid replay on the USGS source.

Where addressed:
- Results roadmap.
- Supplemental GEBCO expansion paragraph.
- USGS extension section.
- Coarse-prior replay section.
- Reviewer-risk matrix.

## 6. “GEBCO is not survey-grade or navigation-grade.”

Response:
The manuscript explicitly treats GEBCO as a reproducible public prior-map benchmark, not as survey-grade terrain or a navigation-safety input.

Where addressed:
- Public provenance table.
- Data-level boundary paragraph.
- Discussion: public benchmark scope.
- Reviewer-risk matrix.

## 7. “Complex Terrain fails.”

Response:
The failure is retained as a scientific boundary result. It shows that terrain-aware spacing is necessary but not sufficient when a single global heading and fixed parallel-line family become too restrictive.

Evidence:
- Fixed Complex Terrain: 96.1889% predicted coverage, 28.4976% excess overlap, infeasible.
- Adaptive: 96.8778% predicted coverage, 7.1212% excess overlap, infeasible.
- Representative Hybrid: 96.7778% predicted coverage, 7.1817% excess overlap, infeasible.

Where addressed:
- Complex-terrain failure-mode figure.
- Cross-scene mechanism and failure boundary section.
- Discussion: complex-terrain failure boundary.

## 8. “The public benchmark could be cherry-picked.”

Response:
The manuscript now reports low-overlap public GEBCO behavior, higher-overlap synthetic behavior, and high-complexity USGS public-grid behavior. The mechanism is tied to the Fixed-Spacing excess-overlap burden rather than to scene provenance alone.

Where addressed:
- Scene-level regime diagnostic figure.
- Supplemental GEBCO expansion.
- USGS extension and coarse-prior replay.

## 9. “The results are overclaimed.”

Response:
The manuscript has been audited to avoid field-ready, mission-ready, hydrographic guarantee, global optimality, and sea-trial language. Supported claims are limited to public-grid numerical benchmark behavior, predicted coverage, overlap suppression, seed repeatability, and prior-resolution/uncertainty replay diagnostics.

Where addressed:
- Abstract and conclusion.
- Discussion and reviewer-risk matrix.
- Data Availability.
