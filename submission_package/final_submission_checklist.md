# Final Submission Checklist

Status date: 2026-05-23

## Manuscript Files

- [x] MDPI/JMSE LaTeX source: `manuscript/mdpi_jmse/template.tex`
- [x] MDPI/JMSE compiled PDF: `manuscript/mdpi_jmse/template.pdf`
- [x] Submission convenience PDF: `mdpi_jmse_jmse_submission_draft.pdf`
- [x] Working manuscript source: `manuscript/latex/template.tex`
- [x] Working manuscript PDF: `manuscript/latex/template.pdf`

## Formatting QA

- [x] MDPI placeholder DOI footer removed from the pre-submission PDF.
- [x] Received/Revised/Accepted/Published placeholders hidden.
- [x] Copyright block hidden in draft copy.
- [x] Author list matches current plan: Changlong Li, Zengye Su, Yudan Nie.
- [x] Affiliation: School of Information Technology and Engineering, Guangzhou College of Commerce.
- [x] Emails: 20210485@gcc.edu.cn, szy@xs.gcc.edu.cn, nyd@xs.gcc.edu.cn.
- [x] Funding retained.
- [x] Data Availability includes GitHub repository, Zenodo concept DOI, and initial fixed version DOI.
- [x] Data Availability no longer contains conditional "if later frozen release..." submission placeholder wording.
- [x] GenAI/AI-assisted-tool disclosure is included in the back matter via `\useofartificialintelligence{...}` and Acknowledgments is kept factual.
- [x] References count is above 40.
- [x] Abbreviations section follows the unframed MDPI template style; no artificial table borders were added.

## Evidence QA

- [x] Main evidence source is `run_5`.
- [x] Public GEBCO means are consistent with `run_5/benchmark_method_statistics.csv`.
- [x] Complex Terrain failure values are recorded in `run_5/complex_terrain_failure_mode_summary.csv`.
- [x] Turning-aware post-evaluation is recorded in `run_5/turning_aware_public_posteval.csv`.
- [x] Bootstrap CI is recorded in `run_5/public_hybrid_bootstrap_ci.csv`.
- [x] PSO local-refinement diagnostic is recorded in `pso_baseline/`.
- [x] Coarse-prior/fine-grid replay is recorded in `coarse_prior_replay/`.
- [x] Supplemental GEBCO expansion is recorded in `gebco_scene_expansion/`.
- [x] Execution-uncertainty replay is recorded in `uncertainty_replay/`.
- [x] Uncertainty-aware margin replay is recorded in `uncertainty_margin_replay/`.
- [x] Current-drift replay is recorded in `current_drift_replay/`.
- [x] Structured prior-error replay is recorded in `structured_prior_error_replay/`.
- [x] Vehicle-aware post-evaluation is recorded in `vehicle_aware_posteval/`.
- [x] Journal target and reviewer-risk assessment is recorded in `audit/JOURNAL_TARGET_AND_REVIEWER_ASSESSMENT_20260512.md`.
- [x] GEBCO TID/source-type audit is recorded in `gebco_tid_audit/`.
- [x] Threshold/local-failure diagnostics are recorded in `threshold_local_failure_extension/`.
- [x] Submission-boundary diagnostics are recorded in `submission_boundary_diagnostics/` with \(W_{\max}=1200/1800/2400\) sensitivity and GA gate/practical-significance CSV/JSON files.
- [x] Heading-resolution diagnostic is recorded in `heading_resolution_diagnostic/`; the \(5^{\circ}\) audit reproduces Adaptive Spacing headings and metrics on the two GEBCO scenes and USGS High.
- [x] Nine-window paired public statistics are recorded in `public_window_statistics/`; both terrain-aware methods improve overlap in 9/9 public windows, with one-sided Wilcoxon \(p=0.00195\).
- [x] Side-specific footprint validity audit is recorded in `footprint_validity_audit/`; the port/starboard audit changes 0/9 audited \(C97/O3\) feasibility decisions and records maximum coverage and overlap deltas of 0.50 pp and 1.217 pp.
- [x] External survey-layout heuristic audit is recorded in `external_layout_baseline_audit/`; min-span/contour/geometry-shortest fixed-width heuristics reach 6/9, 6/9, and 8/9 feasible public windows, while Adaptive Spacing and Hybrid seed-0 reach 9/9.
- [x] External turning-cost audit is recorded in `external_turning_cost_audit/`; it adds \(R_{\min}=25/50/100/200\) m line-change arcs to the v28 external-layout rows and reports mission-time proxy gains without changing the C97/O3 feasibility gate.
- [x] Submission reproduction map is recorded in `README_submission.md`.
- [x] Latest five-point PDF page preview is recorded in `audit/page_preview_20260515_user_5point_v16/contact_sheet.png`.
- [x] Latest Fig. 2/Fig. 6/Fig. 14 PDF page preview is recorded in `audit/page_preview_20260515_v17b_after/contact_sheet.png`.
- [x] Latest reference audit is recorded in `audit/reference_verification_20260514_v2.md`.
- [x] JMSE v24 narrative patch adds a dedicated benchmark-parameter rationale table using IHO C-13, NOAA HSSD 2025, and AusSeabed Guidelines as scope references.

