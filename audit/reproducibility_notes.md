# Reproducibility Notes: Geo Public Bathymetry Benchmark

## Scope

This workspace supports a public-data numerical benchmark for geometry-aware offline AUV MBES survey-line design. It does not contain sea-trial logs, measured MBES returns, or field deployment validation.

## Active Workspace And Evidence

- Workspace: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`
- Main manuscript: `latex/template.tex`
- Latest validated benchmark run: `run_5`
- Main CSV: `run_5/benchmark_method_statistics.csv`
- Raw per-seed CSV: `run_5/benchmark_results.csv`
- Summary JSON: `run_5/benchmark_summary.json`
- Public-scene manifest: `run_5/public_scene_manifest.json`
- Implementation settings: `run_5/implementation_details.json`

## Input Scenes

| Scene | Source | Bounds / extent | Resolution | Depth range | Role |
|---|---|---|---:|---:|---|
| GEBCO Cascadia Margin | GEBCO 2025 global bathymetry subset | lon -126.8 to -125.2, lat 43.2 to 44.8 | 1195.383 m | 1009--3101 m | Primary public-data benchmark |
| GEBCO Monterey Canyon | GEBCO 2025 global bathymetry subset | lon -123.3 to -122.3, lat 35.3 to 36.3 | 758.720 m | 892--3982 m | Primary public-data benchmark |
| Flat Seafloor | Synthetic benchmark | 7408 m x 9260 m local grid | 120 x 150 grid | 120--120 m | Mechanism control |
| Uniform Slope | Synthetic benchmark | 7408 m x 9260 m local grid | 120 x 150 grid | 60--230 m | Slope sensitivity |
| Complex Terrain | Synthetic benchmark | 7408 m x 9260 m local grid | 120 x 150 grid | 10--279 m | Failure-boundary stress test |

## Sensor And Acceptance Settings

- MBES total opening angle: 120 degrees
- Coverage target: 97.0%
- Target overlap: 15%
- Admissible overlap band: 10%--20%
- Excess-overlap metric: area-averaged violation above the 20% ceiling
- Public windows: regional benchmark scale, not single-sortie AUV mission budgets

## Compared Methods

- Fixed-Spacing
- Simple Greedy
- Adaptive Spacing without GA (archived CSV label: `Adaptive Spacing w/o GA`)
- Fixed-Swath GA
- Full Geometry-Aware Hybrid GA

## Search And Seed Settings

- Candidate headings: 0, 15, 30, ..., 165 degrees
- Constant-spacing quantiles: 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50
- Adaptive-spacing quantiles: 0.20, 0.25, 0.30, 0.35
- GA population size: 10
- GA generations: 10
- GA seeds: 0--19
- Deterministic methods: Fixed-Spacing, Simple Greedy, Adaptive Spacing without GA
- Stochastic methods summarized over 20 seeds: Fixed-Swath GA, Full Geometry-Aware Hybrid GA

## Reproduction Commands

Run the benchmark:

```bash
conda run -n uu bash -lc 'cd /Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2 && python geo_public_bathy_benchmark.py --out-dir run_5 --workspace-root .'
```

Regenerate journal figures:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python make_journal_figures.py
```

Run public-scene sensitivity diagnostics:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python make_sensitivity_study.py
```

Run the independent USGS 30 m public-grid extension:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/uu/bin/python make_survey_grade_extension.py
```

Compile the manuscript:

```bash
cd /Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2/latex
xelatex -interaction=nonstopmode template.tex
xelatex -interaction=nonstopmode template.tex
```

## Figure Files Used By The Manuscript

- Figure 1 workflow is built as native TikZ in `latex/template.tex`
- `latex/pic/journal_scene_atlas.png`
- `latex/pic/journal_cascadia_routes.png`
- `latex/pic/journal_monterey_routes.png`
- `latex/pic/journal_metric_heatmap.png`
- `latex/pic/journal_ablation_seed.png`
- `latex/pic/journal_sensitivity_overlap_target.png`
- `latex/pic/journal_sensitivity_resolution.png`
- `latex/pic/journal_usgs_extension.png`

## Sensitivity Diagnostics

Sensitivity artifacts are stored under `sensitivity/` and are diagnostic only; the main evidence source remains `run_5`.

