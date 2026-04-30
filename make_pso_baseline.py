from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import geo_public_bathy_benchmark as geo


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pso_baseline"
PIC = ROOT / "latex" / "pic"
METHODS = (
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
    "PSO Local Refinement",
)
METHOD_LABELS = {
    "Adaptive Spacing w/o GA": "Adaptive",
    "Full Geometry-Aware Hybrid GA": "Hybrid GA",
    "PSO Local Refinement": "PSO refine",
}
METHOD_COLORS = {
    "Adaptive Spacing w/o GA": "#168f83",
    "Full Geometry-Aware Hybrid GA": "#c56335",
    "PSO Local Refinement": "#496aa8",
}
SEEDS = tuple(range(10))
SWARM_SIZE = 10
ITERATIONS = 10


def pso_refine_layout(
    scene: geo.TerrainScene,
    orientation_deg: float,
    base_positions: np.ndarray,
    rng: np.random.Generator,
    swarm_size: int = SWARM_SIZE,
    iterations: int = ITERATIONS,
) -> np.ndarray:
    context = geo.make_context(scene, orientation_deg)
    if len(base_positions) < 2:
        return np.sort(base_positions.copy())
    nominal_spacing = float(np.median(np.diff(base_positions)))
    fitness_v_grid = context.v_grid[:: geo.GA_EVAL_STRIDE, :: geo.GA_EVAL_STRIDE]
    fitness_swath_width = context.swath_width[:: geo.GA_EVAL_STRIDE, :: geo.GA_EVAL_STRIDE]

    particles = [np.sort(base_positions.copy())]
    for _ in range(swarm_size - 1):
        jitter = rng.normal(0.0, 0.10 * nominal_spacing, size=len(base_positions))
        particles.append(np.sort(np.clip(base_positions + jitter, context.vmin, context.vmax)))
    positions = np.asarray(particles, dtype=float)
    velocities = rng.normal(0.0, 0.015 * nominal_spacing, size=positions.shape)

    def fitness(line_positions: np.ndarray) -> float:
        sorted_positions = np.sort(line_positions)
        coverage_pct, overlap_pct = geo.coverage_and_overlap(
            fitness_v_grid,
            sorted_positions,
            fitness_swath_width,
        )
        score = geo.plan_score(geo.plan_length_km(scene, sorted_positions, context.phi_rad), coverage_pct, overlap_pct)
        spacing_penalty = float(np.sum(np.maximum(0.0, 0.25 * nominal_spacing - np.diff(sorted_positions)))) * 0.04
        drift_penalty = float(np.mean(np.abs(sorted_positions - base_positions))) / max(nominal_spacing, 1e-9) * 0.02
        return score + spacing_penalty + drift_penalty

    personal_best = positions.copy()
    personal_scores = np.asarray([fitness(p) for p in personal_best], dtype=float)
    global_best = personal_best[int(np.argmin(personal_scores))].copy()
    global_score = float(np.min(personal_scores))

    for _ in range(iterations):
        r1 = rng.random(size=positions.shape)
        r2 = rng.random(size=positions.shape)
        velocities = 0.55 * velocities + 1.20 * r1 * (personal_best - positions) + 1.20 * r2 * (global_best - positions)
        velocities = np.clip(velocities, -0.18 * nominal_spacing, 0.18 * nominal_spacing)
        positions = np.sort(np.clip(positions + velocities, context.vmin, context.vmax), axis=1)
        scores = np.asarray([fitness(p) for p in positions], dtype=float)
        improved = scores < personal_scores
        personal_best[improved] = positions[improved]
        personal_scores[improved] = scores[improved]
        best_idx = int(np.argmin(personal_scores))
        if float(personal_scores[best_idx]) < global_score:
            global_score = float(personal_scores[best_idx])
            global_best = personal_best[best_idx].copy()
    return np.sort(global_best)


def pso_plan(scene: geo.TerrainScene, base_candidate: geo.LayoutCandidate, seed: int) -> geo.PlanResult:
    import time

    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    refined = pso_refine_layout(scene, base_candidate.orientation_deg, base_candidate.line_positions, rng)
    planning_time = time.perf_counter() - start
    return geo.evaluate_plan(
        scene,
        "PSO Local Refinement",
        seed,
        base_candidate.orientation_deg,
        refined,
        planning_time,
    )


