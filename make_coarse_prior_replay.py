from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
from rasterio.enums import Resampling
from rasterio.windows import Window

import geo_public_bathy_benchmark as geo
import make_survey_grade_extension as extension
import make_survey_grade_pilot as pilot


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "coarse_prior_replay"
PIC = ROOT / "latex" / "pic"
FINE_NX = 240
FINE_NY = 300
DEFAULT_PRIOR_CELLS_M = (120.0, 300.0, 600.0)
DEFAULT_QUANTILES = (0.25, 0.55, 0.80)
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


def resample_array(values: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Small dependency-free bilinear resampler for regular grids."""
    out_y, out_x = shape
    old_y = np.linspace(0.0, 1.0, values.shape[0])
    old_x = np.linspace(0.0, 1.0, values.shape[1])
    new_y = np.linspace(0.0, 1.0, out_y)
    new_x = np.linspace(0.0, 1.0, out_x)

    x_resampled = np.empty((values.shape[0], out_x), dtype=float)
    for row in range(values.shape[0]):
        x_resampled[row, :] = np.interp(new_x, old_x, values[row, :])

    out = np.empty((out_y, out_x), dtype=float)
    for col in range(out_x):
        out[:, col] = np.interp(new_y, old_y, x_resampled[:, col])
    return out


def fine_scene_from_window(
    dataset: rasterio.io.DatasetReader,
    label: str,
    window: Window,
    metrics: dict[str, float],
) -> geo.TerrainScene:
    arr = dataset.read(
        1,
        window=window,
        out_shape=(FINE_NY, FINE_NX),
        masked=True,
        resampling=Resampling.bilinear,
    )
    depth = pilot.depth_from_masked(arr)
    depth, fill_info = geo._fill_depth_gaps(depth)
    bounds = rasterio.windows.bounds(window, dataset.transform)
    width_m = float(bounds[2] - bounds[0])
    height_m = float(bounds[3] - bounds[1])
    x = np.linspace(0.0, width_m, FINE_NX)
    y = np.linspace(0.0, height_m, FINE_NY)
    xx, yy = np.meshgrid(x, y)
    manifest = {
        "scene_id": f"usgs_southern_cascadia_30m_fine_{label}",
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
        "fine_grid_shape": [FINE_NY, FINE_NX],
        "fine_grid_resolution_m": round(max(width_m / max(FINE_NX - 1, 1), height_m / max(FINE_NY - 1, 1)), 3),
        "depth_range_m": [float(np.nanmin(depth)), float(np.nanmax(depth))],
        "terrain_class": f"coarse_prior_replay_{label}",
        "selection_metrics": metrics,
        "missing_value_handling": fill_info,
        "provider": "USGS",
        "extension_policy": "Coarse-prior/fine-grid replay; not mixed into run_5 primary GEBCO means.",
    }
    return geo.TerrainScene(
        scene_id=manifest["scene_id"],
        display_name=f"USGS Cascadia {label.title()} Fine Grid",
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


def prior_scene_from_truth(truth: geo.TerrainScene, target_cell_m: float) -> geo.TerrainScene:
    width_m = truth.width_m
    height_m = truth.height_m
    prior_nx = max(8, int(round(width_m / target_cell_m)) + 1)
    prior_ny = max(8, int(round(height_m / target_cell_m)) + 1)
    z_prior = resample_array(truth.z, (prior_ny, prior_nx))
    x = np.linspace(0.0, width_m, prior_nx)
    y = np.linspace(0.0, height_m, prior_ny)
    xx, yy = np.meshgrid(x, y)
    actual_cell_m = max(width_m / max(prior_nx - 1, 1), height_m / max(prior_ny - 1, 1))
    manifest = dict(truth.manifest_entry)
    manifest.update(
        {
            "scene_id": truth.scene_id.replace("_fine_", f"_prior_{int(target_cell_m)}m_"),
            "coarse_prior_target_cell_m": float(target_cell_m),
            "coarse_prior_actual_cell_m": float(actual_cell_m),
            "coarse_prior_shape": [int(prior_ny), int(prior_nx)],
            "coarse_prior_policy": "Plan on a coarsened public prior and replay the resulting line family on the fine public grid.",
        }
    )
    return geo.TerrainScene(
        scene_id=manifest["scene_id"],
        display_name=truth.display_name.replace("Fine Grid", f"{int(target_cell_m)} m Prior"),
        scene_group=truth.scene_group,
        terrain_class=truth.terrain_class,
        x=xx,
        y=yy,
        z=z_prior,
        source=truth.source,
        download_url=truth.download_url,
        raw_file=truth.raw_file,
        manifest_entry=manifest,
    )


def run_prior_layouts(prior: geo.TerrainScene, seeds: tuple[int, ...]) -> list[geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(prior)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(prior)
    results: list[geo.PlanResult] = [fixed, adaptive]
    for seed in seeds:
        results.append(geo.full_geometry_aware_hybrid_ga_plan(prior, adaptive_base, seed))
    return results


def row_from_replay(
    label: str,
    target_cell_m: float,
    actual_cell_m: float,
    prior: geo.TerrainScene,
    fine: geo.TerrainScene,
    planned: geo.PlanResult,
    replayed: geo.PlanResult,
) -> dict[str, Any]:
    return {
        "crop_label": label,
        "scene_id": fine.scene_id,
        "target_prior_cell_m": float(target_cell_m),
        "actual_prior_cell_m": float(actual_cell_m),
        "fine_grid_resolution_m": float(fine.manifest_entry["fine_grid_resolution_m"]),
        "prior_grid_ny": int(prior.z.shape[0]),
        "prior_grid_nx": int(prior.z.shape[1]),
        "method": planned.method,
        "method_label": METHOD_LABELS.get(planned.method, planned.method),
        "seed": int(planned.seed),
        "orientation_deg": float(planned.orientation_deg),
        "line_count": int(planned.line_count),
        "planned_path_length_km": float(planned.path_length_km),
        "replay_path_length_km": float(replayed.path_length_km),
        "planned_coverage_pct": float(planned.coverage_pct),
        "replay_coverage_pct": float(replayed.coverage_pct),
        "coverage_loss_pp": float(planned.coverage_pct - replayed.coverage_pct),
        "planned_excess_overlap_pct": float(planned.excess_overlap_pct),
        "replay_excess_overlap_pct": float(replayed.excess_overlap_pct),
        "overlap_increase_pp": float(replayed.excess_overlap_pct - planned.excess_overlap_pct),
        "planned_feasible": int(planned.feasible),
        "replay_feasible": int(replayed.feasible),
        "planning_time_s": float(planned.planning_time_s),
    }


def summarize(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        grouped[(str(row["crop_label"]), float(row["target_prior_cell_m"]), str(row["method"]))].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (label, target_cell_m, method), rows in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])):
        out: dict[str, Any] = {
            "crop_label": label,
            "target_prior_cell_m": target_cell_m,
            "actual_prior_cell_m": float(rows[0]["actual_prior_cell_m"]),
            "fine_grid_resolution_m": float(rows[0]["fine_grid_resolution_m"]),
            "prior_grid_ny": int(rows[0]["prior_grid_ny"]),
            "prior_grid_nx": int(rows[0]["prior_grid_nx"]),
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "n_runs": len(rows),
        }
        for key in (
            "orientation_deg",
            "line_count",
            "planned_path_length_km",
            "replay_path_length_km",
            "path_gain_vs_fixed_replay_pct",
            "planned_coverage_pct",
            "replay_coverage_pct",
            "coverage_loss_pp",
            "planned_excess_overlap_pct",
            "replay_excess_overlap_pct",
            "overlap_increase_pp",
            "planned_feasible",
            "replay_feasible",
            "planning_time_s",
        ):
            values = np.asarray([float(row[key]) for row in rows], dtype=float)
            out[f"{key}_mean"] = float(values.mean())
            out[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            out[f"{key}_min"] = float(values.min())
            out[f"{key}_max"] = float(values.max())
        summary_rows.append(out)
    return summary_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_figure(summary_rows: list[dict[str, Any]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 6.2,
            "axes.titlesize": 6.6,
            "axes.labelsize": 6.0,
            "xtick.labelsize": 5.2,
            "ytick.labelsize": 5.4,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    label_order = ["low", "medium", "high"]
    prior_order = [120.0, 300.0, 600.0]
    row_keys = [(label, cell) for label in label_order for cell in prior_order]
    method_order = list(METHODS)
    lookup = {
        (str(row["crop_label"]), float(row["target_prior_cell_m"]), str(row["method"])): row
        for row in summary_rows
    }

    matrices: list[tuple[str, str, np.ndarray, Any, str]] = []
    metrics = [
        ("Replay coverage (%)", "replay_coverage_pct_mean", "{:.1f}"),
        ("Coverage loss (pp)", "coverage_loss_pp_mean", "{:.2f}"),
        ("Replay excess overlap (%)", "replay_excess_overlap_pct_mean", "{:.2f}"),
        ("Replay feasible rate", "replay_feasible_mean", "{:.2f}"),
    ]
    for title, key, fmt in metrics:
        data = np.full((len(row_keys), len(method_order)), np.nan, dtype=float)
        for i, (label, cell) in enumerate(row_keys):
            for j, method in enumerate(method_order):
                data[i, j] = float(lookup[(label, cell, method)][key])
        if "coverage" in key and "loss" not in key:
            norm = TwoSlopeNorm(vmin=min(float(np.nanmin(data)), 96.0), vcenter=97.0, vmax=max(float(np.nanmax(data)), 100.0))
            cmap = LinearSegmentedColormap.from_list("coverage", ["#b75a48", "#f5efe6", "#d6eee9", "#157f76"])
        elif "loss" in key:
            norm = Normalize(vmin=0.0, vmax=max(0.25, float(np.nanmax(data))))
            cmap = LinearSegmentedColormap.from_list("loss", ["#f8fbfd", "#f4d6b8", "#d47a44", "#8f3f2e"])
        elif "overlap" in key:
            norm = Normalize(vmin=0.0, vmax=max(3.0, float(np.nanmax(data))))
            cmap = LinearSegmentedColormap.from_list("overlap", ["#f8fbfd", "#f5d3b6", "#d87b4a", "#843424"])
        else:
            norm = Normalize(vmin=0.0, vmax=1.0)
            cmap = LinearSegmentedColormap.from_list("feasible", ["#b75a48", "#f5efe6", "#d6eee9", "#157f76"])
        matrices.append((title, fmt, data, (cmap, norm), key))

    fig, axes = plt.subplots(1, 4, figsize=(7.24, 3.78), facecolor="white")
    row_labels = [f"{label.title()} {int(cell)} m" for label, cell in row_keys]
    col_labels = [METHOD_LABELS[method] for method in method_order]
    for ax_idx, (ax, (title, fmt, data, style, _)) in enumerate(zip(axes, matrices)):
        cmap, norm = style
        im = ax.imshow(data, cmap=cmap, norm=norm, aspect="auto")
        ax.set_title(title, fontweight="bold", pad=5.0, color="#1f2933")
        ax.set_xticks(np.arange(len(col_labels)))
        ax.set_xticklabels(col_labels)
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, pad=1.1)
        ax.set_yticks(np.arange(len(row_labels)))
        ax.set_yticklabels(row_labels if ax_idx == 0 else [])
        ax.tick_params(axis="y", length=0, pad=1.5)
        ax.set_xticks(np.arange(-0.5, len(col_labels), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(row_labels), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.85)
        ax.tick_params(which="minor", bottom=False, left=False)
        for boundary in (2.5, 5.5):
            ax.axhline(boundary, color="#34495e", linewidth=0.55, alpha=0.45)
        for spine in ax.spines.values():
            spine.set_color("#c8d4df")
            spine.set_linewidth(0.5)
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
                    fontsize=5.35,
                    color="white" if luminance < 0.45 else "#23313f",
                )

    fig.text(
        0.012,
        0.985,
        "Coarse-prior to fine-grid replay on USGS public bathymetry",
        ha="left",
        va="top",
        fontsize=7.3,
        fontweight="bold",
        color="#1f2933",
    )
    fig.text(
        0.012,
        0.956,
        "Line families are planned on 120/300/600 m priors and rescored on the fine public grid without re-optimization.",
        ha="left",
        va="top",
        fontsize=5.15,
        color="#667483",
    )
    fig.tight_layout(rect=(0.0, 0.02, 1.0, 0.91), w_pad=0.55)
    OUT.mkdir(parents=True, exist_ok=True)
    PIC.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "coarse_prior_replay_journal.png", bbox_inches="tight", facecolor="white", pad_inches=0.035)
    fig.savefig(PIC / "journal_coarse_prior_replay.png", bbox_inches="tight", facecolor="white", pad_inches=0.035)
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]], seeds: tuple[int, ...]) -> None:
    lines = [
        "# Coarse-prior to fine-grid replay\n\n",
        "This diagnostic plans fixed-pattern line families on coarsened USGS public bathymetry priors and replays the selected layouts on a finer public grid without re-optimization. It remains a public-grid numerical replay, not mission-log validation.\n\n",
        f"- Hybrid GA seeds: {seeds[0]}--{seeds[-1]}\n",
        f"- Fine-grid shape: {FINE_NY} x {FINE_NX}\n",
        "- Prior target cells: 120, 300, 600 m\n\n",
        "| Crop | Prior m | Method | Replay coverage % | Coverage loss pp | Replay Oex % | Replay feasible |\n",
        "|---|---:|---|---:|---:|---:|---:|\n",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['crop_label']} | {float(row['target_prior_cell_m']):.0f} | {row['method_label']} | "
            f"{float(row['replay_coverage_pct_mean']):.2f} | {float(row['coverage_loss_pp_mean']):.2f} | "
            f"{float(row['replay_excess_overlap_pct_mean']):.3f} | {float(row['replay_feasible_mean']):.2f} |\n"
        )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run coarse-prior/fine-grid public bathymetry replay.")
    parser.add_argument("--quantiles", default=",".join(str(q) for q in DEFAULT_QUANTILES))
    parser.add_argument("--prior-cells-m", default=",".join(str(v) for v in DEFAULT_PRIOR_CELLS_M))
    parser.add_argument("--seed-count", type=int, default=5)
    args = parser.parse_args()

    quantiles = tuple(float(item) for item in args.quantiles.split(",") if item.strip())
    prior_cells_m = tuple(float(item) for item in args.prior_cells_m.split(",") if item.strip())
    seeds = tuple(range(args.seed_count))

    OUT.mkdir(parents=True, exist_ok=True)
    pilot.ensure_extracted()
    raw_rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    with rasterio.open(pilot.RASTER_PATH) as dataset:
        candidates = extension.enumerate_candidate_windows(dataset)
        selected = extension.select_windows(candidates, list(quantiles))
        for label, window, metrics in selected:
            fine = fine_scene_from_window(dataset, label, window, dict(metrics))
            manifests.append(fine.manifest_entry)
            for target_cell_m in prior_cells_m:
                prior = prior_scene_from_truth(fine, target_cell_m)
                planned_results = run_prior_layouts(prior, seeds)
                combo_rows: list[dict[str, Any]] = []
                for planned in planned_results:
                    replayed = geo.evaluate_plan(
                        fine,
                        planned.method,
                        planned.seed,
                        planned.orientation_deg,
                        planned.line_positions,
                        planned.planning_time_s,
                    )
                    combo_rows.append(
                        row_from_replay(
                            label,
                            target_cell_m,
                            float(prior.manifest_entry["coarse_prior_actual_cell_m"]),
                            prior,
                            fine,
                            planned,
                            replayed,
                        )
                    )
                fixed_replay = next(row for row in combo_rows if row["method"] == "Fixed-Spacing")
                fixed_path = float(fixed_replay["replay_path_length_km"])
                for row in combo_rows:
                    row["path_gain_vs_fixed_replay_pct"] = (
                        0.0
                        if fixed_path <= 0.0
                        else (fixed_path - float(row["replay_path_length_km"])) / fixed_path * 100.0
                    )
                raw_rows.extend(combo_rows)

    summary_rows = summarize(raw_rows)
    write_csv(OUT / "coarse_prior_replay_raw.csv", raw_rows)
    write_csv(OUT / "coarse_prior_replay_summary.csv", summary_rows)
    (OUT / "coarse_prior_replay_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    (OUT / "public_scene_manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    make_figure(summary_rows)
    write_report(summary_rows, seeds)
    print(json.dumps({"out_dir": str(OUT), "rows": len(raw_rows), "summary_rows": len(summary_rows)}, indent=2))


if __name__ == "__main__":
    main()
