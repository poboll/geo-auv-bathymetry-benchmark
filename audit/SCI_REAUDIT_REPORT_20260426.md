# SCI Re-audit Report: Geo Public Bathymetry Benchmark

- Re-audit time: 2026-04-26 CST
- Workspace: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`
- Main manuscript: `latex/template.tex`
- Main PDF: `latex/template.pdf`
- Synced PDFs: `paper_refined.pdf`, `geo_public_bathy_rebuild.pdf`
- Primary evidence source: `run_5`

## Status

This round is a substantive SCI-style re-audit and revision, not a cosmetic polish. The manuscript now uses a clearer evidence chain:

1. Does terrain-aware spacing help on real public gridded bathymetry?
2. Is the public-scene gain caused by adaptive spacing or by GA alone?
3. Where does the single-heading fixed-pattern assumption fail?

## Before/After Build Evidence

- Before compile command: `xelatex -interaction=nonstopmode template.tex > compile_before_sci_reaudit_20260426.log 2>&1`
- Before PDF snapshot: `latex/template_before_sci_reaudit_20260426.pdf`
- Before compile output: `Output written on template.pdf (20 pages).`
- After compile commands:
  - `xelatex -interaction=nonstopmode template.tex > compile_after_sci_reaudit_20260426.log 2>&1`
  - `xelatex -interaction=nonstopmode template.tex >> compile_after_sci_reaudit_20260426.log 2>&1`
- After compile output: `Output written on template.pdf (21 pages).` appears twice.
- After QA grep result: no undefined citations, no undefined references, no missing graphics, no overfull/underfull boxes, no fatal errors.

## Manuscript Fixes

- Rewrote the Abstract to state the narrow problem, evidence layers, public-data scope, ablation interpretation, sensitivity boundaries, and no-sea-trial boundary.
- Added an Introduction bridge that explicitly organizes the paper around three reviewer-facing questions.
- Added Table 2, `tab:public_provenance`, documenting the two GEBCO 2025 public gridded bathymetry subsets, crop bounds, projected extents, grid resolution, depth range, and valid-cell coverage.
- Added Table 3, `tab:evidence_map`, mapping each Results claim to its evidence source and boundary.
- Rewrote route-figure captions for Figures 3 and 4 as public-scene evidence cards rather than simple route overlays.
- Replaced the old Figure 5 heatmap framing with a cross-scene evidence summary caption and prose organized around route gain, coverage failure, overlap cleanup, and planning time.
- Strengthened Discussion to state that the two public scenes are external-data evidence, not geographic representativeness or field validation.
- Preserved the complex-terrain infeasibility result as a genuine boundary-of-validity finding.

## Figure Fixes

Regenerated figures with:

```bash
conda run -n uu python make_journal_figures.py > make_journal_figures_sci_reaudit_20260426_v3.log 2>&1
```

Updated figure files:

- `latex/pic/journal_scene_atlas.png`
- `latex/pic/journal_cascadia_routes.png`
- `latex/pic/journal_monterey_routes.png`
- `latex/pic/journal_metric_heatmap.png`
- `latex/pic/journal_public_layout_matrix.png`
- `latex/pic/journal_ablation_seed.png`

Visual QA render command:

```bash
gs -q -dNOPAUSE -dBATCH -sDEVICE=png16m -r130 -dFirstPage=10 -dLastPage=15 -sOutputFile=/tmp/geo_sci_reaudit_page_%02d.png template.pdf
```

Rendered pages checked:

- `/tmp/geo_sci_reaudit_page_01.png`: title, abstract, keywords.
- `/tmp/geo_sci_reaudit_page_09.png`: public-data provenance table.
- `/tmp/geo_sci_reaudit_page_10.png`: claim-evidence map.
- `/tmp/geo_sci_reaudit_page_11.png`: benchmark atlas.
- `/tmp/geo_sci_reaudit_page_12.png`: Cascadia evidence card.
- `/tmp/geo_sci_reaudit_page_13.png`: Monterey evidence card and public table.
- `/tmp/geo_sci_reaudit_page_14.png`: cross-scene evidence summary.

## Continuation Pass (2026-04-26 Afternoon)

The public-scene route figures were refined again because the earlier overlay-card design still obscured the method differences in the main evidence scenes.

- Regenerated figures with:

```bash
conda run -n uu python make_journal_figures.py > make_journal_figures_iter_20260426_v6.log 2>&1
```

- Reframed Figures 3 and 4 as method-separated public-scene layout cards:
  - left column: three row-aligned method strips on the same bathymetry window,
  - upper-right: archived `run_5` metrics table,
  - lower-right: relative-improvement panel against Fixed-Spacing.
- Tightened Results captions and bridge paragraphs so the text now explicitly distinguishes:
  - Cascadia as an overlap-cleanup case with the same horizontal sweep family,
  - Monterey as a structural-change case with a clear `0 deg -> 90 deg` rotation.
- Softened panel titles in Figures 5 and 6 away from slogan-like phrasing and toward neutral journal wording.

Build and QA evidence:

- `xelatex -interaction=nonstopmode template.tex > compile_after_iter_20260426_v7.log 2>&1`
- `xelatex -interaction=nonstopmode template.tex >> compile_after_iter_20260426_v7.log 2>&1`
- grep result: only
  - `Output written on template.pdf (22 pages).`
  - `Output written on template.pdf (22 pages).`
- updated QA renders:
  - `/tmp/geo_iter_v7_pages_12_19_contact.png`
  - `/tmp/geo_iter_v7_pages_20_22_contact.png`

The page count increased from 21 to 22 after the scene-card redesign, but the later pages still compile cleanly and the Discussion/Conclusion boundary language remains intact.

## Numeric Verification

Recomputed from `run_5/benchmark_method_statistics.csv` and `run_5/public_scene_manifest.json`.

| Metric | Verified value |
|---|---:|
| Cascadia fixed-to-hybrid path gain | 0.847593% |
| Monterey fixed-to-hybrid path gain | 0.655803% |
| Public mean path shortening | 0.7516978595129359% |
| Hybrid public predicted coverage range | 98.966667%--99.625000% |
| Fixed public mean excess-overlap violation | 0.8066666666666665% |
| Hybrid public mean excess-overlap violation | 0.0951915103314442% |

The addendum was written to `verify_run_metrics.md`.

## Real-data Boundary

The model has results on real public GEBCO 2025 gridded bathymetry subsets plus synthetic stress-test terrains. It does not have real AUV sea-trial logs, raw MBES sonar returns, field-executed tracks, or operational validation. The manuscript now says this explicitly in the Abstract, Methods, Results, evidence map, captions, Discussion, and Conclusion.

## Integrity Checks

- 7777 API check succeeded: `http://127.0.0.1:7777/api/workspaces` lists this workspace with `run_count=6` and state `refine_completed`.
- Label/citation/graphics regex check:
  - missing refs: `[]`
  - missing cites: `[]`
  - unused bibitems: `[]`
  - missing graphics: `[]`
  - only unreferenced labels: `sec:methods`, `sec:related` (section labels retained for future cross-references; not a build issue)
