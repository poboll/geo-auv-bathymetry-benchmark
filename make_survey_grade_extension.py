from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap, LightSource, Normalize, TwoSlopeNorm
from matplotlib.lines import Line2D
from PIL import Image
from rasterio.enums import Resampling
from rasterio.windows import Window

import geo_public_bathy_benchmark as geo
import make_survey_grade_pilot as pilot


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "survey_grade_extension_usgs_cascadia"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)
LIGHT = LightSource(azdeg=318, altdeg=42)


def enumerate_candidate_windows(dataset: rasterio.io.DatasetReader) -> list[tuple[float, Window, dict[str, float]]]:
    xres = abs(float(dataset.transform.a))
    yres = abs(float(dataset.transform.e))
    crop_w = max(geo.GRID_NX, int(round(geo.PUBLIC_CROP_WIDTH_M / xres)))
    crop_h = max(geo.GRID_NY, int(round(geo.PUBLIC_CROP_HEIGHT_M / yres)))

    overview_w = 1000
    overview_h = max(1, int(round(dataset.height * overview_w / dataset.width)))
    overview = dataset.read(1, out_shape=(overview_h, overview_w), masked=True, resampling=Resampling.nearest)
    overview_depth = pilot.depth_from_masked(overview)
    overview_valid = np.isfinite(overview_depth)

    scale_x = dataset.width / overview_w
    scale_y = dataset.height / overview_h
    crop_w_overview = max(2, int(round(crop_w / scale_x)))
    crop_h_overview = max(2, int(round(crop_h / scale_y)))
    step_x = max(3, crop_w_overview * 2)
    step_y = max(3, crop_h_overview * 2)

    candidates: list[tuple[float, Window, dict[str, float]]] = []
    for oy in range(0, max(overview_h - crop_h_overview, 1), step_y):
        for ox in range(0, max(overview_w - crop_w_overview, 1), step_x):
            patch_valid = overview_valid[oy : oy + crop_h_overview, ox : ox + crop_w_overview]
            if patch_valid.size == 0 or float(np.mean(patch_valid)) < 0.90:
                continue
            center_col = int(round((ox + 0.5 * crop_w_overview) * scale_x))
            center_row = int(round((oy + 0.5 * crop_h_overview) * scale_y))
            col = min(max(center_col - crop_w // 2, 0), dataset.width - crop_w)
            row = min(max(center_row - crop_h // 2, 0), dataset.height - crop_h)
            window = Window(col, row, crop_w, crop_h)
            arr = dataset.read(1, window=window, masked=True)
            depth = pilot.depth_from_masked(arr)
            metrics = pilot.candidate_complexity(depth, xres, yres)
            if metrics is None:
                continue
            metrics = dict(metrics)
            metrics["overview_col"] = float(ox)
            metrics["overview_row"] = float(oy)
            candidates.append((metrics["complexity"], window, metrics))

    candidates.sort(key=lambda item: item[0])
    for rank, (_, _, metrics) in enumerate(candidates):
        metrics["complexity_rank"] = rank
        metrics["candidate_count"] = len(candidates)
        metrics["complexity_quantile_empirical"] = rank / max(len(candidates) - 1, 1)
    return candidates


def select_windows(
    candidates: list[tuple[float, Window, dict[str, float]]],
    quantiles: list[float],
) -> list[tuple[str, Window, dict[str, float]]]:
    if not candidates:
        raise RuntimeError("No valid USGS Cascadia candidate windows found.")
    labels = ["low", "medium", "high", "very_high", "extreme"]
    selected: list[tuple[str, Window, dict[str, float]]] = []
    used: set[tuple[int, int]] = set()
    for idx, q in enumerate(quantiles):
        target = int(round(q * (len(candidates) - 1)))
        order = sorted(range(len(candidates)), key=lambda i: abs(i - target))
        chosen_i = None
        for i in order:
            _, window, _ = candidates[i]
            key = (int(window.col_off), int(window.row_off))
            if key not in used:
                chosen_i = i
                used.add(key)
                break
        if chosen_i is None:
            chosen_i = target
        _, window, metrics = candidates[chosen_i]
        metrics = dict(metrics)
        metrics["requested_complexity_quantile"] = q
        label = labels[idx] if idx < len(labels) else f"q{int(q * 100)}"
        selected.append((label, window, metrics))
    return selected


def scene_from_window(
    dataset: rasterio.io.DatasetReader,
    label: str,
    window: Window,
    metrics: dict[str, float],
) -> geo.TerrainScene:
    arr = dataset.read(
        1,
        window=window,
        out_shape=(geo.GRID_NY, geo.GRID_NX),
        masked=True,
        resampling=Resampling.bilinear,
    )
    depth = pilot.depth_from_masked(arr)
    depth, fill_info = geo._fill_depth_gaps(depth)
    bounds = rasterio.windows.bounds(window, dataset.transform)
    width_m = float(bounds[2] - bounds[0])
    height_m = float(bounds[3] - bounds[1])
    x = np.linspace(0.0, width_m, geo.GRID_NX)
    y = np.linspace(0.0, height_m, geo.GRID_NY)
    xx, yy = np.meshgrid(x, y)
    scene_id = f"usgs_southern_cascadia_30m_{label}"
    manifest = {
        "scene_id": scene_id,
        "source": "USGS Southern Cascadia 30 m composite bathymetry, v2",
        "download_url": "https://doi.org/10.5066/P9C5DBMR",
        "license": "USGS public data release",
        "raw_file": str(pilot.RASTER_PATH),
        "crop_bounds": {
            "left": float(bounds[0]),
            "bottom": float(bounds[1]),
            "right": float(bounds[2]),
            "top": float(bounds[3]),
            "crs": dataset.crs.to_string() if dataset.crs else None,
        },
        "raw_resolution_m": {
            "x": abs(float(dataset.transform.a)),
            "y": abs(float(dataset.transform.e)),
        },
        "planner_grid_resolution_m": round(max(width_m / max(geo.GRID_NX - 1, 1), height_m / max(geo.GRID_NY - 1, 1)), 3),
        "depth_range_m": [float(np.nanmin(depth)), float(np.nanmax(depth))],
        "terrain_class": f"survey_grade_cascadia_{label}",
        "selection_metrics": metrics,
        "missing_value_handling": fill_info,
        "provider": "USGS",
        "extension_policy": "Separate survey-grade public grid extension; not mixed into run_5.",
    }
    return geo.TerrainScene(
        scene_id=scene_id,
        display_name=f"USGS Cascadia 30 m {label.title()}",
        scene_group="public",
        terrain_class=manifest["terrain_class"],
        x=xx,
        y=yy,
        z=depth,
        source=manifest["source"],
        download_url=manifest["download_url"],
        raw_file=str(pilot.RASTER_PATH),
        manifest_entry=manifest,
    )


def run_scene(scene: geo.TerrainScene, seeds: tuple[int, ...]) -> list[geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(scene)
    greedy, greedy_base = geo.simple_greedy_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    results: list[geo.PlanResult] = [fixed, greedy, adaptive]
    for seed in seeds:
        results.append(geo.fixed_swath_ga_plan(scene, greedy_base, seed))
        results.append(geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed))
    return results


def save_extension_preview(scenes: list[geo.TerrainScene], results: list[geo.PlanResult]) -> None:
    methods = ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]
    colors = {
        "Fixed-Spacing": "#727b86",
        "Adaptive Spacing w/o GA": "#168d80",
        "Full Geometry-Aware Hybrid GA": "#c76032",
    }
    labels = {
        "Fixed-Spacing": "Fixed",
        "Adaptive Spacing w/o GA": "Adaptive",
        "Full Geometry-Aware Hybrid GA": "Hybrid",
    }

    def mean_result(scene_id: str, method: str, field: str) -> float:
        vals = [float(getattr(row, field)) for row in results if row.scene_id == scene_id and row.method == method]
        return float(np.mean(vals))

    def representative(scene_id: str, method: str) -> geo.PlanResult:
        rows = [row for row in results if row.scene_id == scene_id and row.method == method]
        rows.sort(key=lambda row: (row.seed < 0, row.seed))
        return rows[0]

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "font.size": 7.0,
            "axes.titlesize": 7.55,
            "axes.labelsize": 6.75,
            "xtick.labelsize": 6.05,
            "ytick.labelsize": 6.05,
            "axes.linewidth": 0.45,
        }
    )
    path_gain_cmap = LinearSegmentedColormap.from_list(
        "ext_gain",
        ["#f7fcfb", "#d8f1ee", "#8ccfc7", "#1d8f84", "#0e5f59"],
    )
    coverage_cmap = LinearSegmentedColormap.from_list(
        "ext_cov",
        ["#b84a3a", "#f6f2ec", "#d3ece8", "#1b877d"],
    )
    overlap_cmap = LinearSegmentedColormap.from_list(
        "ext_overlap",
        ["#fff9f2", "#f8ceb0", "#e3895d", "#7c3325"],
    )

    fig = plt.figure(figsize=(7.55, 5.02), facecolor="white")
    outer = fig.add_gridspec(2, 1, height_ratios=[1.82, 1.0], hspace=0.150)
    map_grid = outer[0, 0].subgridspec(1, len(scenes), wspace=0.060)
    metric_grid = outer[1, 0].subgridspec(1, 3, wspace=0.190)
    fig.text(
        0.03,
        0.985,
        "USGS Southern Cascadia extension",
        ha="left",
        va="top",
        fontsize=7.8,
        fontweight="bold",
        color="#1f2933",
    )
    fig.text(
        0.03,
        0.962,
        "Straight lines are fixed-pattern survey transects; matrices report extension means for each crop.",
        ha="left",
        va="top",
        fontsize=4.35,
        color="#667483",
    )

    scene_labels: list[str] = []
    gain_matrix = np.zeros((len(scenes), len(methods)), dtype=float)
    coverage_matrix = np.zeros((len(scenes), len(methods)), dtype=float)
    overlap_matrix = np.zeros((len(scenes), len(methods)), dtype=float)

    for row_idx, scene in enumerate(scenes):
        manifest = scene.manifest_entry
        metrics = manifest.get("selection_metrics", {})
        extent = (
            scene.x.min() / geo.NM_TO_M,
            scene.x.max() / geo.NM_TO_M,
            scene.y.min() / geo.NM_TO_M,
            scene.y.max() / geo.NM_TO_M,
        )

        ax_map = fig.add_subplot(map_grid[0, row_idx])
        dx = float(np.abs(scene.x[0, 1] - scene.x[0, 0])) if scene.x.shape[1] > 1 else 1.0
        dy = float(np.abs(scene.y[1, 0] - scene.y[0, 0])) if scene.y.shape[0] > 1 else 1.0
        z_fill = np.where(np.isfinite(scene.z), scene.z, float(np.nanmedian(scene.z)))
        shaded = LIGHT.shade(
            z_fill,
            cmap=geo.BATHY_CMAP,
            vert_exag=0.85,
            dx=max(dx, 1.0),
            dy=max(dy, 1.0),
            blend_mode="soft",
        )
        ax_map.imshow(shaded, extent=extent, origin="lower", aspect="equal")
        if float(np.nanmax(scene.z) - np.nanmin(scene.z)) > 1e-6:
            levels = np.linspace(float(np.nanmin(scene.z)), float(np.nanmax(scene.z)), 11)
            ax_map.contour(
                scene.x / geo.NM_TO_M,
                scene.y / geo.NM_TO_M,
                scene.z,
                levels=levels[1:-1:2],
                colors="#ffffff",
                linewidths=0.22,
                alpha=0.22,
            )
        preview_lines = 8 if row_idx < 2 else 10
        for method, lw, alpha in [
            ("Fixed-Spacing", 0.42, 0.64),
            ("Full Geometry-Aware Hybrid GA", 0.58, 0.86),
        ]:
            result = representative(scene.scene_id, method)
            phi = math.radians(result.orientation_deg)
            for pos in pilot.positions_for_preview(result.line_positions, max_lines=preview_lines):
                xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
                if xs.size:
                    ax_map.plot(
                        xs / geo.NM_TO_M,
                        ys / geo.NM_TO_M,
                        color=colors[method],
                        lw=lw,
                        alpha=alpha,
                        solid_capstyle="round",
                    )
        fixed_rep = representative(scene.scene_id, "Fixed-Spacing")
        hybrid_rep = representative(scene.scene_id, "Full Geometry-Aware Hybrid GA")
        scene_label = scene.display_name.replace("USGS Cascadia 30 m ", "")
        scene_labels.append(scene_label)
        relief = float(metrics.get("relief", np.nan))
        q = float(metrics.get("complexity_quantile_empirical", np.nan))
        ax_map.text(
            0.018,
            0.965,
            f"{scene_label} crop",
            transform=ax_map.transAxes,
            ha="left",
            va="top",
            fontsize=6.35,
            fontweight="bold",
            color="#1f2933",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 0.55},
        )
        ax_map.text(
            0.03,
            0.04,
            f"q={q:.2f}  relief={relief:.0f} m",
            transform=ax_map.transAxes,
            ha="left",
            va="bottom",
            fontsize=5.35,
            color="#263440",
            bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "#d7e0e7", "linewidth": 0.35, "alpha": 0.86},
        )
        ax_map.text(
            0.985,
            0.045,
            f"psi {fixed_rep.orientation_deg:.0f} deg -> {hybrid_rep.orientation_deg:.0f} deg; "
            f"n {len(fixed_rep.line_positions)} -> {len(hybrid_rep.line_positions)}",
            transform=ax_map.transAxes,
            ha="right",
            va="bottom",
            fontsize=4.35,
            color="#263440",
            bbox={"boxstyle": "round,pad=0.16", "facecolor": "white", "edgecolor": "#d7e0e7", "linewidth": 0.32, "alpha": 0.82},
        )
        ax_map.set_xticks([])
        ax_map.set_yticks([])
        for spine in ax_map.spines.values():
            spine.set_color("#b7c3ce")
            spine.set_linewidth(0.45)
        if row_idx == 0:
            legend_handles = [
                Line2D([0], [0], color=colors["Fixed-Spacing"], lw=1.0, label="Fixed lines"),
                Line2D([0], [0], color=colors["Full Geometry-Aware Hybrid GA"], lw=1.2, label="Hybrid lines"),
            ]
            leg = ax_map.legend(
                handles=legend_handles,
                loc="upper left",
                bbox_to_anchor=(0.01, 0.84),
                frameon=True,
                framealpha=0.90,
                borderpad=0.25,
                handlelength=1.9,
                fontsize=4.95,
            )
            leg.get_frame().set_edgecolor("#d7e0e7")
            leg.get_frame().set_linewidth(0.35)
            leg.get_frame().set_facecolor("white")

        fixed_path = mean_result(scene.scene_id, "Fixed-Spacing", "path_length_km")
        for col_idx, method in enumerate(methods):
            gain_matrix[row_idx, col_idx] = (fixed_path - mean_result(scene.scene_id, method, "path_length_km")) / fixed_path * 100.0
            coverage_matrix[row_idx, col_idx] = mean_result(scene.scene_id, method, "coverage_pct")
            overlap_matrix[row_idx, col_idx] = mean_result(scene.scene_id, method, "excess_overlap_pct")

    method_headers = ["Fixed", "Adapt.", "Hybrid"]
    metric_axes = [fig.add_subplot(metric_grid[0, i]) for i in range(3)]
    cov_min = float(np.min(coverage_matrix))
    cov_max = float(np.max(coverage_matrix))
    if cov_min < 97.0 < cov_max:
        cov_norm = TwoSlopeNorm(vmin=cov_min, vcenter=97.0, vmax=cov_max)
    else:
        cov_norm = Normalize(vmin=cov_min, vmax=cov_max)

    metric_specs = [
        (metric_axes[0], gain_matrix, path_gain_cmap, Normalize(vmin=float(np.min(gain_matrix)), vmax=float(np.max(gain_matrix))), "Path gain (%)", "{:.1f}"),
        (metric_axes[1], coverage_matrix, coverage_cmap, cov_norm, "Coverage (%)", "{:.1f}"),
        (metric_axes[2], overlap_matrix, overlap_cmap, Normalize(vmin=float(np.min(overlap_matrix)), vmax=float(np.max(overlap_matrix))), "Excess overlap (%)", "{:.1f}"),
    ]

    for ax_idx, (ax, data, cmap, norm, title, fmt) in enumerate(metric_specs):
        im = ax.imshow(data, cmap=cmap, norm=norm, aspect="equal")
        ax.set_title(title, color="#1f2933", fontweight="bold", fontsize=6.05, pad=2.8)
        ax.set_xticks(np.arange(len(methods)))
        ax.set_xticklabels(method_headers)
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, pad=1.2, length=0.0)
        for tick in ax.get_xticklabels():
            tick.set_fontsize(5.10)
        ax.set_yticks(np.arange(len(scene_labels)))
        ax.set_yticklabels(scene_labels if ax_idx == 0 else [])
        ax.tick_params(axis="y", left=False, right=False, labelleft=ax_idx == 0, length=0.0, pad=1.5)
        for spine in ax.spines.values():
            spine.set_color("#c8d4df")
            spine.set_linewidth(0.55)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                rgba = im.cmap(im.norm(float(data[i, j])))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                ax.text(
                    j,
                    i,
                    fmt.format(float(data[i, j])),
                    ha="center",
                    va="center",
                    fontsize=5.55,
                    color="white" if luminance < 0.43 else "#263440",
                )

    fig.subplots_adjust(left=0.050, right=0.990, top=0.925, bottom=0.070)
    output_paths = [OUT / "survey_grade_extension_journal.png"]
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
        output_paths.append(pic_dir / "journal_usgs_extension.png")
    for output_path in output_paths:
        fig.savefig(output_path, dpi=420, bbox_inches="tight", facecolor="white", pad_inches=0.038)
        rgba = Image.open(output_path).convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        bg.alpha_composite(rgba)
        bg.convert("RGB").save(output_path, optimize=True)
    plt.close(fig)


