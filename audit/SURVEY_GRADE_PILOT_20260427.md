# Survey-grade Grid Pilot: USGS Southern Cascadia 30 m

- Date: 2026-04-27 CST
- Workspace: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`
- Status: successful ingestion and planning probe, not yet part of the manuscript's main `run_5` evidence.

## Why This Was Added

The current paper already has a clean `run_5` benchmark on GEBCO public gridded bathymetry, but GEBCO is a global information product rather than survey-grade mission evidence. The next honest evidence step is therefore not to relabel GEBCO as "real sea trial"; it is to test whether the same planner can ingest a higher-resolution public bathymetric product.

## Data Source

- Source: USGS Southern Cascadia 30 m composite bathymetry, version 2.
- DOI / landing page: `https://doi.org/10.5066/P9C5DBMR`
- Downloaded file:
  - `public_bathy/raw/usgs/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2.zip`
  - 105,474,683 bytes
- Extracted raster:
  - `public_bathy/raw/usgs/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2.tif`
  - 316 MB
- Raster metadata:
  - CRS: `EPSG:26910`
  - raw resolution: 30 m
  - raster size: 85,490 x 47,618
  - nodata: `3.3999999521443642e+38`

This is still a public gridded bathymetric product, not an AUV mission log or raw MBES survey track replay.

## Script Added

- `make_survey_grade_pilot.py`

The script:

1. extracts the USGS raster if needed,
2. searches for a fully valid physical crop at the same approximate regional-pilot dimensions used by the planner,
3. runs Fixed-Spacing, Simple Greedy, Adaptive Spacing without GA, Fixed-Swath GA, and Full Geometry-Aware Hybrid GA,
4. uses seeds 0--4 for stochastic GA methods,
5. writes a separate pilot output directory so `run_5` remains untouched.

## Pilot Output

Output directory:

- `survey_grade_pilot_usgs_cascadia/`

Artifacts:

- `survey_grade_pilot_usgs_cascadia/benchmark_method_statistics.csv`
- `survey_grade_pilot_usgs_cascadia/benchmark_results.csv`
- `survey_grade_pilot_usgs_cascadia/benchmark_results.json`
- `survey_grade_pilot_usgs_cascadia/benchmark_summary.json`
- `survey_grade_pilot_usgs_cascadia/public_scene_manifest.json`
- `survey_grade_pilot_usgs_cascadia/survey_grade_pilot_layouts.png`
- `survey_grade_pilot_usgs_cascadia/README.md`

Run log:

- `survey_grade_pilot_usgs_cascadia_20260427.log`

The first run failed only at preview rendering because the script called a non-existent helper. That failed log was preserved as:

- `survey_grade_pilot_usgs_cascadia_20260427_failed_preview.log`

The preview helper was then fixed and the pilot reran successfully.

## Selected Crop

From `public_scene_manifest.json`:

- crop bounds: left `316481.158`, bottom `4661309.413`, right `323891.158`, top `4670579.413`, CRS `EPSG:26910`
- crop size: approximately 7.41 km x 9.27 km
- planner grid resolution: 62.269 m
- raw resolution: 30 m
- depth range: 1775.89--2573.46 m
- valid fraction before fill: 1.0
- filled cells: 0
- candidate windows found: 56
- selected complexity quantile: 0.72

## Pilot Results

From `survey_grade_pilot_usgs_cascadia/benchmark_method_statistics.csv`:

| Method | Runs | Path km | Coverage % | Excess overlap % | Lines | Feasible |
|---|---:|---:|---:|---:|---:|---:|
| Fixed-Spacing | 1 | 51.93 | 100.00 | 1.633 | 6 | 1.0 |
| Simple Greedy | 1 | 54.63 | 99.994 | 0.240 | 7 | 1.0 |
| Adaptive Spacing without GA | 1 | 52.11 | 100.00 | 0.000 | 6 | 1.0 |
| Fixed-Swath GA | 5 | 52.81 +/- 0.40 | 99.42 +/- 0.87 | 0.004 +/- 0.008 | 7 | 1.0 |
| Full Geometry-Aware Hybrid GA | 5 | 51.99 +/- 0.03 | 99.07 +/- 0.37 | 0.000 +/- 0.000 | 6 | 1.0 |

Interpretation:

- The pilot successfully proves ingestion feasibility for a higher-resolution public bathymetric product.
- The result does not strengthen the path-shortening claim: Hybrid GA is slightly longer than Fixed-Spacing on this pilot crop (`-0.106%` path gain).
- The result does strengthen the overlap-control story: Fixed-Spacing has 1.633% excess-overlap violation, while Adaptive and Hybrid reduce it to 0.0%.
- This agrees with the revised manuscript story: the robust contribution is geometry-aware overlap control and stable line placement, not guaranteed route shortening.

## Candidate Data Audit

Additional local files checked:

- `public_bathy/raw/gmrt/gmrt_monterey_canyon_high.tif`
  - CRS: `EPSG:4326`
  - size: 1093 x 1138
  - status: corrupted/incomplete read (`TIFFReadEncodedStrip` failure)
  - action: do not use as evidence until redownloaded or replaced.
- `public_bathy/raw/noaa/BlueTopo_BC24C27H_20250708.tiff`
  - NOAA Office of Coast Survey BlueTopo product
  - CRS: NAD83 / UTM zone 8N + NAVD88 compound CRS
  - raw resolution: 16 m
  - status: readable
  - caution: NOAA metadata explicitly states not for navigation and includes interpolation/quality caveats.
  - action: possible future public bathymetric grid probe, but not geographically aligned with the current Monterey/Cascadia story.

## Manuscript Policy

Do not add this pilot as a main result yet. It has only one selected crop and five GA seeds, so it is useful as proof that the next evidence layer is technically feasible, not as a submission-ready validation layer.

Recommended next manuscript-safe step:

1. expand the USGS pilot to several automatically selected Cascadia crops,
2. run 20 seeds for stochastic methods,
3. add a matching higher-resolution Monterey/California grid if available,
4. then add a new "survey-grade public grid extension" subsection or supplementary table.
