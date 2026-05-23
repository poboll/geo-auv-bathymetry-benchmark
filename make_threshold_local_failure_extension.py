from __future__ import annotations

import argparse
import csv
import json
import math
from collections import deque
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

import geo_public_bathy_benchmark as geo
import journal_heatmap_style as jhs
import make_survey_grade_pilot as pilot


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "threshold_local_failure_extension"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)
USGS_MANIFEST = ROOT / "survey_grade_extension_usgs_cascadia" / "public_scene_manifest.json"

COVERAGE_THRESHOLDS = (95.0, 97.0, 98.0, 99.0, 99.5)
OVERLAP_GATES = (1.0, 2.0, 3.0, 5.0)
METHODS = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
)
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adaptive",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
}
SCENE_LABELS = {
    "gebco_cascadia_margin_moderate": "GEBCO Cascadia",
    "gebco_monterey_canyon_complex": "GEBCO Monterey",
    "usgs_southern_cascadia_30m_high": "USGS High",
}


def _safe_json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _save_white_rgb_figure(fig: plt.Figure, path: Path) -> None:
    """Save with a real white RGB background, avoiding alpha-renderer artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=430, bbox_inches="tight", facecolor="white", transparent=False, pad_inches=0.035)
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        background.convert("RGB").save(path)


def _read_usgs_high_manifest() -> dict[str, Any]:
    items = json.loads(USGS_MANIFEST.read_text(encoding="utf-8"))
    for item in items:
        if item["scene_id"] == "usgs_southern_cascadia_30m_high":
            return item
    raise KeyError("usgs_southern_cascadia_30m_high not found in USGS extension manifest.")


def load_usgs_high_scene() -> geo.TerrainScene:
    manifest = _read_usgs_high_manifest()
    raw_file = Path(manifest["raw_file"])
    if not raw_file.exists():
        pilot.ensure_extracted()
        raw_file = pilot.RASTER_PATH
    bounds = manifest["crop_bounds"]
    with rasterio.open(raw_file) as dataset:
        window = from_bounds(
            float(bounds["left"]),
            float(bounds["bottom"]),
            float(bounds["right"]),
            float(bounds["top"]),
            transform=dataset.transform,
        ).round_offsets().round_lengths()
        arr = dataset.read(
            1,
            window=window,
            out_shape=(geo.GRID_NY, geo.GRID_NX),
            masked=True,
            resampling=Resampling.bilinear,
        )
        depth = pilot.depth_from_masked(arr)
        depth, fill_info = geo._fill_depth_gaps(depth)
        crop_bounds = rasterio.windows.bounds(window, dataset.transform)
        width_m = float(crop_bounds[2] - crop_bounds[0])
        height_m = float(crop_bounds[3] - crop_bounds[1])
        x = np.linspace(0.0, width_m, geo.GRID_NX)
        y = np.linspace(0.0, height_m, geo.GRID_NY)
        xx, yy = np.meshgrid(x, y)
        merged_manifest = dict(manifest)
        merged_manifest["raw_file"] = str(raw_file)
        merged_manifest["missing_value_handling_recomputed"] = fill_info
        merged_manifest["diagnostic_rebuild_policy"] = (
            "Rebuilt from the exact crop bounds recorded in the USGS extension manifest."
        )
    return geo.TerrainScene(
        scene_id=manifest["scene_id"],
        display_name="USGS Cascadia 30 m High",
        scene_group="public",
        terrain_class=manifest["terrain_class"],
        x=xx,
        y=yy,
        z=depth,
        source=manifest["source"],
        download_url=manifest["download_url"],
        raw_file=str(raw_file),
        manifest_entry=merged_manifest,
    )


def load_scenes() -> list[geo.TerrainScene]:
    gebco_scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    return gebco_scenes + [load_usgs_high_scene()]


def representative_plans(scene: geo.TerrainScene, seed_count: int) -> list[geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    plans: list[geo.PlanResult] = [fixed, adaptive]
    for seed in range(seed_count):
        plans.append(geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed))
    return plans


def connected_uncovered_stats(gap_map: np.ndarray) -> tuple[int, int, float]:
    visited = np.zeros_like(gap_map, dtype=bool)
    rows, cols = gap_map.shape
    components = 0
    largest = 0
    for r in range(rows):
        for c in range(cols):
            if not gap_map[r, c] or visited[r, c]:
                continue
            components += 1
            size = 0
            queue: deque[tuple[int, int]] = deque([(r, c)])
            visited[r, c] = True
            while queue:
                rr, cc = queue.popleft()
                size += 1
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if 0 <= nr < rows and 0 <= nc < cols and gap_map[nr, nc] and not visited[nr, nc]:
                        visited[nr, nc] = True
                        queue.append((nr, nc))
            largest = max(largest, size)
    largest_pct = 100.0 * largest / max(int(gap_map.size), 1)
    return components, largest, largest_pct


def evaluate_local_metrics(scene: geo.TerrainScene, plan: geo.PlanResult) -> dict[str, Any]:
    context = geo.make_context(scene, plan.orientation_deg)
    positions = np.sort(plan.line_positions)
    counts = geo.coverage_counts(context.v_grid, positions, context.swath_width)
    excess = geo.cellwise_excess_overlap(context.v_grid, positions, context.swath_width)
    gap_map = counts < 1
    components, largest_cells, largest_pct = connected_uncovered_stats(gap_map)
    count_hist = {str(k): int(v) for k, v in zip(*np.unique(np.clip(counts, 0, 5), return_counts=True))}
    base = {
        "scene_id": scene.scene_id,
        "scene_name": scene.display_name,
        "method": plan.method,
        "seed": int(plan.seed),
        "orientation_deg": float(plan.orientation_deg),
        "line_count": int(plan.line_count),
        "path_length_km": float(plan.path_length_km),
        "coverage_pct": float(plan.coverage_pct),
        "uncovered_pct": float(100.0 - plan.coverage_pct),
        "excess_overlap_pct": float(plan.excess_overlap_pct),
        "feasible_97_3": int(plan.coverage_pct >= 97.0 and plan.excess_overlap_pct <= 3.0),
        "uncovered_component_count": int(components),
        "largest_uncovered_patch_cells": int(largest_cells),
        "largest_uncovered_patch_pct": float(largest_pct),
        "coverage_count_0_cells": int(np.sum(counts == 0)),
        "coverage_count_1_cells": int(np.sum(counts == 1)),
        "coverage_count_2_cells": int(np.sum(counts == 2)),
        "coverage_count_ge3_cells": int(np.sum(counts >= 3)),
        "coverage_count_hist_capped_5": json.dumps(count_hist, sort_keys=True),
        "cell_excess_overlap_p95": float(np.percentile(excess, 95)),
        "cell_excess_overlap_p99": float(np.percentile(excess, 99)),
        "cell_excess_overlap_max": float(np.max(excess)),
        "cell_excess_overlap_nonzero_pct": float(np.mean(excess > 0.0) * 100.0),
    }
    for threshold in COVERAGE_THRESHOLDS:
        base[f"pass_coverage_{threshold:g}"] = int(plan.coverage_pct >= threshold)
    for gate in OVERLAP_GATES:
        base[f"pass_overlap_{gate:g}"] = int(plan.excess_overlap_pct <= gate)
    for threshold in COVERAGE_THRESHOLDS:
        for gate in OVERLAP_GATES:
            base[f"pass_C{threshold:g}_O{gate:g}"] = int(plan.coverage_pct >= threshold and plan.excess_overlap_pct <= gate)
    return base


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["scene_id"], row["method"]), []).append(row)
    summary: list[dict[str, Any]] = []
    numeric_keys = [
        "path_length_km",
        "coverage_pct",
        "uncovered_pct",
        "excess_overlap_pct",
        "feasible_97_3",
        "uncovered_component_count",
        "largest_uncovered_patch_pct",
        "cell_excess_overlap_p95",
        "cell_excess_overlap_p99",
        "cell_excess_overlap_max",
        "cell_excess_overlap_nonzero_pct",
    ]
    pass_keys = [
        f"pass_C{threshold:g}_O{gate:g}"
        for threshold in COVERAGE_THRESHOLDS
        for gate in OVERLAP_GATES
    ]
    for (scene_id, method), items in sorted(grouped.items()):
        record: dict[str, Any] = {
            "scene_id": scene_id,
            "scene_label": SCENE_LABELS.get(scene_id, scene_id),
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "n_runs": len(items),
        }
        for key in numeric_keys + pass_keys:
            vals = np.asarray([float(item[key]) for item in items], dtype=float)
            record[f"{key}_mean"] = float(np.mean(vals))
            record[f"{key}_min"] = float(np.min(vals))
            record[f"{key}_max"] = float(np.max(vals))
        summary.append(record)
    return summary


def _summary_lookup(summary_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["scene_id"], row["method"]): row for row in summary_rows}


def make_figure(summary_rows: list[dict[str, Any]]) -> None:
    scene_ids = list(SCENE_LABELS.keys())
    method_names = list(METHODS)
    lookup = _summary_lookup(summary_rows)

    coverage = np.full((len(scene_ids), len(method_names)), np.nan)
    overlap = np.full_like(coverage, np.nan)
    largest_gap = np.full_like(coverage, np.nan)
    p99 = np.full_like(coverage, np.nan)
    strict_pass = np.full_like(coverage, np.nan)
    for i, scene_id in enumerate(scene_ids):
        for j, method in enumerate(method_names):
            row = lookup[(scene_id, method)]
            coverage[i, j] = row["coverage_pct_mean"]
            overlap[i, j] = row["excess_overlap_pct_mean"]
            largest_gap[i, j] = row["largest_uncovered_patch_pct_mean"]
            p99[i, j] = row["cell_excess_overlap_p99_mean"]
            strict_pass[i, j] = row["pass_C99_O2_mean"]

    jhs.apply_rc(base_font=8.92)

    fig, axes_grid = plt.subplots(2, 3, figsize=(7.35, 3.66), facecolor=jhs.BG)
    axes = list(axes_grid.flat)
    matrices = [
        (
            coverage,
            mcolors.TwoSlopeNorm(vmin=96.5, vcenter=97.0, vmax=100.0),
            jhs.COVERAGE_CMAP,
            "(a) Coverage (%)",
            "{:.1f}",
            lambda value: value < 97.0,
        ),
        (
            overlap,
            mcolors.Normalize(vmin=0.0, vmax=max(3.0, float(np.nanmax(overlap)))),
            jhs.FAILURE_CMAP,
            "(b) Mean excess (%)",
            "{:.2f}",
            lambda value: value > 3.0,
        ),
        (
            largest_gap,
            mcolors.Normalize(vmin=0.0, vmax=max(1.0, float(np.nanmax(largest_gap)))),
            jhs.FAILURE_CMAP,
            "(c) Largest gap (%)",
            "{:.2f}",
            lambda value: value > 0.5,
        ),
        (
            p99,
            mcolors.Normalize(vmin=0.0, vmax=max(3.0, float(np.nanmax(p99)))),
            jhs.FAILURE_CMAP,
            "(d) p99 excess (%)",
            "{:.1f}",
            lambda value: value > 3.0,
        ),
        (
            strict_pass,
            mcolors.Normalize(vmin=0.0, vmax=1.0),
            jhs.COVERAGE_CMAP,
            "(e) Pass C99/O2",
            "{:.2f}",
            lambda value: value < 1.0,
        ),
        (
            np.asarray([[float(lookup[(scene_id, method)]["pass_C97_O3_mean"]) for method in method_names] for scene_id in scene_ids], dtype=float),
            mcolors.Normalize(vmin=0.0, vmax=1.0),
            jhs.COVERAGE_CMAP,
            "(f) Pass C97/O3",
            "{:.2f}",
            lambda value: value < 1.0,
        ),
    ]
    xlabels = [METHOD_LABELS[method] for method in method_names]
    ylabels = ["Cascadia", "Monterey", "USGS-H"]
    for ax_idx, (ax, (data, norm, cmap, title, fmt, mark_bad)) in enumerate(zip(axes, matrices)):
        ax.imshow(data, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        jhs.style_heatmap_axis(
            ax,
            title,
            xlabels,
            ylabels if ax_idx in (0, 3) else None,
            data.shape[0],
            rotate_x=0,
        )
        jhs.annotate_cells(ax, data, cmap, norm, fmt, mark_bad=mark_bad, fontsize=7.08)

    fig.subplots_adjust(left=0.066, right=0.998, top=0.926, bottom=0.092, wspace=0.062, hspace=0.180)
    OUT.mkdir(parents=True, exist_ok=True)
    _save_white_rgb_figure(fig, OUT / "threshold_local_failure_journal.png")
    for pic_dir in PIC_DIRS:
        _save_white_rgb_figure(fig, pic_dir / "journal_threshold_local_failure.png")
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]], seed_count: int) -> None:
    lookup = _summary_lookup(summary_rows)
    lines = [
        "# Threshold and Local-failure Diagnostics\n\n",
        "This extension rebuilds the two primary GEBCO scenes and the USGS high-complexity public-grid crop, ",
        "then evaluates whether scene-level means hide stricter threshold or local failure modes.\n\n",
        f"- Hybrid GA seeds: 0--{seed_count - 1}\n",
        f"- Coverage thresholds: {', '.join(f'{v:g}%' for v in COVERAGE_THRESHOLDS)}\n",
        f"- Mean-excess-overlap gates: {', '.join(f'{v:g}%' for v in OVERLAP_GATES)}\n",
        "- Local metrics: uncovered components, largest uncovered patch, p95/p99/max cellwise excess overlap.\n\n",
        "| Scene | Method | C mean (%) | O mean (%) | C99/O2 pass rate | Largest gap (%) | p99 cell excess (%) |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for scene_id in SCENE_LABELS:
        for method in METHODS:
            row = lookup[(scene_id, method)]
            lines.append(
                f"| {SCENE_LABELS[scene_id]} | {METHOD_LABELS[method]} | "
                f"{row['coverage_pct_mean']:.2f} | {row['excess_overlap_pct_mean']:.3f} | "
                f"{row['pass_C99_O2_mean']:.2f} | {row['largest_uncovered_patch_pct_mean']:.3f} | "
                f"{row['cell_excess_overlap_p99_mean']:.2f} |\n"
            )
    lines.extend(
        [
            "\n## Interpretation\n\n",
            "- The default 97%/3% benchmark gate is not equivalent to a stricter hydrographic acceptance rule.\n",
            "- The USGS high-complexity crop remains the strongest positive case because Fixed-Spacing carries a very large overlap burden while Hybrid remains feasible under the default gate.\n",
            "- Under stricter 99%/2% screening, the GEBCO Hybrid layouts are not uniformly accepted, which should be reported as margin limitation rather than hidden.\n",
            "- Largest uncovered-patch and p99-overlap metrics help expose local failure that scene-level means can obscure; they remain numerical raster-evaluator diagnostics, not survey-grade QA.\n",
        ]
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-count", type=int, default=20)
    args = parser.parse_args()
    if args.seed_count < 1:
        raise ValueError("--seed-count must be at least 1")

    OUT.mkdir(parents=True, exist_ok=True)
    scenes = load_scenes()
    all_rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for scene in scenes:
        print(f"diagnosing {scene.scene_id}", flush=True)
        manifests.append(scene.manifest_entry)
        for plan in representative_plans(scene, args.seed_count):
            all_rows.append(evaluate_local_metrics(scene, plan))
    summary_rows = summarize(all_rows)
    write_csv(OUT / "threshold_local_failure_raw.csv", all_rows)
    write_csv(OUT / "threshold_local_failure_summary.csv", summary_rows)
    _safe_json_dump(OUT / "threshold_local_failure_summary.json", {"summary_rows": summary_rows, "manifests": manifests})
    make_figure(summary_rows)
    write_report(summary_rows, args.seed_count)
    print(json.dumps({"out_dir": str(OUT), "summary_rows": summary_rows}, indent=2))


if __name__ == "__main__":
    main()