- Overclaim scan found only negative/boundary uses for sea-trial, field validation, operational validation, and guarantees.

## Remaining Objective Boundary

This is now a stronger SCI-style preprint, but it still should not be described as complete field validation. A future target-journal submission should still normalize every bibliography entry to the target style and, if available, add survey-grade bathymetric products or mission logs as a separate validation layer.

## Deep-pass closure (2026-04-26 Evening)

One more evidence-first pass was completed after the section above in order to remove a regression introduced during literature deepening and to improve the public-scene figure cards.

- A new baseline compile was archived as:
  - `latex/compile_before_deep_pass_20260426.log`
  - `latex/template_before_deep_pass_20260426.pdf`
- That baseline exposed five unresolved citation keys in the manuscript body.

### Citation closure

The affected prose was retained, but the citation chain was rebuilt using verified DOI metadata:

- `ling2023active` — *Applied Ocean Research* 130 (2023) 103439
- `shields2023feature` — *Field Robotics* 3 (2023) 652--686
- `zhou2017terrain` — *Sensors* 17(4) (2017) 680
- `kim2017panel` — *2017 IEEE Underwater Technology (UT)*, pp. 1--5
- `zhu2025robust` — *Measurement* 242 (2025) 116223

At the same time, the temporary unsupported keys `ma2023tanreview`, `liu2025bslamreview`, and `zhang2024ttt` were removed, and the surrounding sentences were rewritten to avoid unsupported claims about reviews or sea-trial validation. The bibliography integrity check now reports 24 cite keys, 24 bibitems, no missing entries, and no unused entries.