## Claim Boundary QA

- [x] No claim of AUV sea-trial validation.
- [x] No claim of mission-log validation.
- [x] No claim of hydrographic survey guarantee.
- [x] No claim of navigation-safety readiness.
- [x] GA framed as local refinement rather than main innovation.
- [x] Public result framed as overlap discipline and layout regularization rather than dramatic path shortening.
- [x] Complex Terrain failure retained as a boundary result.
- [x] GEBCO/USGS results are framed as public-grid numerical planning evidence, not sea-trial, mission-log, raw-MBES, or hydrographic-quality validation.
- [x] GA framed as an optional local repeatability/refinement layer; deterministic adaptive spacing and public-grid benchmark evidence remain the main contribution.
- [x] GEBCO TID/source-type information is used only as provenance evidence; derived planning layers are not mislabeled as official source fractions.
- [x] \(W_{\max}=1800\) m is described as a declared benchmark range cap, not an unconstrained sonar-range claim.
- [x] \(W_{\max}\) sensitivity is now explicitly reported in the manuscript; the 2400 m USGS High negative boundary is retained rather than hidden.
- [x] GA practical-significance and operational-gate diagnostic is now reported; GA remains optional local cleanup rather than a main-effect claim.
- [x] Side-specific footprint validity audit is framed as planning-evaluator validity evidence, not beam-level acoustic ray tracing, raw MBES product validation, field/lake/sea trial, or hydrographic QA.
- [x] Repository `geo-auv-bathymetry-benchmark` is explicitly described as historical naming in README, Data Availability, and cover letter.
- [x] Cover letter no longer frames the manuscript as a GA-based AUV survey planner and states the no-field/no-hydrographic-QA boundary.

## Compile QA

- [x] MDPI PDF compiled to 51 pages after the May 24 v29 external turning-cost audit pass.
- [x] Working PDF compiled to 51 pages after the May 24 v29 external turning-cost audit pass.
- [x] Abstract rechecked after the May 23 v24 pass: 199 words by the local LaTeX-stripped counter.
- [x] No undefined citation/reference warnings in latest MDPI compile log.
- [x] No overfull hbox warnings in latest MDPI compile log.
- [x] No `Float too large`, fatal, or emergency-stop messages in the latest strict log scan.
- [x] No sparse/blank figure pages detected in the May 14 rendered contact-sheet QA.
- [x] Working PDF compiled and retained.
- [x] Latest compile logs:
  - `manuscript/mdpi_jmse/compile_after_external_turning_v29_20260524_pass2.log`
  - `manuscript/latex/compile_after_external_turning_v29_20260524_pass2.log`

## Repository and Archive

- [x] GitHub repository: `https://github.com/poboll/geo-auv-bathymetry-benchmark`
- [x] Zenodo concept DOI: `10.5281/zenodo.19919505`
- [x] Initial archived version DOI: `10.5281/zenodo.19919506`
- [x] DOI `10.5281/zenodo.19919506` was checked through DOI.org and resolves to Zenodo record `19919506`.
- [x] Reproducibility manifest generated for current workspace: 313 entries.
- [x] README, `README_submission.md`, `CITATION.cff`, `.zenodo.json`, Data Availability, and cover letter use the current fixed-line MBES benchmark/robustness manuscript title/framing.
- [x] Release-readiness gate added as `check_release_readiness.py`; run it before creating any Zenodo-triggering GitHub release.
- [x] GEBCO TID URL updated to the current official GEBCO TID page.
- [x] Four bibliography entries using `et al.` were expanded or corrected.
- [x] Automatic reference audit reports 45 references, 0 failed DOI/URL checks, and 0 `et al.` entries after adding DOI redirect fallback.

