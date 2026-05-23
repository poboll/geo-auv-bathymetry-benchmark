from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize, TwoSlopeNorm
from PIL import Image

import geo_public_bathy_benchmark as geo
import journal_heatmap_style as jhs


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "uncertainty_replay"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

METHODS = [
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
]
LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adapt.",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
}
COLORS = {
    "Fixed-Spacing": "#6f7682",
    "Adaptive Spacing w/o GA": "#148f82",
    "Full Geometry-Aware Hybrid GA": "#c56335",
}
SCENARIOS = [
    {
        "scenario": "nominal",
        "cross_track_sigma_frac": 0.0,
        "correlated_line_sigma_frac": 0.0,
        "global_shift_sigma_frac": 0.0,
        "heading_sigma_deg": 0.0,
        "swath_scale_sigma": 0.0,
        "local_swath_sigma": 0.0,
        "terrain_swath_sigma": 0.0,
        "n_mc": 1,
    },
    {
        "scenario": "moderate_noise",
        "cross_track_sigma_frac": 0.05,
        "correlated_line_sigma_frac": 0.03,
        "global_shift_sigma_frac": 0.02,
        "heading_sigma_deg": 0.50,
        "swath_scale_sigma": 0.03,
        "local_swath_sigma": 0.02,
        "terrain_swath_sigma": 0.015,
        "n_mc": 300,
    },
    {
        "scenario": "strong_noise",
        "cross_track_sigma_frac": 0.10,
        "correlated_line_sigma_frac": 0.07,
        "global_shift_sigma_frac": 0.04,
        "heading_sigma_deg": 1.00,
        "swath_scale_sigma": 0.06,
        "local_swath_sigma": 0.04,
        "terrain_swath_sigma": 0.035,
        "n_mc": 300,
    },
]