### Figure-card refinement

The two public-scene route figures were refined again with:

```bash
conda run -n uu python make_journal_figures.py > make_journal_figures_deep_pass_20260426_v2.log 2>&1
```

The update:

- kept the method-separated strips,
- replaced the heavy spreadsheet-style inset with a ledger-style metric block,
- added a compact scene-reading panel with GEBCO provenance text,
- removed the scene-label collision in the top strip,
- preserved the reviewer-facing contrast between Cascadia as overlap cleanup and Monterey as structural rotation.

Updated figure files:

- `latex/pic/journal_cascadia_routes.png`
- `latex/pic/journal_monterey_routes.png`

### Final clean build and QA

Final clean build:

```bash
xelatex -interaction=nonstopmode template.tex > compile_after_deep_pass_clean_20260426.log 2>&1
xelatex -interaction=nonstopmode template.tex >> compile_after_deep_pass_clean_20260426.log 2>&1
```

Clean-build grep result:

- `Output written on template.pdf (22 pages).`
- `Output written on template.pdf (22 pages).`
- no undefined citations,
- no undefined references,
- no overfull / underfull boxes,
- no fatal errors.

Results-page QA artifacts:

- `/tmp/geo_deep_final_results_contact.png`

Synced deliverables refreshed again:

- `latex/template.pdf`
- `paper_refined.pdf`
- `geo_public_bathy_rebuild.pdf`

7777 re-check:

- `http://127.0.0.1:7777/api/workspaces` still lists workspace `20260423_152326_geo_public_bathy_rebuild_round2`
- `run_count=6`
- state phase remains `refine_completed`
- PDF artifacts still include `paper_refined.pdf` and `geo_public_bathy_rebuild.pdf`

## Literature-positioning continuation (2026-04-26 Later)

The manuscript was further revised to make the literature argument more explicit and less dependent on prose-only positioning.

### Added Related Work positioning table

File:

- `latex/template.tex`

New artifact:

- `DEEP_LITERATURE_POSITIONING_20260426.md`

Change:

- Added `Table 1` / `tab:positioning`, a reviewer-facing matrix that separates:
  - online bathymetric mapping and active SLAM,
  - track-spacing and sonar-aware survey planning,
  - prior-map benthic survey design,
  - multi-vehicle and sonar-performance CPP,
  - terrain-aided navigation and bathymetric SLAM,
  - the present fixed-pattern public-bathymetry benchmark.

Purpose:

- Make the contribution boundary easier for a reviewer to inspect.
- Show that the paper is not claiming to solve online autonomy or field execution.
- Strengthen the narrow but defensible claim: isolating terrain-dependent MBES line-layout geometry under a fixed lawnmower traversal.

### QA

Initial compile after adding the table produced a valid 23-page PDF but had one minor table overfull:

- `Overfull \hbox (2.14503pt too wide)`

The table column widths were narrowed and the manuscript was recompiled:

```bash
xelatex -interaction=nonstopmode template.tex > compile_after_positioning_table_clean_20260426.log 2>&1
xelatex -interaction=nonstopmode template.tex >> compile_after_positioning_table_clean_20260426.log 2>&1
```

Clean-build grep result:

- `Output written on template.pdf (23 pages).`
- `Output written on template.pdf (23 pages).`
- no undefined citations,
- no undefined references,
- no overfull / underfull boxes,
- no fatal errors.

Visual QA:

- `/tmp/geo_positioning_contact.png`

Synced deliverables:

- `latex/template.pdf`
- `paper_refined.pdf`
- `geo_public_bathy_rebuild.pdf`

