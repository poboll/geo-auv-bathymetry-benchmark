from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

import geo_public_bathy_benchmark as geo


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "uncertainty_replay"
PIC = ROOT / "latex" / "pic"

METHODS = [
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
]
LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adaptive",
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
        "global_shift_sigma_frac": 0.0,
        "heading_sigma_deg": 0.0,
        "swath_scale_sigma": 0.0,
        "local_swath_sigma": 0.0,
        "n_mc": 1,
    },
    {
        "scenario": "moderate_noise",
        "cross_track_sigma_frac": 0.05,
        "global_shift_sigma_frac": 0.02,
        "heading_sigma_deg": 0.50,
        "swath_scale_sigma": 0.03,
        "local_swath_sigma": 0.02,
        "n_mc": 300,
    },
    {
        "scenario": "strong_noise",
        "cross_track_sigma_frac": 0.10,
        "global_shift_sigma_frac": 0.04,
        "heading_sigma_deg": 1.00,
        "swath_scale_sigma": 0.06,
        "local_swath_sigma": 0.04,
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
        shifted = shifted + rng.normal(0.0, float(scenario["cross_track_sigma_frac"]) * spacing_ref, size=len(shifted))
        shifted = np.sort(np.clip(shifted, context.vmin, context.vmax))

    global_scale = 1.0 + float(rng.normal(0.0, float(scenario["swath_scale_sigma"])))
    local_scale = 1.0 + low_frequency_noise(context.swath_width.shape, rng, float(scenario["local_swath_sigma"]))
    scale = np.clip(global_scale * local_scale, 0.75, 1.25)
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
    rng = np.random.default_rng(20260429)
    scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    raw_rows: list[dict[str, float | str | int]] = []
    summary_rows: list[dict[str, float | str | int]] = []

    for scene in scenes:
        layouts = representative_layouts(scene)
        for method, plan in layouts.items():
            for scenario in SCENARIOS:
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
                        "heading_sigma_deg": float(scenario["heading_sigma_deg"]),
                        "swath_scale_sigma": float(scenario["swath_scale_sigma"]),
                        "local_swath_sigma": float(scenario["local_swath_sigma"]),
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
    PIC.mkdir(parents=True, exist_ok=True)
    public = [row for row in summary_rows if row["scenario"] in {"moderate_noise", "strong_noise"}]
    scene_order = [
        "gebco_cascadia_margin_moderate",
        "gebco_monterey_canyon_complex",
    ]
    scenario_order = ["moderate_noise", "strong_noise"]

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 6.8,
            "axes.titlesize": 7.0,
            "axes.labelsize": 6.5,
            "xtick.labelsize": 5.8,
            "ytick.labelsize": 5.8,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 3.75), facecolor="white", sharex="col")
    fig.text(
        0.035,
        0.985,
        "Execution-uncertainty replay on public GEBCO layouts",
        ha="left",
        va="top",
        fontsize=8.0,
        fontweight="bold",
        color="#202a33",
    )
    fig.text(
        0.035,
        0.952,
        "Monte Carlo perturbations add cross-track tracking error, heading error, and spatially correlated footprint-scale noise; metrics are recomputed from the public-grid evaluator.",
        ha="left",
        va="top",
        fontsize=4.8,
        color="#65717f",
    )

    lookup = {(row["scene_id"], row["scenario"], row["method"]): row for row in public}
    for row_idx, scene_id in enumerate(scene_order):
        scene_name = "Cascadia" if "cascadia" in scene_id else "Monterey"
        for col_idx, scenario in enumerate(scenario_order):
            ax = axes[row_idx, col_idx]
            x = np.arange(len(METHODS))
            means = [float(lookup[(scene_id, scenario, method)]["coverage_pct_mean"]) for method in METHODS]
            lows = [float(lookup[(scene_id, scenario, method)]["coverage_pct_p05"]) for method in METHODS]
            highs = [float(lookup[(scene_id, scenario, method)]["coverage_pct_p95"]) for method in METHODS]
            colors = [COLORS[method] for method in METHODS]
            ax.bar(x, means, color=colors, alpha=0.88, width=0.62)
            ax.errorbar(
                x,
                means,
                yerr=[np.asarray(means) - np.asarray(lows), np.asarray(highs) - np.asarray(means)],
                fmt="none",
                ecolor="#26313b",
                elinewidth=0.6,
                capsize=2.2,
                capthick=0.6,
            )
            ax.axhline(geo.TARGET_COVERAGE_PCT, color="#9aa8b5", linestyle=(0, (3, 2)), linewidth=0.65)
            ax.set_ylim(94.0, 100.6)
            ax.grid(axis="y", color="#dbe4ec", linewidth=0.4, alpha=0.8)
            ax.set_axisbelow(True)
            ax.set_title(
                f"({chr(97 + row_idx * 3 + col_idx)}) {scene_name}: {scenario.replace('_', ' ')}",
                loc="left",
                fontsize=5.8,
                fontweight="bold",
                color="#202a33",
                pad=3,
            )
            if col_idx == 0:
                ax.set_ylabel("Coverage (%)")
            ax.set_xticks(x)
            ax.set_xticklabels([LABELS[m] for m in METHODS], rotation=20, ha="right")
            for spine in ax.spines.values():
                spine.set_color("#b8c4cf")
                spine.set_linewidth(0.45)

        ax = axes[row_idx, 2]
        width = 0.34
        x = np.arange(len(scenario_order))
        for k, method in enumerate(["Fixed-Spacing", "Full Geometry-Aware Hybrid GA"]):
            p95 = [
                float(lookup[(scene_id, scenario, method)]["excess_overlap_pct_p95"])
                for scenario in scenario_order
            ]
            feasible = [
                float(lookup[(scene_id, scenario, method)]["feasible_rate"])
                for scenario in scenario_order
            ]
            bars = ax.bar(
                x + (k - 0.5) * width,
                p95,
                width,
                color=COLORS[method],
                alpha=0.88,
                label=LABELS[method],
            )
            for bar, fr in zip(bars, feasible):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.12,
                    f"F={fr:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=4.5,
                    color="#202a33",
                )
        ax.axhline(geo.EXCESS_OVERLAP_FEASIBLE_PCT, color="#9aa8b5", linestyle=(0, (3, 2)), linewidth=0.65)
        ax.grid(axis="y", color="#dbe4ec", linewidth=0.4, alpha=0.8)
        ax.set_axisbelow(True)
        ax.set_ylabel("P95 excess overlap (%)")
        ax.set_xticks(x)
        ax.set_xticklabels(["moderate", "strong"])
        ax.set_title(
            f"({chr(99 + row_idx * 3)}) {scene_name}: overlap tail",
            loc="left",
            fontsize=5.8,
            fontweight="bold",
            color="#202a33",
            pad=3,
        )
        for spine in ax.spines.values():
            spine.set_color("#b8c4cf")
            spine.set_linewidth(0.45)
        if row_idx == 0:
            leg = ax.legend(loc="upper right", frameon=True, fontsize=4.9, borderpad=0.25)
            leg.get_frame().set_facecolor("white")
            leg.get_frame().set_edgecolor("#d7e2eb")
            leg.get_frame().set_linewidth(0.32)

    fig.subplots_adjust(left=0.065, right=0.992, top=0.865, bottom=0.135, wspace=0.35, hspace=0.43)
    fig.savefig(PIC / "journal_uncertainty_replay.png", bbox_inches="tight", facecolor="white", pad_inches=0.025)
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
    print(f"Wrote uncertainty figure to {PIC / 'journal_uncertainty_replay.png'}")


if __name__ == "__main__":
    main()
