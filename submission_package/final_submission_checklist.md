# Final Submission Checklist

Status date: 2026-05-22

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
- [x] GenAI/AI-assisted-tool disclosure is included in Methods and Acknowledgments is kept factual.
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
- [x] Submission reproduction map is recorded in `README_submission.md`.
- [x] Latest five-point PDF page preview is recorded in `audit/page_preview_20260515_user_5point_v16/contact_sheet.png`.
- [x] Latest Fig. 2/Fig. 6/Fig. 14 PDF page preview is recorded in `audit/page_preview_20260515_v17b_after/contact_sheet.png`.
- [x] Latest reference audit is recorded in `audit/reference_verification_20260514_v2.md`.

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
- [x] Repository `geo-auv-bathymetry-benchmark` is explicitly described as historical naming in README, Data Availability, and cover letter.
- [x] Cover letter no longer frames the manuscript as a GA-based AUV survey planner and states the no-field/no-hydrographic-QA boundary.

## Compile QA

- [x] MDPI PDF compiled to 45 pages after the May 22 heading-resolution and public-window statistics patch.
- [x] Working PDF compiled to 45 pages after the May 22 heading-resolution and public-window statistics patch.
- [x] Abstract rechecked after the May 15 pass: 197 words by the local LaTeX-stripped counter.
- [x] No undefined citation/reference warnings in latest MDPI compile log.
- [x] No overfull hbox warnings in latest MDPI compile log.
- [x] No `Float too large`, fatal, or emergency-stop messages in the latest strict log scan.
- [x] No sparse/blank figure pages detected in the May 14 rendered contact-sheet QA.
- [x] Working PDF compiled and retained.
- [x] Latest compile logs:
  - `manuscript/mdpi_jmse/compile_after_public_window_stats_20260522_pass2.log`
  - `manuscript/latex/compile_after_public_window_stats_20260522_pass2.log`

## Repository and Archive

- [x] GitHub repository: `https://github.com/poboll/geo-auv-bathymetry-benchmark`
- [x] Zenodo concept DOI: `10.5281/zenodo.19919505`
- [x] Initial archived version DOI: `10.5281/zenodo.19919506`
- [x] DOI `10.5281/zenodo.19919506` was checked through DOI.org and resolves to Zenodo record `19919506`.
- [x] Reproducibility manifest generated for current workspace: 257 entries.
- [x] README, `README_submission.md`, `CITATION.cff`, `.zenodo.json`, Data Availability, and cover letter use the current fixed-line MBES manuscript title/framing.
- [x] GEBCO TID URL updated to the current official GEBCO TID page.
- [x] Four bibliography entries using `et al.` were expanded or corrected.
- [x] Automatic reference audit reports 42 references and 0 `et al.` entries; the only automated DOI failure is `xie2024three`, caused by HTTP 403 on DOI resolution, and the MDPI article page confirms the title, authors, journal, year, volume/issue, article number, and DOI.

## Final Actions Before Actual Submission

- [ ] Create a final GitHub release only after the manuscript is frozen.
- [ ] Confirm Zenodo has minted the final release DOI after the GitHub release.
- [x] Add fixed version DOI wording to Data Availability without conditional future-release placeholder text.
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
