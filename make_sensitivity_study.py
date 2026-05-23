from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "sensitivity"
PIC = ROOT / "latex" / "pic"
GEO_PATH = ROOT / "geo_public_bathy_benchmark.py"

BEAM_ANGLES = (100.0, 110.0, 120.0, 130.0)
OVERLAP_TARGETS = (0.10, 0.15, 0.20)
RESOLUTION_STRIDES = (1, 2, 3)
DEPTH_BIAS_VALUES = (-150.0, 0.0, 150.0)
RELIEF_SCALE_VALUES = (0.7, 1.0, 1.3)
SENSITIVITY_SEEDS = tuple(range(20))
METHODS = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
)
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adaptive",
    "Full Geometry-Aware Hybrid GA": "Hybrid GA",
}
METHOD_COLORS = {
    "Fixed-Spacing": "#6f7682",
    "Adaptive Spacing w/o GA": "#168f83",
    "Full Geometry-Aware Hybrid GA": "#c56335",
}
METHOD_MARKERS = {
    "Fixed-Spacing": "o",
    "Adaptive Spacing w/o GA": "s",
    "Full Geometry-Aware Hybrid GA": "^",
}


def load_geo_module():
    spec = importlib.util.spec_from_file_location("geo_public_bathy_benchmark", GEO_PATH)
    geo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(geo)
    return geo


def patch_beam_angle(geo, angle: float):
    original = geo.directional_swath_width

    def directional_swath_width_for_angle(scene, phi_rad, beam_angle_deg=None):
        del beam_angle_deg
        return original(scene, phi_rad, beam_angle_deg=angle)

    geo.BEAM_ANGLE_DEG = angle
    geo.directional_swath_width = directional_swath_width_for_angle
    return original


def restore_beam_angle(geo, original):
    geo.BEAM_ANGLE_DEG = 120.0
    geo.directional_swath_width = original


def patch_overlap_target(geo, target: float):
    original_adaptive = geo.adaptive_line_positions
    original_target = geo.TARGET_OVERLAP

    def adaptive_line_positions_for_target(vmin, vmax, profile_v, profile_w, overlap_target=None):
        del overlap_target
        return original_adaptive(vmin, vmax, profile_v, profile_w, overlap_target=target)

    geo.TARGET_OVERLAP = target
    geo.adaptive_line_positions = adaptive_line_positions_for_target
    return original_target, original_adaptive


def restore_overlap_target(geo, original_target, original_adaptive):
    geo.TARGET_OVERLAP = original_target
    geo.adaptive_line_positions = original_adaptive


def result_row(result, beam_angle: float, fixed_path: float | None = None) -> dict[str, float | int | str]:
    path_gain = 0.0 if fixed_path in (None, 0.0) else (fixed_path - result.path_length_km) / fixed_path * 100.0
    return {
        "beam_angle_deg": float(beam_angle),
        "scene_id": result.scene_id,
        "scene_name": result.scene_name,
        "method": result.method,
        "seed": int(result.seed),
        "orientation_deg": float(result.orientation_deg),
        "line_count": int(result.line_count),
        "path_length_km": float(result.path_length_km),
        "path_gain_vs_fixed_pct": float(path_gain),
        "coverage_pct": float(result.coverage_pct),
        "excess_overlap_pct": float(result.excess_overlap_pct),
        "planning_time_s": float(result.planning_time_s),
        "feasible": int(result.feasible),
    }