def write_extension_report(summary_rows: list[dict], scenes: list[geo.TerrainScene], seeds: tuple[int, ...]) -> None:
    lookup = {(row["scene_id"], row["method"]): row for row in summary_rows}
    lines = [
        "# USGS Southern Cascadia Multi-crop Extension\n",
        "This is a separate survey-grade public grid extension. It is not mixed into the primary benchmark.\n",
        f"- Source: USGS Southern Cascadia 30 m composite bathymetry, v2 ({scenes[0].download_url})\n",
        f"- Crops: {len(scenes)}\n",
        f"- Stochastic seeds: {seeds[0]}--{seeds[-1]}\n\n",
        "| Scene | Method | Path km | Coverage % | Excess overlap % | Lines | Feasible |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for scene in scenes:
        for method in ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]:
            row = lookup[(scene.scene_id, method)]
            lines.append(
                f"| {scene.display_name} | {method} | {float(row['path_length_km_mean']):.2f} | "
                f"{float(row['coverage_pct_mean']):.2f} | {float(row['excess_overlap_pct_mean']):.3f} | "
                f"{float(row['line_count_mean']):.1f} | {float(row['feasible_mean']):.1f} |\n"
            )
    lines.append("\n## Interpretation\n\n")
    lines.append(
        "This extension is designed to test whether the overlap-control finding survives on several higher-resolution "
        "public-grid crops. It should be treated as an extension candidate until matched Monterey/California data are "
        "added and the manuscript text is revised deliberately.\n"
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantiles", default="0.25,0.55,0.80")
    parser.add_argument("--seed-count", type=int, default=20)
    args = parser.parse_args()
    quantiles = [float(item) for item in args.quantiles.split(",") if item.strip()]
    seeds = tuple(range(args.seed_count))

    OUT.mkdir(parents=True, exist_ok=True)
    pilot.ensure_extracted()
    with rasterio.open(pilot.RASTER_PATH) as dataset:
        candidates = enumerate_candidate_windows(dataset)
        selected = select_windows(candidates, quantiles)
        scenes = [scene_from_window(dataset, label, window, metrics) for label, window, metrics in selected]

    all_results: list[geo.PlanResult] = []
    for scene in scenes:
        print(f"running {scene.scene_id}", flush=True)
        all_results.extend(run_scene(scene, seeds))

    summary_rows = geo.summarize_results(all_results)
    public_manifest = [scene.manifest_entry for scene in scenes]
    means, stderrs, final_info = geo.build_final_info(summary_rows)
    geo.write_results_tables(OUT, all_results, summary_rows)
    geo.write_public_manifest(OUT, scenes)
    geo.write_summary_bundle(OUT, all_results, summary_rows, public_manifest, means, stderrs)
    np.save(OUT / "all_results.npy", final_info, allow_pickle=True)
    save_extension_preview(scenes, all_results)
    write_extension_report(summary_rows, scenes, seeds)
    print(json.dumps({"out_dir": str(OUT), "means": means, "scenes": [scene.manifest_entry for scene in scenes]}, indent=2))


if __name__ == "__main__":
    main()