## Final Actions Before Actual Submission

- [ ] Create a final GitHub release only after the manuscript is frozen.
- [ ] Confirm Zenodo has minted the final release DOI after the GitHub release.
- [x] Add fixed version DOI wording to Data Availability without conditional future-release placeholder text.
- [ ] After a final release is minted, replace the current initial version DOI with the new fixed Zenodo version DOI in Data Availability, `README.md`, `README_submission.md`, `CITATION.cff`, `.zenodo.json`, and this checklist.
- [ ] Re-download the final PDF from the MDPI submission system after upload and inspect page 1, figure pages, references, and Data Availability.
- [ ] Decide whether to include the cover letter text directly or adapt it to the MDPI submission form.
- [ ] Human corresponding author should do one last title-page/funding/author-email check before upload.

## 2026-05-22 v21 Addendum

- [x] Figure 1 rebuilt as a LaTeX/TikZ small-node vector workflow; no thick rectangle boxes or text overflow in `audit/page_preview_20260522_surrogate_fig1_v21/page_05.png`.
- [x] `make_method_pipeline_figure.py` now targets the active `manuscript/*/pic` directories rather than obsolete root-level figure folders.
- [x] GA stride-3 surrogate audit added in `ga_surrogate_audit/`; Table `tab:ga_surrogate_audit` reports stride-vs-full-grid ranking agreement.
- [x] Manifest updated to 264 entries and includes `ga_surrogate_audit/` plus `make_ga_surrogate_audit.py`.
- [x] MDPI and working PDFs compiled to 46 pages with logs `compile_after_surrogate_fig1_v21_20260522_pass2.log`; strict scan found no LaTeX hard errors, undefined references/citations, overfull boxes, float-too-large warnings, fatal errors, or rerun warnings.
- [x] Latest delivery PDFs refreshed at repository root.

## 2026-05-23 Release-Readiness Addendum

- [x] Data Availability wording changed from redistributing downloaded GEBCO TID GeoTIFF subsets to reporting GEBCO TID audit CSV/JSON, TID basket identifiers, and retrieval metadata; raw GEBCO and USGS source products remain cited through official DOI landing pages.
- [x] `make_reproducibility_manifest.py` now filters manifest entries to Git-tracked files and records the current Git revision, reducing the risk that a GitHub/Zenodo release cites local-only evidence.
- [x] `check_release_readiness.py` added as a release gate for required PDFs, source files, evidence directories, and manifest/Git consistency.
- [x] `python check_release_readiness.py` passes after the v23 manuscript/manifest update: missing required paths, empty required dirs, untracked manifest entries, and tracked core files not in manifest are all 0.

## 2026-05-23 v23 JMSE Narrative Addendum

- [x] Title narrowed across manuscript, README, `CITATION.cff`, `.zenodo.json`, and cover letter to `Terrain-Aware Fixed-Line Planning for MBES Survey Design Using Public Bathymetric Priors`.
- [x] Abstract rewritten to emphasize fixed-line survey design, public bathymetric priors, adaptive spacing, and GA as gated local refinement; it now explicitly states that C97/O3 feasibility does not imply tail-safe C99/O2 or project-specific QA performance.
- [x] Contribution bullets reduced from five to three: reproducible public-grid benchmark, quantile-based adaptive spacing, and regime/boundary diagnostics.
- [x] Methods now justify 15% overlap target, 20% ceiling, C97/O3 gate, and \(W_{\max}=1800\) m as benchmark choices, with IHO/NOAA/AusSeabed references.
- [x] Methods now explains why GA population 10 and generations 10 are appropriate for local cleanup after deterministic heading/adaptive-spacing initialization, and reports 0.32--0.94 s Hybrid GA timing.
- [x] Results now separates nine-window public statistics into low-overlap windows and the overlap-stressed USGS high-complexity crop.
- [x] Supplementary/Reproducibility Evidence now includes a compact implementation map from formulas to scripts and CSV/JSON outputs.
- [x] Discussion demotes segmented-heading to a boundary note and keeps the manuscript focused on fixed-line geometry.

## 2026-05-23 v24 Benchmark/Robustness Addendum