def summarize_rows(raw_rows: list[dict[str, float | int | str]]) -> list[dict[str, float | int | str]]:
    grouped: dict[
        tuple[float | None, int | None, float | None, float | None, float, str, str],
        list[dict[str, float | int | str]],
    ] = defaultdict(list)
    for row in raw_rows:
        target_overlap = float(row["target_overlap"]) if "target_overlap" in row else None
        resolution_stride = int(row["resolution_stride"]) if "resolution_stride" in row else None
        planning_depth_bias = float(row["planning_depth_bias_m"]) if "planning_depth_bias_m" in row else None
        planning_relief_scale = float(row["planning_relief_scale"]) if "planning_relief_scale" in row else None
        grouped[
            (
                target_overlap,
                resolution_stride,
                planning_depth_bias,
                planning_relief_scale,
                float(row["beam_angle_deg"]),
                str(row["scene_id"]),
                str(row["method"]),
            )
        ].append(row)

    summary_rows = []
    for (
        target_overlap,
        resolution_stride,
        planning_depth_bias,
        planning_relief_scale,
        angle,
        scene_id,
        method,
    ), rows in sorted(grouped.items()):
        scene_name = str(rows[0]["scene_name"])
        out = {
            "beam_angle_deg": angle,
            "scene_id": scene_id,
            "scene_name": scene_name,
            "method": method,
            "n_runs": len(rows),
        }
        if target_overlap is not None:
            out["target_overlap"] = target_overlap
        if resolution_stride is not None:
            out["resolution_stride"] = resolution_stride
            out["grid_ny"] = int(rows[0]["grid_ny"])
            out["grid_nx"] = int(rows[0]["grid_nx"])
            out["effective_resolution_m"] = float(rows[0]["effective_resolution_m"])
        if planning_depth_bias is not None:
            out["planning_depth_bias_m"] = planning_depth_bias
        if planning_relief_scale is not None:
            out["planning_relief_scale"] = planning_relief_scale
        for key in (
            "orientation_deg",
            "line_count",
            "path_length_km",
            "path_gain_vs_fixed_pct",
            "coverage_pct",
            "excess_overlap_pct",
            "planning_time_s",
            "feasible",
        ):
            values = np.asarray([float(row[key]) for row in rows], dtype=float)
            out[f"{key}_mean"] = float(values.mean())
            out[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            out[f"{key}_min"] = float(values.min())
            out[f"{key}_max"] = float(values.max())
        summary_rows.append(out)
    return summary_rows


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_plot(summary_rows: list[dict[str, float | int | str]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 7.0,
            "axes.titlesize": 7.3,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.4,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    scene_order = [
        ("gebco_cascadia_margin_moderate", "Cascadia"),
        ("gebco_monterey_canyon_complex", "Monterey"),
    ]
    metrics = [
        ("coverage_pct_mean", "Predicted coverage (%)", (96.0, 100.5), 97.0, "Coverage target"),
        ("excess_overlap_pct_mean", "Excess overlap (%)", (-0.05, 1.25), None, None),
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)", (-0.05, 1.15), None, None),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7.25, 5.0), sharex=True)
    fig.patch.set_facecolor("white")

    for col, (scene_id, scene_label) in enumerate(scene_order):
        for row_idx, (metric, ylabel, ylim, ref, ref_label) in enumerate(metrics):
            ax = axes[row_idx, col]
            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_color("#b8c4cf")
                spine.set_linewidth(0.48)
            ax.grid(True, axis="both", color="#d8e0e7", linewidth=0.38, alpha=0.72)
            ax.set_axisbelow(True)
            if row_idx == 0:
                ax.set_title(scene_label, fontweight="bold", color="#202a33", pad=5)
            for method in METHODS:
                rows = [
                    row
                    for row in summary_rows
                    if row["scene_id"] == scene_id and row["method"] == method
                ]
                rows = sorted(rows, key=lambda row: float(row["beam_angle_deg"]))
                xs = [float(row["beam_angle_deg"]) for row in rows]
                ys = [float(row[metric]) for row in rows]
                ax.plot(
                    xs,
                    ys,
                    color=METHOD_COLORS[method],
                    marker=METHOD_MARKERS[method],
                    markersize=3.2,
                    linewidth=1.05,
                    label=METHOD_LABELS[method],
                )
            if ref is not None:
                ax.axhline(ref, color="#2b3440", linewidth=0.55, linestyle=(0, (4, 2)), alpha=0.75)
                if col == 1 and row_idx == 0:
                    ax.text(
                        130.0,
                        ref + 0.10,
                        ref_label,
                        ha="right",
                        va="bottom",
                        fontsize=5.7,
                        color="#2b3440",
                    )
            ax.set_ylim(*ylim)
            if col == 0:
                ax.set_ylabel(ylabel)
            else:
                ax.set_ylabel("")
            if row_idx == 2:
                ax.set_xlabel("MBES opening angle (deg)")
            ax.set_xticks(list(BEAM_ANGLES))
            ax.tick_params(colors="#202a33", width=0.45, length=2.4, pad=1.6)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
        handlelength=1.8,
    )
    fig.text(
        0.015,
        0.012,
        "Diagnostic reruns on public GEBCO scenes only; Hybrid GA uses seeds 0-4 at each beam angle.",
        ha="left",
        va="bottom",
        color="#65717f",
        fontsize=5.8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.965), h_pad=1.0, w_pad=0.95)
    PIC.mkdir(parents=True, exist_ok=True)
    fig.savefig(PIC / "journal_sensitivity_beam_angle.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_overlap_plot(summary_rows: list[dict[str, float | int | str]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 7.0,
            "axes.titlesize": 7.3,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.4,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    scene_order = [
        ("gebco_cascadia_margin_moderate", "Cascadia"),
        ("gebco_monterey_canyon_complex", "Monterey"),
    ]
    metrics = [
        ("coverage_pct_mean", "Predicted coverage (%)", (96.0, 100.5), 97.0, "Coverage target"),
        ("excess_overlap_pct_mean", "Excess overlap (%)", (-0.05, 1.25), None, None),
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)", (-0.20, 1.35), None, None),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7.25, 5.0), sharex=True)
    fig.patch.set_facecolor("white")

    for col, (scene_id, scene_label) in enumerate(scene_order):
        for row_idx, (metric, ylabel, ylim, ref, ref_label) in enumerate(metrics):
            ax = axes[row_idx, col]
            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_color("#b8c4cf")
                spine.set_linewidth(0.48)
            ax.grid(True, axis="both", color="#d8e0e7", linewidth=0.38, alpha=0.72)
            ax.set_axisbelow(True)
            if row_idx == 0:
                ax.set_title(scene_label, fontweight="bold", color="#202a33", pad=5)
            for method in METHODS:
                rows = [
                    row
                    for row in summary_rows
                    if row["scene_id"] == scene_id and row["method"] == method
                ]
                rows = sorted(rows, key=lambda row: float(row["target_overlap"]))
                xs = [100.0 * float(row["target_overlap"]) for row in rows]
                ys = [float(row[metric]) for row in rows]
                ax.plot(
                    xs,
                    ys,
                    color=METHOD_COLORS[method],
                    marker=METHOD_MARKERS[method],
                    markersize=3.2,
                    linewidth=1.05,
                    label=METHOD_LABELS[method],
                )
            if ref is not None:
                ax.axhline(ref, color="#2b3440", linewidth=0.55, linestyle=(0, (4, 2)), alpha=0.75)
                if col == 1 and row_idx == 0:
                    ax.text(
                        20.0,
                        ref + 0.10,
                        ref_label,
                        ha="right",
                        va="bottom",
                        fontsize=5.7,
                        color="#2b3440",
                    )
            ax.set_ylim(*ylim)
            if col == 0:
                ax.set_ylabel(ylabel)
            else:
                ax.set_ylabel("")
            if row_idx == 2:
                ax.set_xlabel("Target overlap margin (%)")
            ax.set_xticks([10, 15, 20])
            ax.tick_params(colors="#202a33", width=0.45, length=2.4, pad=1.6)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
        handlelength=1.8,
    )
    fig.text(
        0.015,
        0.012,
        "Diagnostic reruns on public GEBCO scenes only; Hybrid GA uses seeds 0-4 at each target-overlap setting.",
        ha="left",
        va="bottom",
        color="#65717f",
        fontsize=5.8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.965), h_pad=1.0, w_pad=0.95)
    PIC.mkdir(parents=True, exist_ok=True)
    fig.savefig(PIC / "journal_sensitivity_overlap_target.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def add_target_overlap(row: dict[str, float | int | str], target: float) -> dict[str, float | int | str]:
    updated = dict(row)
    updated["target_overlap"] = float(target)
    return updated


def downsample_scene(geo, scene, stride: int):
    if stride <= 1:
        return scene
    y_idx = np.unique(np.r_[np.arange(0, scene.y.shape[0], stride), scene.y.shape[0] - 1])
    x_idx = np.unique(np.r_[np.arange(0, scene.x.shape[1], stride), scene.x.shape[1] - 1])
    x = scene.x[np.ix_(y_idx, x_idx)]
    y = scene.y[np.ix_(y_idx, x_idx)]
    z = scene.z[np.ix_(y_idx, x_idx)]
    entry = dict(scene.manifest_entry)
    entry["resolution_sensitivity_stride"] = int(stride)
    entry["resolution_sensitivity_shape"] = [int(z.shape[0]), int(z.shape[1])]
    if z.shape[1] > 1 and z.shape[0] > 1:
        dx = float(np.nanmedian(np.diff(x[0, :])))
        dy = float(np.nanmedian(np.diff(y[:, 0])))
        entry["effective_resolution_m"] = round(max(abs(dx), abs(dy)), 3)
    return geo.TerrainScene(
        scene_id=scene.scene_id,
        display_name=scene.display_name,
        scene_group=scene.scene_group,
        terrain_class=scene.terrain_class,
        x=x,
        y=y,
        z=z,
        source=scene.source,
        download_url=scene.download_url,
        raw_file=scene.raw_file,
        manifest_entry=entry,
    )


def add_resolution_stride(row: dict[str, float | int | str], stride: int, scene) -> dict[str, float | int | str]:
    updated = dict(row)
    updated["resolution_stride"] = int(stride)
    updated["grid_ny"] = int(scene.z.shape[0])
    updated["grid_nx"] = int(scene.z.shape[1])
    if scene.z.shape[1] > 1 and scene.z.shape[0] > 1:
        dx = float(np.nanmedian(np.diff(scene.x[0, :])))
        dy = float(np.nanmedian(np.diff(scene.y[:, 0])))
        updated["effective_resolution_m"] = float(max(abs(dx), abs(dy)))
    else:
        updated["effective_resolution_m"] = 0.0
    return updated


def bias_scene(geo, scene, depth_bias_m: float):
    if abs(depth_bias_m) < 1e-12:
        return scene
    entry = dict(scene.manifest_entry)
    entry["planning_depth_bias_m"] = float(depth_bias_m)
    return geo.TerrainScene(
        scene_id=scene.scene_id,
        display_name=scene.display_name,
        scene_group=scene.scene_group,
        terrain_class=scene.terrain_class,
        x=scene.x,
        y=scene.y,
        z=scene.z + float(depth_bias_m),
        source=scene.source,
        download_url=scene.download_url,
        raw_file=scene.raw_file,
        manifest_entry=entry,
    )


def add_depth_bias(row: dict[str, float | int | str], depth_bias_m: float) -> dict[str, float | int | str]:
    updated = dict(row)
    updated["planning_depth_bias_m"] = float(depth_bias_m)
    return updated


def relief_scaled_scene(geo, scene, relief_scale: float):
    if abs(relief_scale - 1.0) < 1e-12:
        return scene
    z_mean = float(np.nanmean(scene.z))
    entry = dict(scene.manifest_entry)
    entry["planning_relief_scale"] = float(relief_scale)
    return geo.TerrainScene(
        scene_id=scene.scene_id,
        display_name=scene.display_name,
        scene_group=scene.scene_group,
        terrain_class=scene.terrain_class,
        x=scene.x,
        y=scene.y,
        z=z_mean + float(relief_scale) * (scene.z - z_mean),
        source=scene.source,
        download_url=scene.download_url,
        raw_file=scene.raw_file,
        manifest_entry=entry,
    )


def add_relief_scale(row: dict[str, float | int | str], relief_scale: float) -> dict[str, float | int | str]:
    updated = dict(row)
    updated["planning_relief_scale"] = float(relief_scale)
    return updated


def make_resolution_plot(summary_rows: list[dict[str, float | int | str]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 7.0,
            "axes.titlesize": 7.3,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.4,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    scene_order = [
        ("gebco_cascadia_margin_moderate", "Cascadia"),
        ("gebco_monterey_canyon_complex", "Monterey"),
    ]
    metrics = [
        ("coverage_pct_mean", "Predicted coverage (%)", (96.0, 100.5), 97.0, "Coverage target"),
        ("excess_overlap_pct_mean", "Excess overlap (%)", (-0.05, 1.7), None, None),
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)", (-0.10, 1.35), None, None),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7.25, 5.0), sharex=True)
    fig.patch.set_facecolor("white")

    for col, (scene_id, scene_label) in enumerate(scene_order):
        for row_idx, (metric, ylabel, ylim, ref, ref_label) in enumerate(metrics):
            ax = axes[row_idx, col]
            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_color("#b8c4cf")
                spine.set_linewidth(0.48)
            ax.grid(True, axis="both", color="#d8e0e7", linewidth=0.38, alpha=0.72)
            ax.set_axisbelow(True)
            if row_idx == 0:
                ax.set_title(scene_label, fontweight="bold", color="#202a33", pad=5)
            for method in METHODS:
                rows = [
                    row
                    for row in summary_rows
                    if row["scene_id"] == scene_id and row["method"] == method
                ]
                rows = sorted(rows, key=lambda row: int(float(row["resolution_stride"])))
                xs = [int(float(row["resolution_stride"])) for row in rows]
                ys = [float(row[metric]) for row in rows]
                ax.plot(
                    xs,
                    ys,
                    color=METHOD_COLORS[method],
                    marker=METHOD_MARKERS[method],
                    markersize=3.2,
                    linewidth=1.05,
                    label=METHOD_LABELS[method],
                )
            if ref is not None:
                ax.axhline(ref, color="#2b3440", linewidth=0.55, linestyle=(0, (4, 2)), alpha=0.75)
                if col == 1 and row_idx == 0:
                    ax.text(
                        3.0,
                        ref + 0.10,
                        ref_label,
                        ha="right",
                        va="bottom",
                        fontsize=5.7,
                        color="#2b3440",
                    )
            ax.set_ylim(*ylim)
            if col == 0:
                ax.set_ylabel(ylabel)
            else:
                ax.set_ylabel("")
            if row_idx == 2:
                ax.set_xlabel("Grid stride for diagnostic rerun")
            ax.set_xticks(list(RESOLUTION_STRIDES))
            ax.set_xticklabels(["native", "2x", "3x"])
            ax.tick_params(colors="#202a33", width=0.45, length=2.4, pad=1.6)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
        handlelength=1.8,
    )
    fig.text(
        0.015,
        0.012,
        "Diagnostic reruns on public GEBCO scenes only; downsampled grids expose resolution dependence of the planning evaluator.",
        ha="left",
        va="bottom",
        color="#65717f",
        fontsize=5.8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.965), h_pad=1.0, w_pad=0.95)
    PIC.mkdir(parents=True, exist_ok=True)
    fig.savefig(PIC / "journal_sensitivity_resolution.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_depth_bias_plot(summary_rows: list[dict[str, float | int | str]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 7.0,
            "axes.titlesize": 7.3,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.4,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    scene_order = [
        ("gebco_cascadia_margin_moderate", "Cascadia"),
        ("gebco_monterey_canyon_complex", "Monterey"),
    ]
    metrics = [
        ("coverage_pct_mean", "Predicted coverage (%)", (96.0, 100.5), 97.0, "Coverage target"),
        ("excess_overlap_pct_mean", "Excess overlap (%)", (-0.05, 1.7), None, None),
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)", (-0.10, 1.35), None, None),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7.25, 5.0), sharex=True)
    fig.patch.set_facecolor("white")

    for col, (scene_id, scene_label) in enumerate(scene_order):
        for row_idx, (metric, ylabel, ylim, ref, ref_label) in enumerate(metrics):
            ax = axes[row_idx, col]
            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_color("#b8c4cf")
                spine.set_linewidth(0.48)
            ax.grid(True, axis="both", color="#d8e0e7", linewidth=0.38, alpha=0.72)
            ax.set_axisbelow(True)
            if row_idx == 0:
                ax.set_title(scene_label, fontweight="bold", color="#202a33", pad=5)
            for method in METHODS:
                rows = [
                    row
                    for row in summary_rows
                    if row["scene_id"] == scene_id and row["method"] == method
                ]
                rows = sorted(rows, key=lambda row: float(row["planning_depth_bias_m"]))
                xs = [float(row["planning_depth_bias_m"]) for row in rows]
                ys = [float(row[metric]) for row in rows]
                ax.plot(
                    xs,
                    ys,
                    color=METHOD_COLORS[method],
                    marker=METHOD_MARKERS[method],
                    markersize=3.2,
                    linewidth=1.05,
                    label=METHOD_LABELS[method],
                )
            if ref is not None:
                ax.axhline(ref, color="#2b3440", linewidth=0.55, linestyle=(0, (4, 2)), alpha=0.75)
                if col == 1 and row_idx == 0:
                    ax.text(
                        150.0,
                        ref + 0.10,
                        ref_label,
                        ha="right",
                        va="bottom",
                        fontsize=5.7,
                        color="#2b3440",
                    )
            ax.set_ylim(*ylim)
            if col == 0:
                ax.set_ylabel(ylabel)
            else:
                ax.set_ylabel("")
            if row_idx == 2:
                ax.set_xlabel("Uniform prior-depth bias used for planning (m)")
            ax.set_xticks(list(DEPTH_BIAS_VALUES))
            ax.tick_params(colors="#202a33", width=0.45, length=2.4, pad=1.6)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
        handlelength=1.8,
    )
    fig.text(
        0.015,
        0.012,
        "Layouts are designed on depth-biased public priors and rescored on the native GEBCO grids; this is a simplified prior-map mismatch diagnostic.",
        ha="left",
        va="bottom",
        color="#65717f",
        fontsize=5.8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.965), h_pad=1.0, w_pad=0.95)
    PIC.mkdir(parents=True, exist_ok=True)
    fig.savefig(PIC / "journal_sensitivity_prior_depth_bias.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_relief_scale_plot(summary_rows: list[dict[str, float | int | str]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 7.0,
            "axes.titlesize": 7.3,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.4,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    scene_order = [
        ("gebco_cascadia_margin_moderate", "Cascadia"),
        ("gebco_monterey_canyon_complex", "Monterey"),
    ]
    metrics = [
        ("coverage_pct_mean", "Predicted coverage (%)", (96.0, 100.5), 97.0, "Coverage target"),
        ("excess_overlap_pct_mean", "Excess overlap (%)", (-0.05, 1.9), None, None),
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)", (-0.10, 1.5), None, None),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7.25, 5.0), sharex=True)
    fig.patch.set_facecolor("white")

    for col, (scene_id, scene_label) in enumerate(scene_order):
        for row_idx, (metric, ylabel, ylim, ref, ref_label) in enumerate(metrics):
            ax = axes[row_idx, col]
            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_color("#b8c4cf")
                spine.set_linewidth(0.48)
            ax.grid(True, axis="both", color="#d8e0e7", linewidth=0.38, alpha=0.72)
            ax.set_axisbelow(True)
            if row_idx == 0:
                ax.set_title(scene_label, fontweight="bold", color="#202a33", pad=5)
            for method in METHODS:
                rows = [
                    row
                    for row in summary_rows
                    if row["scene_id"] == scene_id and row["method"] == method
                ]
                rows = sorted(rows, key=lambda row: float(row["planning_relief_scale"]))
                xs = [float(row["planning_relief_scale"]) for row in rows]
                ys = [float(row[metric]) for row in rows]
                ax.plot(
                    xs,
                    ys,
                    color=METHOD_COLORS[method],
                    marker=METHOD_MARKERS[method],
                    markersize=3.2,
                    linewidth=1.05,
                    label=METHOD_LABELS[method],
                )
            if ref is not None:
                ax.axhline(ref, color="#2b3440", linewidth=0.55, linestyle=(0, (4, 2)), alpha=0.75)
                if col == 1 and row_idx == 0:
                    ax.text(
                        1.3,
                        ref + 0.10,
                        ref_label,
                        ha="right",
                        va="bottom",
                        fontsize=5.7,
                        color="#2b3440",
                    )
            ax.set_ylim(*ylim)
            if col == 0:
                ax.set_ylabel(ylabel)
            else:
                ax.set_ylabel("")
            if row_idx == 2:
                ax.set_xlabel("Relief scale used in planning prior")
            ax.set_xticks(list(RELIEF_SCALE_VALUES))
            ax.tick_params(colors="#202a33", width=0.45, length=2.4, pad=1.6)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
        handlelength=1.8,
    )
    fig.text(
        0.015,
        0.012,
        "Layouts are designed on relief-scaled public priors and rescored on the native GEBCO grids; this is a simplified prior-map mismatch diagnostic.",
        ha="left",
        va="bottom",
        color="#65717f",
        fontsize=5.8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.965), h_pad=1.0, w_pad=0.95)
    PIC.mkdir(parents=True, exist_ok=True)
    fig.savefig(PIC / "journal_sensitivity_prior_relief_scale.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    global SENSITIVITY_SEEDS
    parser = argparse.ArgumentParser(description="Run public GEBCO parameter-sensitivity diagnostics.")
    parser.add_argument(
        "--seed-count",
        type=int,
        default=len(SENSITIVITY_SEEDS),
        help="Number of Hybrid GA seeds to run at each sensitivity setting, starting at zero.",
    )
    args = parser.parse_args()
    if args.seed_count < 1:
        raise ValueError("--seed-count must be at least 1")
    SENSITIVITY_SEEDS = tuple(range(args.seed_count))

    OUT.mkdir(parents=True, exist_ok=True)
    geo = load_geo_module()
    public_scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    raw_rows: list[dict[str, float | int | str]] = []

    for angle in BEAM_ANGLES:
        original = patch_beam_angle(geo, angle)
        try:
            for scene in public_scenes:
                fixed = geo.fixed_spacing_plan(scene)
                adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
                fixed_path = fixed.path_length_km
                raw_rows.append(result_row(fixed, angle, fixed_path))
                raw_rows.append(result_row(adaptive, angle, fixed_path))
                for seed in SENSITIVITY_SEEDS:
                    hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed)
                    raw_rows.append(result_row(hybrid, angle, fixed_path))
        finally:
            restore_beam_angle(geo, original)

    summary_rows = summarize_rows(raw_rows)
    write_csv(OUT / "beam_angle_sensitivity_raw.csv", raw_rows)
    write_csv(OUT / "beam_angle_sensitivity_summary.csv", summary_rows)
    with (OUT / "beam_angle_sensitivity.json").open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "scope": "Public GEBCO scenes only; diagnostic planning-parameter sensitivity, not field validation.",
                "beam_angles_deg": list(BEAM_ANGLES),
                "hybrid_ga_seeds": list(SENSITIVITY_SEEDS),
                "raw_rows": raw_rows,
                "summary_rows": summary_rows,
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    make_plot(summary_rows)

    overlap_raw_rows: list[dict[str, float | int | str]] = []
    for target in OVERLAP_TARGETS:
        original_target, original_adaptive = patch_overlap_target(geo, target)
        try:
            for scene in public_scenes:
                fixed = geo.fixed_spacing_plan(scene)
                adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
                fixed_path = fixed.path_length_km
                overlap_raw_rows.append(add_target_overlap(result_row(fixed, 120.0, fixed_path), target))
                overlap_raw_rows.append(add_target_overlap(result_row(adaptive, 120.0, fixed_path), target))
                for seed in SENSITIVITY_SEEDS:
                    hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed)
                    overlap_raw_rows.append(add_target_overlap(result_row(hybrid, 120.0, fixed_path), target))
        finally:
            restore_overlap_target(geo, original_target, original_adaptive)

    overlap_summary_rows = summarize_rows(overlap_raw_rows)
    overlap_summary_rows = sorted(
        overlap_summary_rows,
        key=lambda row: (float(row["target_overlap"]), str(row["scene_id"]), str(row["method"])),
    )
    write_csv(OUT / "target_overlap_sensitivity_raw.csv", overlap_raw_rows)
    write_csv(OUT / "target_overlap_sensitivity_summary.csv", overlap_summary_rows)
    with (OUT / "target_overlap_sensitivity.json").open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "scope": "Public GEBCO scenes only; diagnostic design-margin sensitivity, not field validation.",
                "target_overlap_values": list(OVERLAP_TARGETS),
                "hybrid_ga_seeds": list(SENSITIVITY_SEEDS),
                "raw_rows": overlap_raw_rows,
                "summary_rows": overlap_summary_rows,
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    make_overlap_plot(overlap_summary_rows)

    resolution_raw_rows: list[dict[str, float | int | str]] = []
    for stride in RESOLUTION_STRIDES:
        for base_scene in public_scenes:
            scene = downsample_scene(geo, base_scene, stride)
            fixed = geo.fixed_spacing_plan(scene)
            adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
            fixed_path = fixed.path_length_km
            resolution_raw_rows.append(add_resolution_stride(result_row(fixed, 120.0, fixed_path), stride, scene))
            resolution_raw_rows.append(add_resolution_stride(result_row(adaptive, 120.0, fixed_path), stride, scene))
            for seed in SENSITIVITY_SEEDS:
                hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed)
                resolution_raw_rows.append(add_resolution_stride(result_row(hybrid, 120.0, fixed_path), stride, scene))

    resolution_summary_rows = summarize_rows(resolution_raw_rows)
    resolution_summary_rows = sorted(
        resolution_summary_rows,
        key=lambda row: (int(float(row["resolution_stride"])), str(row["scene_id"]), str(row["method"])),
    )
    write_csv(OUT / "resolution_sensitivity_raw.csv", resolution_raw_rows)
    write_csv(OUT / "resolution_sensitivity_summary.csv", resolution_summary_rows)
    with (OUT / "resolution_sensitivity.json").open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "scope": "Public GEBCO scenes only; diagnostic grid-resolution sensitivity, not field validation.",
                "resolution_strides": list(RESOLUTION_STRIDES),
                "hybrid_ga_seeds": list(SENSITIVITY_SEEDS),
                "raw_rows": resolution_raw_rows,
                "summary_rows": resolution_summary_rows,
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    make_resolution_plot(resolution_summary_rows)

    depth_bias_raw_rows: list[dict[str, float | int | str]] = []
    for depth_bias_m in DEPTH_BIAS_VALUES:
        for base_scene in public_scenes:
            planning_scene = bias_scene(geo, base_scene, depth_bias_m)
            fixed_plan = geo.fixed_spacing_plan(planning_scene)
            fixed_eval = geo.evaluate_plan(
                base_scene,
                "Fixed-Spacing",
                fixed_plan.seed,
                fixed_plan.orientation_deg,
                fixed_plan.line_positions,
                fixed_plan.planning_time_s,
            )
            fixed_path = fixed_eval.path_length_km
            depth_bias_raw_rows.append(add_depth_bias(result_row(fixed_eval, 120.0, fixed_path), depth_bias_m))

            adaptive_plan, adaptive_base = geo.adaptive_spacing_plan(planning_scene)
            adaptive_eval = geo.evaluate_plan(
                base_scene,
                "Adaptive Spacing w/o GA",
                adaptive_plan.seed,
                adaptive_plan.orientation_deg,
                adaptive_plan.line_positions,
                adaptive_plan.planning_time_s,
            )
            depth_bias_raw_rows.append(add_depth_bias(result_row(adaptive_eval, 120.0, fixed_path), depth_bias_m))

            for seed in SENSITIVITY_SEEDS:
                hybrid_plan = geo.full_geometry_aware_hybrid_ga_plan(planning_scene, adaptive_base, seed)
                hybrid_eval = geo.evaluate_plan(
                    base_scene,
                    "Full Geometry-Aware Hybrid GA",
                    hybrid_plan.seed,
                    hybrid_plan.orientation_deg,
                    hybrid_plan.line_positions,
                    hybrid_plan.planning_time_s,
                )
                depth_bias_raw_rows.append(add_depth_bias(result_row(hybrid_eval, 120.0, fixed_path), depth_bias_m))

    depth_bias_summary_rows = summarize_rows(depth_bias_raw_rows)
    depth_bias_summary_rows = sorted(
        depth_bias_summary_rows,
        key=lambda row: (float(row["planning_depth_bias_m"]), str(row["scene_id"]), str(row["method"])),
    )
    write_csv(OUT / "prior_depth_bias_sensitivity_raw.csv", depth_bias_raw_rows)
    write_csv(OUT / "prior_depth_bias_sensitivity_summary.csv", depth_bias_summary_rows)
    with (OUT / "prior_depth_bias_sensitivity.json").open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "scope": (
                    "Public GEBCO scenes only; layouts are planned on uniformly depth-biased priors and "
                    "evaluated on the native grids as a simplified prior-map mismatch diagnostic."
                ),
                "planning_depth_bias_m_values": list(DEPTH_BIAS_VALUES),
                "hybrid_ga_seeds": list(SENSITIVITY_SEEDS),
                "raw_rows": depth_bias_raw_rows,
                "summary_rows": depth_bias_summary_rows,
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    make_depth_bias_plot(depth_bias_summary_rows)

    relief_scale_raw_rows: list[dict[str, float | int | str]] = []
    for relief_scale in RELIEF_SCALE_VALUES:
        for base_scene in public_scenes:
            planning_scene = relief_scaled_scene(geo, base_scene, relief_scale)
            fixed_plan = geo.fixed_spacing_plan(planning_scene)
            fixed_eval = geo.evaluate_plan(
                base_scene,
                "Fixed-Spacing",
                fixed_plan.seed,
                fixed_plan.orientation_deg,
                fixed_plan.line_positions,
                fixed_plan.planning_time_s,
            )
            fixed_path = fixed_eval.path_length_km
            relief_scale_raw_rows.append(add_relief_scale(result_row(fixed_eval, 120.0, fixed_path), relief_scale))

            adaptive_plan, adaptive_base = geo.adaptive_spacing_plan(planning_scene)
            adaptive_eval = geo.evaluate_plan(
                base_scene,
                "Adaptive Spacing w/o GA",
                adaptive_plan.seed,
                adaptive_plan.orientation_deg,
                adaptive_plan.line_positions,
                adaptive_plan.planning_time_s,
            )
            relief_scale_raw_rows.append(add_relief_scale(result_row(adaptive_eval, 120.0, fixed_path), relief_scale))

            for seed in SENSITIVITY_SEEDS:
                hybrid_plan = geo.full_geometry_aware_hybrid_ga_plan(planning_scene, adaptive_base, seed)
                hybrid_eval = geo.evaluate_plan(
                    base_scene,
                    "Full Geometry-Aware Hybrid GA",
                    hybrid_plan.seed,
                    hybrid_plan.orientation_deg,
                    hybrid_plan.line_positions,
                    hybrid_plan.planning_time_s,
                )
                relief_scale_raw_rows.append(add_relief_scale(result_row(hybrid_eval, 120.0, fixed_path), relief_scale))

    relief_scale_summary_rows = summarize_rows(relief_scale_raw_rows)
    relief_scale_summary_rows = sorted(
        relief_scale_summary_rows,
        key=lambda row: (float(row["planning_relief_scale"]), str(row["scene_id"]), str(row["method"])),
    )
    write_csv(OUT / "prior_relief_scale_sensitivity_raw.csv", relief_scale_raw_rows)
    write_csv(OUT / "prior_relief_scale_sensitivity_summary.csv", relief_scale_summary_rows)
    with (OUT / "prior_relief_scale_sensitivity.json").open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "scope": (
                    "Public GEBCO scenes only; layouts are planned on relief-scaled priors and "
                    "evaluated on the native grids as a simplified prior-map mismatch diagnostic."
                ),
                "planning_relief_scale_values": list(RELIEF_SCALE_VALUES),
                "hybrid_ga_seeds": list(SENSITIVITY_SEEDS),
                "raw_rows": relief_scale_raw_rows,
                "summary_rows": relief_scale_summary_rows,
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    make_relief_scale_plot(relief_scale_summary_rows)
    try:
        from make_sensitivity_evidence_figures import main as make_evidence_figures

        make_evidence_figures()
    except Exception as exc:
        print(f"WARNING: could not render manuscript evidence-matrix sensitivity figures: {exc}")

    print(f"Wrote {OUT / 'beam_angle_sensitivity_summary.csv'}")
    print(f"Wrote {OUT / 'target_overlap_sensitivity_summary.csv'}")
    print(f"Wrote {OUT / 'resolution_sensitivity_summary.csv'}")
    print(f"Wrote {PIC / 'journal_sensitivity_beam_angle.png'}")
    print(f"Wrote {PIC / 'journal_sensitivity_overlap_target.png'}")
    print(f"Wrote {PIC / 'journal_sensitivity_resolution.png'}")


if __name__ == "__main__":
    main()