def low_frequency_noise(shape: tuple[int, int], rng: np.random.Generator, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return np.zeros(shape, dtype=float)
    coarse_h = min(16, max(4, shape[0] // 10))
    coarse_w = min(16, max(4, shape[1] // 10))
    coarse = rng.normal(0.0, sigma, size=(coarse_h, coarse_w)).astype("float32")
    arr = ((coarse - coarse.min()) / max(float(coarse.max() - coarse.min()), 1e-9) * 255.0).astype("uint8")
    im = Image.fromarray(arr, mode="L").resize((shape[1], shape[0]), resample=Image.Resampling.BICUBIC)
    field = np.asarray(im, dtype=float) / 255.0
    field = (field - float(field.mean())) / max(float(field.std()), 1e-9)
    return field * sigma


def low_frequency_vector(n: int, rng: np.random.Generator, sigma: float) -> np.ndarray:
    """Generate a smooth cross-track drift sequence across adjacent survey lines."""
    if n <= 0 or sigma <= 0:
        return np.zeros(n, dtype=float)
    if n == 1:
        return rng.normal(0.0, sigma, size=1)
    coarse_n = min(10, max(3, n // 3))
    coarse_x = np.linspace(0.0, 1.0, coarse_n)
    fine_x = np.linspace(0.0, 1.0, n)
    coarse = rng.normal(0.0, 1.0, size=coarse_n)
    values = np.interp(fine_x, coarse_x, coarse)
    values = values - float(np.mean(values))
    values = values / max(float(np.std(values)), 1e-9)
    return values * sigma


def terrain_difficulty_weight(scene: geo.TerrainScene) -> np.ndarray:
    """Weight execution-footprint shrinkage toward deep or steep cells."""
    dy = float(np.abs(scene.y[1, 0] - scene.y[0, 0])) if scene.y.shape[0] > 1 else 1.0
    dx = float(np.abs(scene.x[0, 1] - scene.x[0, 0])) if scene.x.shape[1] > 1 else 1.0
    gy, gx = np.gradient(scene.z, dy, dx)
    slope = np.hypot(gx, gy)
    slope_ref = max(float(np.nanpercentile(slope, 95)), 1e-9)
    slope_w = np.clip(slope / slope_ref, 0.0, 1.0)
    depth_low = float(np.nanpercentile(scene.z, 5))
    depth_high = float(np.nanpercentile(scene.z, 95))
    depth_w = np.clip((scene.z - depth_low) / max(depth_high - depth_low, 1e-9), 0.0, 1.0)
    return np.clip(0.55 * slope_w + 0.45 * depth_w, 0.0, 1.0)


def representative_layouts(scene: geo.TerrainScene) -> dict[str, geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed=0)
    return {
        "Fixed-Spacing": fixed,
        "Adaptive Spacing w/o GA": adaptive,
        "Full Geometry-Aware Hybrid GA": hybrid,
    }


def evaluate_noisy(
    scene: geo.TerrainScene,
    plan: geo.PlanResult,
    scenario: dict[str, float | int | str],
    rng: np.random.Generator,
) -> tuple[float, float, int, float, float, float]:
    positions = np.asarray(plan.line_positions, dtype=float)
    spacing_ref = float(np.median(np.diff(positions))) if len(positions) > 1 else max(scene.width_m, scene.height_m)
    heading_error = float(rng.normal(0.0, float(scenario["heading_sigma_deg"])))
    context = geo.make_context(scene, plan.orientation_deg + heading_error)

    shifted = positions.copy()
    if len(shifted):
        shifted = shifted + rng.normal(0.0, float(scenario["global_shift_sigma_frac"]) * spacing_ref)
        shifted = shifted + low_frequency_vector(
            len(shifted),
            rng,
            float(scenario["correlated_line_sigma_frac"]) * spacing_ref,
        )
        shifted = shifted + rng.normal(0.0, float(scenario["cross_track_sigma_frac"]) * spacing_ref, size=len(shifted))
        shifted = np.sort(np.clip(shifted, context.vmin, context.vmax))

    global_scale = 1.0 + float(rng.normal(0.0, float(scenario["swath_scale_sigma"])))
    local_scale = 1.0 + low_frequency_noise(context.swath_width.shape, rng, float(scenario["local_swath_sigma"]))
    terrain_sigma = float(scenario["terrain_swath_sigma"])
    terrain_shrink = 1.0 - abs(float(rng.normal(0.0, terrain_sigma))) * terrain_difficulty_weight(scene)
    scale = np.clip(global_scale * local_scale * terrain_shrink, 0.72, 1.25)
    coverage, overlap = geo.coverage_and_overlap(context.v_grid, shifted, context.swath_width * scale)
    feasible = int(coverage >= geo.TARGET_COVERAGE_PCT and overlap <= geo.EXCESS_OVERLAP_FEASIBLE_PCT)
    return coverage, overlap, feasible, heading_error, float(global_scale), spacing_ref


def summarize(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=0)),
        "min": float(np.min(values)),
        "p05": float(np.percentile(values, 5)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "max": float(np.max(values)),
    }


def run_replay() -> tuple[list[dict[str, float | str | int]], list[dict[str, float | str | int]]]:
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    raw_rows: list[dict[str, float | str | int]] = []
    summary_rows: list[dict[str, float | str | int]] = []

    for scene in scenes:
        layouts = representative_layouts(scene)
        for method, plan in layouts.items():
            for scenario in SCENARIOS:
                # Seed by scene/scenario, not method, so method comparisons use
                # common random numbers rather than sequential RNG slices.
                rng = np.random.default_rng(
                    20260429 + sum(ord(ch) for ch in scene.scene_id + str(scenario["scenario"]))
                )
                coverage_vals: list[float] = []
                overlap_vals: list[float] = []
                feasible_vals: list[int] = []
                n_mc = int(scenario["n_mc"])
                for trial in range(n_mc):
                    coverage, overlap, feasible, heading_error, swath_scale, spacing_ref = evaluate_noisy(
                        scene, plan, scenario, rng
                    )
                    coverage_vals.append(coverage)
                    overlap_vals.append(overlap)
                    feasible_vals.append(feasible)
                    raw_rows.append(
                        {
                            "scene_id": scene.scene_id,
                            "scene_name": scene.display_name,
                            "method": method,
                            "scenario": str(scenario["scenario"]),
                            "trial": trial,
                            "coverage_pct": coverage,
                            "excess_overlap_pct": overlap,
                            "feasible": feasible,
                            "orientation_deg_nominal": plan.orientation_deg,
                            "heading_error_deg": heading_error,
                            "swath_global_scale": swath_scale,
                            "line_count": plan.line_count,
                            "spacing_ref_m": spacing_ref,
                        }
                    )
                cov = summarize(np.asarray(coverage_vals, dtype=float))
                ov = summarize(np.asarray(overlap_vals, dtype=float))
                summary_rows.append(
                    {
                        "scene_id": scene.scene_id,
                        "scene_name": scene.display_name,
                        "method": method,
                        "scenario": str(scenario["scenario"]),
                        "n_mc": n_mc,
                        "coverage_pct_mean": cov["mean"],
                        "coverage_pct_std": cov["std"],
                        "coverage_pct_min": cov["min"],
                        "coverage_pct_p05": cov["p05"],
                        "coverage_pct_p50": cov["p50"],
                        "coverage_pct_p95": cov["p95"],
                        "coverage_pct_max": cov["max"],
                        "excess_overlap_pct_mean": ov["mean"],
                        "excess_overlap_pct_std": ov["std"],
                        "excess_overlap_pct_min": ov["min"],
                        "excess_overlap_pct_p05": ov["p05"],
                        "excess_overlap_pct_p50": ov["p50"],
                        "excess_overlap_pct_p95": ov["p95"],
                        "excess_overlap_pct_max": ov["max"],
                        "feasible_rate": float(np.mean(feasible_vals)),
                        "cross_track_sigma_frac": float(scenario["cross_track_sigma_frac"]),
                        "global_shift_sigma_frac": float(scenario["global_shift_sigma_frac"]),
                        "correlated_line_sigma_frac": float(scenario["correlated_line_sigma_frac"]),
                        "heading_sigma_deg": float(scenario["heading_sigma_deg"]),
                        "swath_scale_sigma": float(scenario["swath_scale_sigma"]),
                        "local_swath_sigma": float(scenario["local_swath_sigma"]),
                        "terrain_swath_sigma": float(scenario["terrain_swath_sigma"]),
                    }
                )
    return raw_rows, summary_rows


def write_csv(path: Path, rows: list[dict[str, float | str | int]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_figure(summary_rows: list[dict[str, float | str | int]]) -> None:
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    public = [row for row in summary_rows if row["scenario"] in {"moderate_noise", "strong_noise"}]
    scene_order = [
        "gebco_cascadia_margin_moderate",
        "gebco_monterey_canyon_complex",
    ]
    scenario_order = ["moderate_noise", "strong_noise"]
    scene_names = {str(row["scene_id"]): str(row["scene_name"]) for row in public}
    scene_short_labels = {
        "gebco_cascadia_margin_moderate": "Casc.",
        "gebco_monterey_canyon_complex": "Mont.",
    }
    scenario_short_labels = {
        "moderate_noise": "Mod.",
        "strong_noise": "Strong",
    }
    row_labels: list[str] = []
    for scene_id in scene_order:
        for scenario in scenario_order:
            row_labels.append(f"{scene_short_labels.get(scene_id, scene_names[scene_id])} {scenario_short_labels.get(scenario, scenario)}")

    jhs.apply_rc(base_font=8.10)
    fig = plt.figure(figsize=(7.25, 3.66), facecolor=jhs.BG)
    grid = fig.add_gridspec(2, 2, wspace=0.08, hspace=0.20)

    lookup = {(row["scene_id"], row["scenario"], row["method"]): row for row in public}
    def matrix(metric: str) -> np.ndarray:
        rows: list[list[float]] = []
        for scene_id in scene_order:
            for scenario in scenario_order:
                rows.append([float(lookup[(scene_id, scenario, method)][metric]) for method in METHODS])
        return np.asarray(rows, dtype=float)

    feasible = matrix("feasible_rate")
    mean_coverage = matrix("coverage_pct_mean")
    coverage_margin_p05 = matrix("coverage_pct_p05") - geo.TARGET_COVERAGE_PCT
    overlap_p95 = matrix("excess_overlap_pct_p95")

    panels = [
        (
            "(a) Feasible rate",
            feasible,
            jhs.COVERAGE_CMAP,
            Normalize(vmin=0.0, vmax=1.0),
            "{:.2f}",
            lambda value: value < 1.0,
        ),
        (
            "(b) Mean coverage (%)",
            mean_coverage,
            jhs.COVERAGE_CMAP,
            Normalize(vmin=min(float(np.min(mean_coverage)), 94.0), vmax=100.0),
            "{:.2f}",
            lambda value: value < geo.TARGET_COVERAGE_PCT,
        ),
        (
            "(c) P05 coverage margin (pp)",
            coverage_margin_p05,
            jhs.COVERAGE_CMAP,
            TwoSlopeNorm(vmin=min(float(np.min(coverage_margin_p05)), -3.0), vcenter=0.0, vmax=max(float(np.max(coverage_margin_p05)), 3.0)),
            "{:+.2f}",
            lambda value: value < 0.0,
        ),
        (
            "(d) P95 excess-overlap tail (%)",
            overlap_p95,
            jhs.OVERLAP_CMAP,
            Normalize(vmin=0.0, vmax=max(float(np.max(overlap_p95)), geo.EXCESS_OVERLAP_FEASIBLE_PCT)),
            "{:.2f}",
            lambda value: value > geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        ),
    ]

    col_labels = [LABELS[method] for method in METHODS]
    for panel_idx, (title, data, cmap, norm, fmt, mark_bad) in enumerate(panels):
        ax = fig.add_subplot(grid[panel_idx // 2, panel_idx % 2])
        ax.imshow(data, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
        jhs.style_heatmap_axis(
            ax,
            title,
            col_labels,
            row_labels if panel_idx in (0, 2) else None,
            data.shape[0],
            group_every=len(scenario_order),
        )
        jhs.annotate_cells(ax, data, cmap, norm, fmt, mark_bad=mark_bad, fontsize=6.35)
    fig.subplots_adjust(left=0.125, right=0.996, top=0.920, bottom=0.075, wspace=0.08, hspace=0.20)
    jhs.save_white_rgb(fig, OUT / "uncertainty_replay.png", pad_inches=0.018)
    for pic_dir in PIC_DIRS:
        jhs.save_white_rgb(fig, pic_dir / "journal_uncertainty_replay.png", pad_inches=0.018)
    plt.close(fig)


def main() -> None:
    raw_rows, summary_rows = run_replay()
    write_csv(OUT / "uncertainty_replay_raw.csv", raw_rows)
    write_csv(OUT / "uncertainty_replay_summary.csv", summary_rows)
    (OUT / "uncertainty_replay_summary.json").write_text(
        json.dumps(summary_rows, indent=2), encoding="utf-8"
    )
    make_figure(summary_rows)
    print(f"Wrote {len(raw_rows)} Monte Carlo rows to {OUT}")
    print(f"Wrote uncertainty figure to {OUT / 'uncertainty_replay.png'} and manuscript figure directories")


if __name__ == "__main__":
    main()