- [x] Title strengthened across manuscript, README, `CITATION.cff`, `.zenodo.json`, and cover letter to `Terrain-Aware Fixed-Line MBES Survey Planning from Public Bathymetric Priors: A Reproducible Benchmark and Robustness Study`.
- [x] Abstract remains within the JMSE safe range at 199 words and now includes rank-biserial effect size 1.00 for the nine-window overlap-cleanup result.
- [x] Methods now includes Table `tab:parameter_rationale`, which ties overlap target, overlap ceiling, C97/O3 gate, swath clipping, heading grid, score weights, and GA budget to their robustness checks.
- [x] Results Table `tab:public_window_stats` was reformatted from a dense horizontal table into a readable vertical statistic-by-method table, including path, overlap, and coverage-delta effect-size evidence.
- [x] Visual QA rendered and inspected `audit/page_preview_20260523_v24/mdpi_key_page_01_v24b.png`, `mdpi_key_page_10_v24b.png`, and `mdpi_key_page_22_v24b.png`; title, parameter table, and public-window table are readable and not clipped.
- [x] MDPI and working PDFs compiled to 47 pages with logs `compile_after_benchmark_robustness_v24_20260523_pass2.log`; strict scan found no LaTeX hard errors, undefined references/citations, overfull boxes, float-too-large warnings, fatal errors, or rerun warnings.
- [x] v24+ reference/release audit rerun: `python3 audit/verify_references_20260514.py` reports 45 references / 0 failed / 0 et_al; `make_reproducibility_manifest.py` writes 290 entries; `check_release_readiness.py` reports 0 missing required paths, 0 empty required dirs, 0 untracked manifest entries, and 0 tracked core files missing from the manifest.

## 2026-05-23 v25 Footprint-validity Addendum

- [x] Added `make_footprint_validity_audit.py` and `footprint_validity_audit/` to compare the manuscript total-width proxy with a side-specific port/starboard footprint submodel on GEBCO Cascadia, GEBCO Monterey, and USGS High representative layouts.
- [x] The audit output is `footprint_validity_raw.csv`, `footprint_validity_summary.json`, and `journal_footprint_validity_audit.png`; the figure is copied into both manuscript figure directories.
- [x] Key audit result: 0 \(C97/O3\) feasibility changes across 9 audited scene-method layouts; maximum absolute coverage delta 0.50 pp; maximum absolute mean excess-overlap delta 1.217 pp; maximum local count disagreement 10.42%.
- [x] The new audit is written into Methods, Results, Discussion, risk matrix, Conclusion, Data Availability, README, README_submission, cover letter, and this checklist as planning-layer evidence rather than field or survey-product validation.
- [x] The audit heatmap was redrawn after PDF QA: duplicate in-figure title/note removed, matrix spacing tightened, Times/STIX-style font applied, and PDF page preview `audit/page_preview_20260523_v25d_final/mdpi_page_37.png` confirms no clipping, overlap, or abnormal blank area.
- [x] Latest reference/release audit after v25d: `python3 audit/verify_references_20260514.py` reports 45 references / 0 failed / 0 et_al; `python check_release_readiness.py` reports 0 missing required paths, 0 empty required dirs, 0 untracked manifest entries, and 0 tracked core files missing from the manifest.

## 2026-05-23 v26 Heatmap-system Polish Addendum

- [x] Main-text heatmap family was polished as a system: Figure 8, Figure 11, Figure 12, Figure 13, Figure 15, Figure 16, and Figure 17 now share tighter panel spacing, lower-saturation palettes, and consistent sans-serif figure typography.
- [x] Figure 8 no longer uses square-cell layout that created wide inter-panel gaps; Figure 15 replaces the right-side reading-guide blank area with a default \(C97/O3\) pass-rate heatmap; Figure 16 was brought back to the same sans-serif heatmap typography as the rest of the manuscript.
- [x] Updated scripts: `journal_heatmap_style.py`, `make_journal_figures.py`, `make_structured_prior_error_replay.py`, `make_uncertainty_replay.py`, `make_uncertainty_margin_replay.py`, `make_threshold_local_failure_extension.py`, `make_footprint_validity_audit.py`, and `make_coarse_prior_replay.py`.
- [x] Visual QA artifacts: before pages in `audit/heatmap_review_20260523_v26/pdf_pages_before/`; final after pages in `audit/heatmap_review_20260523_v26/pdf_pages_after_v26b/` for pages 25, 32, 33, 34, 37, 38, and 39.
- [x] Latest compile logs: `manuscript/mdpi_jmse/compile_after_heatmap_system_v26b_20260523_pass2.log` and `manuscript/latex/compile_after_heatmap_system_v26b_20260523_pass2.log`; both output 49 pages and strict scans report no hard LaTeX errors, undefined references/citations, rerun warnings, overfull boxes, float-too-large warnings, fatal errors, or emergency stops.
- [x] Latest audit rerun: `python3 audit/verify_references_20260514.py` reports 45 references / 0 failed / 0 et_al; `make_reproducibility_manifest.py` writes 297 entries; `check_release_readiness.py` reports all release-blocking counts as 0.

