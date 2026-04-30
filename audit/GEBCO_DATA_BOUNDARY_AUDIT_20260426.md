# GEBCO Data Boundary Audit

- Date: 2026-04-26 CST
- Workspace: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`
- Manuscript: `latex/template.tex`
- Purpose: strengthen the paper's public-data realism without overstating the evidentiary strength of GEBCO-derived numerical benchmarks.

## Why This Pass Was Needed

The manuscript already used GEBCO 2025 public grids correctly as real public gridded bathymetry inputs. However, a reviewer could still ask whether the paper is treating public global bathymetry as survey-grade terrain, mission telemetry, or navigation-grade data. This pass makes that boundary explicit.

## Source Finding

The official GEBCO 2025 Grid documentation describes the grid as a global terrain model / information product derived from heterogeneous source data and interpolation. GEBCO also provides an accompanying Type Identifier (TID) grid that indicates source-data categories for grid cells. The GEBCO disclaimer states that the grid is not intended for navigation or safety-at-sea use.

Source:

- GEBCO Compilation Group. *GEBCO 2025 Grid*. DOI: https://doi.org/10.5285/37c52e96-24ea-67ce-e063-7086abc05f29
- Official product page: https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2025-grid

## Manuscript Changes

File changed:

- `latex/template.tex`

Changes made:

- Added a Methods paragraph after the public scene provenance table explaining that GEBCO is a public global grid, not a survey-grade mission product.
- Stated that the current benchmark uses GEBCO elevation subsets but does not yet condition the planner on TID or source-specific uncertainty.
- Strengthened Discussion wording so the GEBCO layer is presented as a reproducible benchmark input, not as a substitute for safety-of-navigation or field deployment data.

## Resulting Evidence Boundary

Allowed wording:

- real public GEBCO gridded bathymetry input
- public-grid numerical benchmark
- external public bathymetry benchmark
- reproducible prior-map planning input

Disallowed wording:

- field validation
- sea-trial validation
- operational validation
- navigation-grade planning product
- survey-grade mission product
- safety-of-navigation input

## QA Evidence

Compile command:

```bash
cd latex
xelatex -interaction=nonstopmode template.tex > compile_after_gebco_boundary_20260426.log 2>&1
xelatex -interaction=nonstopmode template.tex >> compile_after_gebco_boundary_20260426.log 2>&1
rg -n "Undefined|undefined|Citation|Reference.*undefined|Overfull|Underfull|LaTeX Warning|Fatal|Emergency|Error|Output written" compile_after_gebco_boundary_20260426.log
```

Result:

- `Output written on template.pdf (23 pages).` appears twice.
- No undefined citation/reference warning.
- No overfull/underfull warning.
- No fatal error.

Visual QA:

- `/tmp/geo_gebco_boundary_contact.png`

Synced deliverables:

- `latex/template.pdf`
- `paper_refined.pdf`
- `geo_public_bathy_rebuild.pdf`
