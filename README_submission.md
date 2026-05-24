# Submission Reproducibility Notes

This file is a compact submission-facing map for the JMSE manuscript package. It records the environment, key commands, and evidence artifacts used by the current manuscript version.

## Environment

The local Conda environment is `uu`. The environment specification is recorded in `environment.yml`.

```bash
conda env update -n uu -f environment.yml
conda run -n uu python --version
```

## Core Commands

Run the main public-grid benchmark only if the full evidence package needs to be regenerated:

```bash
conda run -n uu python geo_public_bathy_benchmark.py
```

Regenerate the submission-boundary diagnostics added for the final teacher-review checklist:

```bash
conda run -n uu python make_submission_boundary_diagnostics.py --seed-count 20
```

Regenerate the heading-resolution and paired public-window statistics diagnostics:

```bash
conda run -n uu python make_heading_resolution_diagnostic.py --scenes all
conda run -n uu python make_public_window_statistics.py
```

Regenerate the side-specific footprint validity audit:

```bash
conda run -n uu python make_footprint_validity_audit.py
```

Regenerate the external survey-layout and turning-cost audits:

```bash
conda run -n uu python make_external_layout_baseline_audit.py
conda run -n uu python make_external_turning_cost_audit.py
```

Refresh the reproducibility manifest with SHA-256 checksums:

```bash
conda run -n uu python make_reproducibility_manifest.py
```

Check that the manifest and the submission-critical evidence directories are
actually tracked by Git before creating a GitHub release:

```bash
python check_release_readiness.py
```

Compile the MDPI/JMSE manuscript:

```bash
cd manuscript/mdpi_jmse
xelatex -interaction=nonstopmode template.tex
xelatex -interaction=nonstopmode template.tex
```

Compile the synchronized working copy:

```bash
cd manuscript/latex
xelatex -interaction=nonstopmode template.tex
xelatex -interaction=nonstopmode template.tex
```

## Evidence Artifacts

- `run_5/`: main benchmark outputs.
- `gebco_tid_audit/`: GEBCO TID provenance audit.
- `threshold_local_failure_extension/`: strict-threshold and local-tail diagnostics.
- `submission_boundary_diagnostics/`: \(W_{\max}\) cap sensitivity, raw Hybrid GA vs Adaptive Spacing practical deltas, and conservative GA gate diagnostics.
- `heading_resolution_diagnostic/`: \(15^{\circ}\) versus \(5^{\circ}\) deterministic heading-resolution audit.
- `public_window_statistics/`: paired statistics across the two main GEBCO windows, four supplemental GEBCO windows, and three USGS 30 m crops.
- `footprint_validity_audit/`: total-width proxy versus side-specific port/starboard footprint validity audit.
- `external_layout_baseline_audit/`: deterministic external fixed-width survey-layout heuristic audit on nine public-grid windows.
- `external_turning_cost_audit/`: minimum-turn-radius and mission-time proxy post-evaluation for the same external-layout audit rows.
- `survey_grade_extension_usgs_cascadia/`: USGS 30 m public-grid extension.
- `coarse_prior_replay/`, `structured_prior_error_replay/`, `uncertainty_replay/`, `uncertainty_margin_replay/`, and `current_drift_replay/`: transfer and execution-boundary diagnostics.
- `reproducibility_manifest.json`: file inventory and SHA-256 checksums for the current workspace.
- `check_release_readiness.py`: release-gate audit that flags missing required
  manuscript artifacts, empty evidence directories, and manifest entries that
  are not tracked by Git.

## Claim Boundary

The manuscript is a depth-referenced MBES fixed-line public-grid planning benchmark and robustness study. The current title/framing is `Terrain-Aware Fixed-Line MBES Survey Planning from Public Bathymetric Priors: A Reproducible Benchmark and Robustness Study`. The side-specific footprint audit is a planning-evaluator validity check, and the external turning-cost audit is a deterministic post-planning mission-time proxy. Neither is beam-level acoustic ray tracing, raw MBES product validation, controller simulation, mission-log replay, sea/lake/field validation, hydrographic-quality assurance, navigation-safety readiness, or altitude-controlled AUV execution.

### Additional v21 Diagnostics

Regenerate the GA surrogate-audit diagnostic used to answer the stride-3 evaluator question:

```bash
conda run -n uu python make_ga_surrogate_audit.py --scenes all --seeds 12 --candidates-per-seed 12
```

Regenerate the Figure 1 TikZ workflow used by both manuscript tracks:

```bash
conda run -n uu python make_method_pipeline_figure.py
```

## Release Gate

Do not mint a Zenodo-triggering GitHub release until `python
check_release_readiness.py` exits with code 0, both manuscript PDFs compile
cleanly, and the checklist in
`submission_package/final_submission_checklist.md` records the exact release
tag and DOI. The initial archived DOI is `10.5281/zenodo.19919506`; a new
GitHub release should only be created when the current manuscript package is
ready to be frozen as a new version.