## 2026-05-23 v27b Heatmap-system Refinement Addendum

- [x] The heatmap family was refined again after v26: Figure 8/11/12/13/15/16/17 now use a restrained ivory / slate-teal / muted-rust / gray-slate palette and unified Arial/Helvetica-style sans-serif typography.
- [x] v27 initially made some multi-row heatmaps too tight; v27b restores enough vertical separation for Figure 11 and Figure 17 while keeping the matrices wider and more readable in the PDF.
- [x] Figure 8/11/12/13/16/17 LaTeX insertion widths now use `\textwidth` with modest height caps, reducing perceived source-image whitespace without stretching the matrices.
- [x] Python static check passed for all heatmap scripts: `journal_heatmap_style.py`, `make_journal_figures.py`, `make_structured_prior_error_replay.py`, `make_uncertainty_replay.py`, `make_uncertainty_margin_replay.py`, `make_threshold_local_failure_extension.py`, `make_footprint_validity_audit.py`, and `make_coarse_prior_replay.py`.
- [x] Visual QA artifacts: `audit/heatmap_review_20260523_v27/pdf_pages_after_v27b/` for pages 25, 32, 33, 34, 37, 38, and 39; page images are 1191 x 1684 px and were manually inspected.
- [x] Latest compile logs: `manuscript/mdpi_jmse/compile_after_heatmap_system_v27b_20260523_pass2.log` and `manuscript/latex/compile_after_heatmap_system_v27b_20260523_pass2.log`; both output 49 pages and strict scans report no hard LaTeX errors, undefined references/citations, rerun warnings, overfull boxes, float-too-large warnings, fatal errors, or emergency stops.
- [x] Latest audit rerun: `python3 audit/verify_references_20260514.py` reports 45 references / 0 failed / 0 et_al; `make_reproducibility_manifest.py` writes 297 entries; `check_release_readiness.py` reports all release-blocking counts as 0.
- [x] No claim boundary changed in the v27b visual pass: figures remain public-grid numerical benchmark evidence, not field/lake/sea trials, raw MBES validation, hydrographic QA, or navigation-safety evidence.

## 2026-05-23 v28 External-layout Baseline Audit Addendum

- [x] Added `make_external_layout_baseline_audit.py` and `external_layout_baseline_audit/` to address the reviewer/teacher risk that baselines were only drawn from the manuscript's own fixed-pattern family.
- [x] The audit covers 9 public-grid windows and compares min-span boustrophedon, contour-parallel fixed-width, geometry-shortest fixed-width, Adaptive Spacing, and Hybrid seed-0 under the same \(C97/O3\) benchmark gate.
- [x] Key result: the three external fixed-width heuristics achieve 6/9, 6/9, and 8/9 feasible public windows; Adaptive Spacing and Hybrid seed-0 achieve 9/9. USGS High remains the decisive overlap-stressed boundary where all three external fixed-width heuristics fail and the terrain-aware layouts pass.
- [x] Manuscript text updated in Methods, Results, Discussion, Data Availability, and the implementation map; `Table~\ref{tab:external_layout_audit}` added as the main-text evidence carrier.
- [x] Visual QA artifacts: `audit/page_preview_20260523_external_baseline_v28/page_28.png` through `page_34.png`; page 30 was inspected and the new external-layout audit table is readable, not clipped, and not overwide.
- [x] Latest compile logs: `manuscript/mdpi_jmse/compile_after_external_layout_audit_v28_pass2.log` and `manuscript/latex/compile_after_external_layout_audit_v28_pass2.log`; both output 50 pages and strict scans report no hard LaTeX errors, undefined references/citations, rerun warnings, overfull boxes, float-too-large warnings, fatal errors, or emergency stops.
- [x] Latest audit rerun: `python3 audit/verify_references_20260514.py` reports 45 references / 0 failed / 0 et_al; `make_reproducibility_manifest.py` writes 313 entries; `check_release_readiness.py` reports all release-blocking counts as 0.
- [x] No claim boundary changed in the v28 evidence pass: results remain public-grid numerical planning benchmark evidence, not field/lake/sea trials, raw MBES validation, hydrographic QA, mission-log validation, or navigation-safety evidence.