def summarize(rows: list[geo.PlanResult]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[geo.PlanResult]] = defaultdict(list)
    for row in rows:
        grouped[(row.scene_id, row.method)].append(row)

    fixed_lookup: dict[str, float] = {}
    for scene_id, group_rows in defaultdict(list, {}).items():
        del scene_id, group_rows
    for row in rows:
        if row.method == "Fixed-Spacing":
            fixed_lookup[row.scene_id] = row.path_length_km

    out: list[dict[str, Any]] = []
    for (scene_id, method), group_rows in sorted(grouped.items()):
        if method == "Fixed-Spacing":
            continue
        values = {
            "path_length_km": np.asarray([row.path_length_km for row in group_rows], dtype=float),
            "coverage_pct": np.asarray([row.coverage_pct for row in group_rows], dtype=float),
            "excess_overlap_pct": np.asarray([row.excess_overlap_pct for row in group_rows], dtype=float),
            "planning_time_s": np.asarray([row.planning_time_s for row in group_rows], dtype=float),
            "line_count": np.asarray([row.line_count for row in group_rows], dtype=float),
            "feasible": np.asarray([1.0 if row.feasible else 0.0 for row in group_rows], dtype=float),
        }
        fixed_path = fixed_lookup.get(scene_id)
        path_gain = (
            np.zeros_like(values["path_length_km"])
            if not fixed_path
            else (fixed_path - values["path_length_km"]) / fixed_path * 100.0
        )
        values["path_gain_vs_fixed_pct"] = path_gain
        record: dict[str, Any] = {
            "scene_id": scene_id,
            "scene_name": group_rows[0].scene_name,
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "n_runs": len(group_rows),
        }
        for key, arr in values.items():
            record[f"{key}_mean"] = float(arr.mean())
            record[f"{key}_std"] = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
            record[f"{key}_min"] = float(arr.min())
            record[f"{key}_max"] = float(arr.max())
        out.append(record)
    return out


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
            "font.size": 7.0,
            "axes.titlesize": 7.4,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.0,
            "ytick.labelsize": 6.0,
            "legend.fontsize": 6.2,
            "axes.linewidth": 0.5,
            "savefig.dpi": 420,
        }
    )
    scenes = [
        ("gebco_cascadia_margin_moderate", "Cascadia"),
        ("gebco_monterey_canyon_complex", "Monterey"),
    ]
    metrics = [
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)"),
        ("coverage_pct_mean", "Predicted coverage (%)"),
        ("excess_overlap_pct_mean", "Excess overlap (%)"),
        ("planning_time_s_mean", "Planning time (s)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.24, 4.05), facecolor="white")
    axes_flat = axes.ravel()
    x = np.arange(len(scenes))
    width = 0.24
    for ax, (metric_key, title) in zip(axes_flat, metrics):
        for idx, method in enumerate(METHODS):
            vals = []
            err = []
            for scene_id, _ in scenes:
                match = [row for row in summary_rows if row["scene_id"] == scene_id and row["method"] == method]
                vals.append(float(match[0][metric_key]) if match else np.nan)
                std_key = metric_key.replace("_mean", "_std")
                err.append(float(match[0].get(std_key, 0.0)) if match else 0.0)
            ax.bar(
                x + (idx - 1) * width,
                vals,
                width=width,
                color=METHOD_COLORS[method],
                label=METHOD_LABELS[method],
                yerr=err if any(v > 0 for v in err) else None,
                error_kw={"elinewidth": 0.55, "capsize": 2.0, "capthick": 0.55},
            )
        ax.set_title(title, fontweight="bold", color="#1f2933")
        ax.set_xticks(x)
        ax.set_xticklabels([label for _, label in scenes])
        ax.grid(True, axis="y", color="#d8e0e7", linewidth=0.45, alpha=0.8)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color("#c8d4df")
            spine.set_linewidth(0.5)
    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.985))
    fig.text(
        0.012,
        0.018,
        "External optimizer sanity check on public GEBCO scenes; PSO uses the same 10x10 local-refinement budget as GA and starts from the adaptive-spacing base layout.",
        ha="left",
        va="bottom",
        fontsize=5.6,
        color="#667483",
    )
    fig.tight_layout(rect=(0.0, 0.065, 1.0, 0.90), h_pad=0.85, w_pad=0.65)
    OUT.mkdir(parents=True, exist_ok=True)
    PIC.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "pso_public_baseline.png", facecolor="white")
    fig.savefig(PIC / "journal_pso_baseline.png", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    all_results: list[geo.PlanResult] = []
    raw_rows: list[dict[str, Any]] = []
    for scene in scenes:
        fixed = geo.fixed_spacing_plan(scene)
        adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
        all_results.extend([fixed, adaptive])
        for seed in SEEDS:
            all_results.append(geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed))
            all_results.append(pso_plan(scene, adaptive_base, seed))

    for result in all_results:
        raw_rows.append(geo._result_to_row(result))
    summary_rows = summarize(all_results)
    write_csv(OUT / "pso_public_baseline_raw.csv", raw_rows)
    write_csv(OUT / "pso_public_baseline_summary.csv", summary_rows)
    (OUT / "pso_public_baseline_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    make_figure(summary_rows)
    print(json.dumps({"out_dir": str(OUT), "raw_rows": len(raw_rows), "summary_rows": len(summary_rows)}, indent=2))


if __name__ == "__main__":
    main()