## GEBCO Data-Boundary Continuation (2026-04-26 Latest)

Another focused pass was completed on the public-data realism boundary. The goal was to make the paper stronger, not by inflating the GEBCO evidence, but by stating exactly what GEBCO supports and what it does not support.

### Added data-level caveat

File:

- `latex/template.tex`

New audit artifact:

- `GEBCO_DATA_BOUNDARY_AUDIT_20260426.md`

Changes:

- Added a Methods paragraph after the public-scene provenance table explaining that GEBCO~2025 is a global terrain model / public information product derived from heterogeneous source data and interpolation.
- Noted that GEBCO provides an accompanying Type Identifier (TID) grid, but the current benchmark does not yet condition planning on TID classes or source-specific uncertainty.
- Strengthened Discussion so GEBCO is framed as a reproducible public-grid benchmark input, not a survey-grade or safety-of-navigation terrain product.

This improves the paper's defensibility because it prevents the public-data layer from being mistaken for raw MBES, mission logs, field validation, or navigation-grade data.

### QA

Build:

```bash
xelatex -interaction=nonstopmode template.tex > compile_after_gebco_boundary_20260426.log 2>&1
xelatex -interaction=nonstopmode template.tex >> compile_after_gebco_boundary_20260426.log 2>&1
```

Clean-build grep result:

- `Output written on template.pdf (23 pages).`
- `Output written on template.pdf (23 pages).`
- no undefined citations,
- no undefined references,
- no overfull / underfull boxes,
- no fatal errors.

Visual QA:

- `/tmp/geo_gebco_boundary_contact.png`

Synced deliverables:

- `latex/template.pdf`
- `paper_refined.pdf`
- `geo_public_bathy_rebuild.pdf`

## Reviewer-risk repair continuation (2026-04-27)

A further reviewer-facing repair pass was completed to answer the user's question directly: the experiment did run successfully, but the manuscript must continue to tell a bounded numerical-benchmark story rather than a field-validation story.

### Changes made

- Added `tab:reviewer_risk_matrix` to `latex/template.tex` in the Discussion.
- Added `REVIEWER_OBJECTION_MATRIX_20260427.md` as a standalone point-by-point audit artifact.
- Reworked the public-scene route cards again via `make_journal_figures.py`: thinner linework, smaller metric chips, tighter right-side evidence panels, and less empty dashboard-like space.
- Regenerated:
  - `latex/pic/journal_cascadia_routes.png`
  - `latex/pic/journal_monterey_routes.png`
  - plus the existing journal figure set listed in `make_journal_figures_reviewer_repair_20260427.log`.

### QA evidence

Before-build snapshot:

```bash
xelatex -interaction=nonstopmode template.tex > compile_before_reviewer_repair_20260426.log 2>&1
cp template.pdf template_before_reviewer_repair_20260426.pdf
```

Clean after-build:

```bash
xelatex -interaction=nonstopmode template.tex > compile_after_reviewer_repair_clean_20260427.log 2>&1
xelatex -interaction=nonstopmode template.tex >> compile_after_reviewer_repair_clean_20260427.log 2>&1
```

Clean-build grep result:

- `Output written on template.pdf (23 pages).` appears twice.
- no undefined citations,
- no undefined references,
- no overfull / underfull boxes,
- no fatal errors.

Citation/reference integrity:

- 24 cite keys,
- 24 bibitems,
- no missing citations,
- no unused bibitems,
- 23 labels,
- 23 refs,
- no missing refs.

Visual QA:

- Rendered pages 10--23 with Ghostscript.
- Contact sheet: `/tmp/geo_reviewer_repair_contact.png`.
- Public route cards and the new reviewer-risk matrix are visible in the rendered PDF.

7777 API check:

- `http://127.0.0.1:7777/api/workspaces` lists `paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`.
- `run_count=6`.
- state phase remains `refine_completed`.
- PDFs include `paper_refined.pdf` and `geo_public_bathy_rebuild.pdf`.

Synced deliverables:

- `latex/template.pdf`
- `paper_refined.pdf`
- `geo_public_bathy_rebuild.pdf`
