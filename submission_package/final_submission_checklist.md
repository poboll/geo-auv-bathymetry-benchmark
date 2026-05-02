# Final Submission Checklist

Status date: 2026-05-02

## Manuscript Files

- [x] MDPI/JMSE LaTeX source: `mdpi_jmse/template.tex`
- [x] MDPI/JMSE compiled PDF: `mdpi_jmse/template.pdf`
- [x] Submission convenience PDF: `mdpi_jmse_jmse_submission_draft.pdf`
- [x] Working manuscript source: `latex/template.tex`
- [x] Working manuscript PDF: `latex/template.pdf`

## Formatting QA

- [x] MDPI placeholder DOI footer removed from the pre-submission PDF.
- [x] Received/Revised/Accepted/Published placeholders hidden.
- [x] Copyright block hidden in draft copy.
- [x] Author list matches current plan: Changlong Li, Zengye Su, Yudan Nie.
- [x] Affiliation: School of Information Technology and Engineering, Guangzhou College of Commerce.
- [x] Emails: 20210485@gcc.edu.cn, szy@xs.gcc.edu.cn, nyd@xs.gcc.edu.cn.
- [x] Funding retained.
- [x] Data Availability includes GitHub repository and Zenodo concept DOI.
- [x] References count is above 40.

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

## Claim Boundary QA

- [x] No claim of AUV sea-trial validation.
- [x] No claim of mission-log validation.
- [x] No claim of hydrographic survey guarantee.
- [x] No claim of navigation-safety readiness.
- [x] GA framed as local refinement rather than main innovation.
- [x] Public result framed as overlap discipline and layout regularization rather than dramatic path shortening.
- [x] Complex Terrain failure retained as a boundary result.

## Compile QA

- [x] MDPI PDF compiled to 36 pages after DOI-footer cleanup.
- [x] No undefined citation/reference warnings in latest MDPI compile log.
- [x] No overfull hbox warnings in latest MDPI compile log.
- [x] Working PDF compiled and retained.

## Repository and Archive

- [x] GitHub repository: `https://github.com/poboll/geo-auv-bathymetry-benchmark`
- [x] Zenodo concept DOI: `10.5281/zenodo.19919505`
- [x] Initial archived version DOI: `10.5281/zenodo.19919506`
- [x] Reproducibility manifest generated for workspace: 90 entries.
- [x] Reproducibility manifest generated for GitHub package: 117 entries.

## Final Actions Before Actual Submission

- [ ] Create a final GitHub release only after the manuscript is frozen.
- [ ] Confirm Zenodo has minted the final release DOI after the GitHub release.
- [ ] Replace Data Availability wording if a fixed final version DOI is preferred over the concept DOI.
- [ ] Re-download the final PDF from the MDPI submission system after upload and inspect page 1, figure pages, references, and Data Availability.
- [ ] Decide whether to include the cover letter text directly or adapt it to the MDPI submission form.