- `sensitivity/target_overlap_sensitivity_summary.csv`: public-scene reruns at target-overlap settings 10%, 15%, and 20%, with Hybrid GA summarized over seeds 0--4.
- `sensitivity/target_overlap_sensitivity_raw.csv`: raw deterministic and per-seed rows for the target-overlap diagnostic.
- `sensitivity/beam_angle_sensitivity_summary.csv`: public-scene reruns at MBES opening angles 100, 110, 120, and 130 degrees.
- `sensitivity/beam_angle_sensitivity_raw.csv`: raw deterministic and per-seed rows for the beam-angle diagnostic.
- `sensitivity/prior_depth_bias_sensitivity_summary.csv`: public-scene reruns on uniformly depth-biased planning priors at -150 m, 0 m, and +150 m, rescored on the native GEBCO grids.
- `sensitivity/prior_depth_bias_sensitivity_raw.csv`: raw deterministic and per-seed rows for the simplified prior-depth-bias diagnostic.
- `sensitivity/prior_relief_scale_sensitivity_summary.csv`: public-scene reruns on relief-scaled planning priors at 0.7, 1.0, and 1.3, rescored on the native GEBCO grids.
- `sensitivity/prior_relief_scale_sensitivity_raw.csv`: raw deterministic and per-seed rows for the simplified prior-relief-scale diagnostic.
- `sensitivity/resolution_sensitivity_summary.csv`: public-scene reruns on native, 2x, and 3x strided grids, with Hybrid GA summarized over seeds 0--4.
- `sensitivity/resolution_sensitivity_raw.csv`: raw deterministic and per-seed rows for the grid-resolution diagnostic.
- `latex/pic/journal_sensitivity_overlap_target.png`: manuscript figure for the target-overlap diagnostic.
- `latex/pic/journal_sensitivity_resolution.png`: manuscript figure for the grid-resolution diagnostic.
- `latex/pic/journal_sensitivity_prior_depth_bias.png`: archived figure for the simplified prior-depth-bias diagnostic.
- `latex/pic/journal_sensitivity_prior_relief_scale.png`: archived figure for the simplified prior-relief-scale diagnostic.
- `latex/pic/journal_sensitivity_beam_angle.png`: archived diagnostic figure. In the current public-scene configuration, the beam-angle curves are flat because the effective public-scene swath width is limited by the benchmark's 1800 m swath cap.

## Output Schemas

- `benchmark_method_statistics.csv`: scene-method aggregate metrics, including path length, predicted coverage, excess overlap, planning time, line count, feasibility, and consistency fields.
- `benchmark_results.csv`: per-run and per-seed method outputs, including orientation, line count, path length, predicted coverage, excess overlap, planning time, and feasibility.
- `benchmark_summary.json`: final mean metrics, standard errors, summary rows, public scene manifest, run counts, and figure files.
- `public_scene_manifest.json`: public-data provenance, bounds, resolution, depth range, terrain class, and missing-value handling.
- `implementation_details.json`: sensor geometry, grid settings, search settings, seeds, and public-data policy.

## Known Evidence Boundaries

- GEBCO scenes provide real public gridded bathymetry, not field-executed AUV trajectories.
- Reported coverage is predicted coverage under the archived sensor--terrain model, not measured coverage in the ocean.
- The Complex Terrain synthetic scene remains infeasible under the current parameterization and is retained as a boundary-of-validity result.
- Seed repeatability is checked for public-scene GA seeds only.
- The target-overlap, beam-angle, simplified prior-map perturbation, and grid-resolution diagnostics are limited public-scene planning-parameter checks; they are not a full sensitivity study over GA hyperparameters, spatially varying prior-map error, navigation uncertainty, or vehicle dynamics.
- The resolution diagnostic uses strided downsampling of the already selected public windows. It does not replace a survey-grade multiresolution bathymetry experiment.

## Higher-resolution Public Grid Pilot And Extension

A separate pilot was added on 2026-04-27 to test whether a higher-resolution public bathymetric product can be ingested without changing the main `run_5` evidence chain.

- Script: `make_survey_grade_pilot.py`
- Audit: `SURVEY_GRADE_PILOT_20260427.md`
- Output directory: `survey_grade_pilot_usgs_cascadia/`
- Source: USGS Southern Cascadia 30 m composite bathymetry, v2, DOI `https://doi.org/10.5066/P9C5DBMR`
- Raw raster: `public_bathy/raw/usgs/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2.tif`
- Pilot seeds: 0--4 for stochastic GA methods

This pilot demonstrated ingestion feasibility for a 30 m public bathymetric grid and reinforced the overlap-control story. It was then expanded into a separate three-crop, 20-seed public-grid extension.

### USGS 30 m Multi-crop Extension

- Script: `make_survey_grade_extension.py`
- Audit: `SURVEY_GRADE_EXTENSION_20260427.md`
- Output directory: `survey_grade_extension_usgs_cascadia/`
- Manuscript figure: `latex/pic/journal_usgs_extension.png`
- Run log: `survey_grade_extension_usgs_cascadia_20260427_v3.log`
- Source: USGS Southern Cascadia 30 m composite multibeam bathymetry surface, version 2.0, DOI `https://doi.org/10.5066/P9C5DBMR`
- Selected crops: empirical complexity quantiles 0.25, 0.55, and 0.80
- Hybrid GA seeds: 0--19

The extension is included in the manuscript only as an independent public-grid numerical check. It is not mixed into `run_5`, and it is not field validation. The safe interpretation is that terrain-aware spacing removes excess-overlap violations and can recover feasibility on a high-complexity USGS crop; low- and medium-complexity crops show negligible route shortening.