## 2026-05-24 v29 External Turning-cost Audit Addendum

- [x] Added `make_external_turning_cost_audit.py` and `external_turning_cost_audit/` to address the teacher/reviewer request for a turn-radius / transition-cost post-evaluation layer.
- [x] The audit reuses the v28 54 external-layout rows and expands them to 216 deterministic rows across \(R_{\min}=25/50/100/200\) m; it applies semicircular line-change arcs and declared survey/turn speeds of 1.5 and 0.75 m/s.
- [x] Key result: Adaptive Spacing and Hybrid seed-0 remain 9/9 feasible public windows; their median mission-time gains are 0.682% at both R100 and R200. Geometry-shortest fixed-width is 8/9 feasible; Min-span and Contour are 6/9 feasible.
- [x] USGS High boundary retained: Min-span and Geometry-shortest can show 37.83% R100 mission-time gain, but they remain infeasible with 92.44% coverage and 7.49% mean excess overlap. The manuscript now states explicitly that shorter/faster layouts are not acceptable unless the coverage/overlap gate is passed.
- [x] Manuscript text updated in Results, Discussion, Data Availability, evidence map, and implementation map; Table `tab:external_turning_cost_audit` added as the main-text evidence carrier.
- [x] Visual QA artifacts: `audit/page_preview_20260524_external_turning_v29/page_29.png` through `page_32.png`; page 31 was inspected and Table 17 is readable, not clipped, and not overwide.
- [x] Latest compile logs: `manuscript/mdpi_jmse/compile_after_external_turning_v29_20260524_pass2.log` and `manuscript/latex/compile_after_external_turning_v29_20260524_pass2.log`; both output 51 pages and strict scans report no hard LaTeX errors, undefined references/citations, rerun warnings, overfull boxes, float-too-large warnings, fatal errors, or emergency stops.
- [x] Latest reference audit: `python3 audit/verify_references_20260514.py` reports 45 references / 0 failed / 0 et_al. The script now includes a manual fallback for the USGS Southern Cascadia data DOI `10.5066/P9C5DBMR` because DOI.org automated checks can intermittently fail with TLS EOF even though the official USGS/CMGDS data-release page is verified.
- [x] Latest release-readiness audit: `conda run -n uu python make_reproducibility_manifest.py` writes 325 entries; `python3 check_release_readiness.py` reports `missing_required_paths=0`, `empty_required_dirs=0`, `untracked_manifest_entries=0`, and `tracked_core_files_not_in_manifest=0`.
- [x] No claim boundary changed in the v29 evidence pass: the audit is a deterministic post-planning execution-cost proxy, not a Dubins controller, hydrodynamic simulation, mission-log replay, field/lake/sea trial, hydrographic QA, or navigation-safety evidence.

## 2026-05-24 v30 Blockwise Repair Addendum

- [x] Segmented-heading has been upgraded from a boundary-note diagnostic to a formal gate-aware blockwise fixed-line stress-case extension.
- [x] Manuscript title, abstract, keywords, contribution bullets, Methods, Results, Discussion, Conclusion, Data Availability, README, README_submission, `CITATION.cff`, `.zenodo.json`, and cover letter now use the blockwise-repair framing.
- [x] Added `make_segmented_decision_audit.py` and `segmented_decision_audit/` with CSV/JSON/README/PNG outputs.
- [x] Key decision-audit result: Synthetic Complex is repaired in 30/30 seeds; Monterey accepts blockwise layouts in 14/30 seeds; Mariana/Puerto Rico reject blockwise candidates due to coverage loss; USGS High finds coverage-preserving cleanup in 8/30 seeds but the transition-aware selector retains single-heading due to transition burden.
- [x] v30 compile, visual page QA, reference audit, reproducibility manifest, release-readiness gate, and delivery PDFs rerun: both manuscript PDFs output 52 pages; `python3 audit/verify_references_20260514.py` reports 45 references / 0 failed / 0 et_al; `make_reproducibility_manifest.py` writes 337 entries; `check_release_readiness.py` reports all release-blocking counts as 0.
