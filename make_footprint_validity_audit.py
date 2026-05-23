from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

import geo_public_bathy_benchmark as geo
import journal_heatmap_style as jhs
import make_threshold_local_failure_extension as threshold


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "footprint_validity_audit"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

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
METHOD_ORDER = {method: idx for idx, method in enumerate(METHODS)}
SCENE_LABELS = {
    "gebco_cascadia_margin_moderate": "GEBCO Cascadia",
    "gebco_monterey_canyon_complex": "GEBCO Monterey",
    "usgs_southern_cascadia_30m_high": "USGS High",
}


def _safe_json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _side_reaches(scene: geo.TerrainScene, phi_rad: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dx = float(scene.x[0, 1] - scene.x[0, 0])
    dy = float(scene.y[1, 0] - scene.y[0, 0])
    dz_dy, dz_dx = np.gradient(scene.z, dy, dx)
    cross_track_dx = -math.sin(phi_rad)
    cross_track_dy = math.cos(phi_rad)
    dz_dv = dz_dx * cross_track_dx + dz_dy * cross_track_dy
    slope_angle = np.arctan(dz_dv)
    half = math.radians(geo.BEAM_ANGLE_DEG / 2.0)
    denom_port = np.sin(np.pi / 2.0 + slope_angle - half)
    denom_star = np.sin(np.pi / 2.0 - slope_angle - half)
    denom_port = np.sign(denom_port) * np.maximum(np.abs(denom_port), 1e-3)
    denom_star = np.sign(denom_star) * np.maximum(np.abs(denom_star), 1e-3)
    port = scene.z * math.sin(half) * np.cos(slope_angle) / denom_port
    star = scene.z * math.sin(half) * np.cos(slope_angle) / denom_star
    port = np.nan_to_num(port, nan=0.0, posinf=0.0, neginf=0.0)
    star = np.nan_to_num(star, nan=0.0, posinf=0.0, neginf=0.0)
    port = np.clip(port, 15.0, 900.0)
    star = np.clip(star, 15.0, 900.0)
    total = np.clip(port + star, 30.0, 1800.0)
    return port, star, total


def side_specific_counts(
    scene: geo.TerrainScene,
    orientation_deg: float,
    line_positions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    context = geo.make_context(scene, orientation_deg)
    port, star, total = _side_reaches(scene, context.phi_rad)
    counts = np.zeros_like(context.v_grid, dtype=int)
    for line in np.sort(line_positions):
        delta = context.v_grid - line
        counts += ((delta >= 0.0) & (delta <= port)).astype(int)
        counts += ((delta < 0.0) & (-delta <= star)).astype(int)
    return counts, total, context.v_grid


def side_specific_excess_overlap(
    v_grid: np.ndarray,
    line_positions: np.ndarray,
    local_total_width: np.ndarray,
) -> np.ndarray:
    return geo.cellwise_excess_overlap(v_grid, np.sort(line_positions), local_total_width)


def representative_plans(scene: geo.TerrainScene) -> list[geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed=0)
    return [fixed, adaptive, hybrid]


def evaluate(scene: geo.TerrainScene, plan: geo.PlanResult) -> dict[str, Any]:
    context = geo.make_context(scene, plan.orientation_deg)
    proxy_counts = geo.coverage_counts(context.v_grid, plan.line_positions, context.swath_width)
    proxy_excess = geo.cellwise_excess_overlap(context.v_grid, plan.line_positions, context.swath_width)
    side_counts, side_total, v_grid = side_specific_counts(scene, plan.orientation_deg, plan.line_positions)
    side_excess = side_specific_excess_overlap(v_grid, plan.line_positions, side_total)
    proxy_coverage = float(np.mean(proxy_counts >= 1) * 100.0)
    side_coverage = float(np.mean(side_counts >= 1) * 100.0)
    proxy_overlap = float(np.mean(proxy_excess))
    side_overlap = float(np.mean(side_excess))
    disagreement = proxy_counts != side_counts
    proxy_gap_side_covered = (proxy_counts < 1) & (side_counts >= 1)
    proxy_covered_side_gap = (proxy_counts >= 1) & (side_counts < 1)
    return {
        "scene_id": scene.scene_id,
        "scene_label": SCENE_LABELS.get(scene.scene_id, scene.display_name),
        "method": plan.method,
        "method_label": METHOD_LABELS.get(plan.method, plan.method),
        "seed": int(plan.seed),
        "orientation_deg": float(plan.orientation_deg),
        "line_count": int(plan.line_count),
        "path_length_km": float(plan.path_length_km),
        "proxy_coverage_pct": proxy_coverage,
        "side_coverage_pct": side_coverage,
        "coverage_delta_side_minus_proxy_pp": side_coverage - proxy_coverage,
        "proxy_excess_overlap_pct": proxy_overlap,
        "side_excess_overlap_pct": side_overlap,
        "overlap_delta_side_minus_proxy_pp": side_overlap - proxy_overlap,
        "proxy_feasible_C97_O3": int(proxy_coverage >= 97.0 and proxy_overlap <= 3.0),
        "side_feasible_C97_O3": int(side_coverage >= 97.0 and side_overlap <= 3.0),
        "feasibility_changed": int((proxy_coverage >= 97.0 and proxy_overlap <= 3.0) != (side_coverage >= 97.0 and side_overlap <= 3.0)),
        "coverage_count_disagreement_pct": float(np.mean(disagreement) * 100.0),
        "proxy_gap_side_covered_pct": float(np.mean(proxy_gap_side_covered) * 100.0),
        "proxy_covered_side_gap_pct": float(np.mean(proxy_covered_side_gap) * 100.0),
        "side_cell_excess_overlap_p95": float(np.percentile(side_excess, 95)),
        "side_cell_excess_overlap_p99": float(np.percentile(side_excess, 99)),
        "proxy_cell_excess_overlap_p99": float(np.percentile(proxy_excess, 99)),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    arr_cov = np.asarray([abs(float(row["coverage_delta_side_minus_proxy_pp"])) for row in rows], dtype=float)
    arr_ov = np.asarray([abs(float(row["overlap_delta_side_minus_proxy_pp"])) for row in rows], dtype=float)
    arr_dis = np.asarray([float(row["coverage_count_disagreement_pct"]) for row in rows], dtype=float)
    changed = int(sum(int(row["feasibility_changed"]) for row in rows))
    return {
        "n_rows": len(rows),
        "max_abs_coverage_delta_pp": float(np.max(arr_cov)),
        "mean_abs_coverage_delta_pp": float(np.mean(arr_cov)),
        "max_abs_overlap_delta_pp": float(np.max(arr_ov)),
        "mean_abs_overlap_delta_pp": float(np.mean(arr_ov)),
        "max_count_disagreement_pct": float(np.max(arr_dis)),
        "mean_count_disagreement_pct": float(np.mean(arr_dis)),
        "feasibility_changes_C97_O3": changed,
        "policy": (
            "Side-specific footprint audit preserves port/starboard reach asymmetry but still ignores "
            "sound-speed refraction, attitude, beam-level quality, and raw MBES line-product processing."
        ),
    }


def make_figure(rows: list[dict[str, Any]]) -> None:
    jhs.apply_rc(base_font=8.75)
    plt.rcParams.update({"axes.unicode_minus": False})
    rows = sorted(rows, key=lambda r: (r["scene_id"], METHOD_ORDER.get(str(r["method"]), 99)))
    row_labels = [f"{row['scene_label']}  {row['method_label']}" for row in rows]
    delta_cmap = mcolors.LinearSegmentedColormap.from_list(
        "footprint_delta",
        ["#5f82a8", "#f7f7f2", "#c99c62"],
    )
    disagreement_cmap = mcolors.LinearSegmentedColormap.from_list(
        "footprint_disagreement",
        ["#f8fafc", "#d9e3eb", "#9aaec2", "#4d657f"],
    )
    risk_cmap = mcolors.LinearSegmentedColormap.from_list(
        "footprint_risk",
        ["#fffaf0", "#f6dfba", "#e2ad75", "#ba6658"],
    )
    metrics = [
        (
            "coverage_delta_side_minus_proxy_pp",
            "$\\Delta C$\nside-proxy",
            mcolors.TwoSlopeNorm(vmin=-1.5, vcenter=0.0, vmax=1.5),
            delta_cmap,
            "{:+.2f}",
        ),
        (
            "overlap_delta_side_minus_proxy_pp",
            "$\\Delta O$\nside-proxy",
            mcolors.TwoSlopeNorm(vmin=-2.5, vcenter=0.0, vmax=2.5),
            delta_cmap.reversed(),
            "{:+.2f}",
        ),
        (
            "coverage_count_disagreement_pct",
            "Count\nmismatch",
            mcolors.Normalize(vmin=0.0, vmax=max(1.0, max(float(row["coverage_count_disagreement_pct"]) for row in rows))),
            disagreement_cmap,
            "{:.2f}",
        ),
        (
            "side_cell_excess_overlap_p99",
            "Side p99\nexcess",
            mcolors.Normalize(vmin=0.0, vmax=max(5.0, max(float(row["side_cell_excess_overlap_p99"]) for row in rows))),
            risk_cmap,
            "{:.1f}",
        ),
    ]
    data = np.asarray([[float(row[key]) for key, *_ in metrics] for row in rows], dtype=float)
    rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=float)
    for col, (_, _, norm, cmap, _) in enumerate(metrics):
        rgba[:, col, :] = cmap(norm(data[:, col]))

    fig = plt.figure(figsize=(7.15, 3.60), facecolor="white")
    ax = fig.add_axes([0.270, 0.080, 0.715, 0.805])
    ax.imshow(rgba, aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(len(metrics)))
    ax.set_xticklabels([title for _, title, *_ in metrics], fontsize=8.15, color=jhs.TEXT)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, length=0, pad=4)
    for tick in ax.get_xticklabels():
        tick.set_fontweight("semibold")
        tick.set_linespacing(0.88)
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=7.95, color=jhs.TEXT)
    ax.tick_params(axis="y", length=0, pad=4)
    for i, tick in enumerate(ax.get_yticklabels()):
        tick.set_color(jhs.TEXT if i % 3 == 0 else jhs.MUTED)
    ax.set_xticks(np.arange(-0.5, len(metrics), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(row_labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.62)
    ax.tick_params(which="minor", bottom=False, left=False)
    for y in [2.5, 5.5]:
        ax.axhline(y, color="#e8edf2", linewidth=1.15)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_facecolor("white")

    for i in range(data.shape[0]):
        for j, (_, _, norm, cmap, fmt) in enumerate(metrics):
            value = float(data[i, j])
            ax.text(
                j,
                i,
                fmt.format(value),
                ha="center",
                va="center",
                fontsize=7.75,
                color=jhs.cell_text_color(cmap, norm, value),
                fontweight="normal",
            )
    out = OUT / "journal_footprint_validity_audit.png"
    jhs.save_white_rgb(fig, out, dpi=430, pad_inches=0.015)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
        jhs.save_white_rgb(fig, pic_dir / "journal_footprint_validity_audit.png", dpi=430, pad_inches=0.015)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for scene in threshold.load_scenes():
        for plan in representative_plans(scene):
            if plan.method in METHODS:
                rows.append(evaluate(scene, plan))
    summary = summarize(rows)
    _write_csv(OUT / "footprint_validity_raw.csv", rows)
    _safe_json_dump(OUT / "footprint_validity_summary.json", {"summary": summary, "rows": rows})
    make_figure(rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
