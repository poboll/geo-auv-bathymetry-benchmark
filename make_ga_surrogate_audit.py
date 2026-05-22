from __future__ import annotations

import argparse
import csv
import json
import time
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
OUT = ROOT / "ga_surrogate_audit"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

SCENE_LABELS = {
    "gebco_cascadia_margin_moderate": "GEBCO Cascadia",
    "gebco_monterey_canyon_complex": "GEBCO Monterey",
    "usgs_southern_cascadia_30m_high": "USGS High",
}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _safe_json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _score(path_km: float, coverage_pct: float, overlap_pct: float) -> float:
    return geo.plan_score(path_km, coverage_pct, overlap_pct)


def _spacing_penalty(positions: np.ndarray, nominal_spacing: float) -> float:
    if len(positions) <= 1:
        return 0.0
    return float(np.sum(np.maximum(0.0, 0.25 * nominal_spacing - np.diff(np.sort(positions))))) * 0.04


def _metrics_for_grid(
    scene: geo.TerrainScene,
    orientation_deg: float,
    positions: np.ndarray,
    *,
    stride: int,
    nominal_spacing: float,
) -> dict[str, float]:
    context = geo.make_context(scene, orientation_deg)
    v_grid = context.v_grid[::stride, ::stride]
    swath_width = context.swath_width[::stride, ::stride]
    positions = np.sort(positions)
    coverage_pct, overlap_pct = geo.coverage_and_overlap(v_grid, positions, swath_width)
    path_km = geo.plan_length_km(scene, positions, context.phi_rad)
    score = _score(path_km, coverage_pct, overlap_pct)
    penalty = _spacing_penalty(positions, nominal_spacing)
    return {
        "coverage_pct": float(coverage_pct),
        "excess_overlap_pct": float(overlap_pct),
        "path_length_km": float(path_km),
        "score": float(score),
        "spacing_penalty": float(penalty),
        "ga_fitness": float(score + penalty),
        "feasible_97_3": int(geo._is_feasible(coverage_pct, overlap_pct)),
    }


def _sample_candidates(
    scene: geo.TerrainScene,
    base: geo.LayoutCandidate,
    seed: int,
    n_candidates: int,
) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    base_positions = np.sort(base.line_positions)
    context = geo.make_context(scene, base.orientation_deg)
    if len(base_positions) <= 1:
        return [base_positions.copy()]
    nominal_spacing = float(np.median(np.diff(base_positions)))
    candidates = [base_positions.copy()]
    for idx in range(1, n_candidates):
        scale = 0.025 + 0.125 * ((idx - 1) / max(n_candidates - 2, 1))
        jitter = rng.normal(0.0, scale * nominal_spacing, size=len(base_positions))
        candidate = np.clip(base_positions + jitter, context.vmin, context.vmax)
        candidates.append(np.sort(candidate))
    return candidates


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_vals = values[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_vals[end] == sorted_vals[start]:
            end += 1
        avg_rank = 0.5 * (start + end - 1) + 1.0
        ranks[order[start:end]] = avg_rank
        start = end
    return ranks


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return float("nan")
    rx = _rankdata(x)
    ry = _rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def _kendall_tau(x: np.ndarray, y: np.ndarray) -> float:
    n = len(x)
    if n < 2:
        return float("nan")
    concordant = 0
    discordant = 0
    for i in range(n - 1):
        dx = x[i] - x[i + 1 :]
        dy = y[i] - y[i + 1 :]
        prod = dx * dy
        concordant += int(np.sum(prod > 0))
        discordant += int(np.sum(prod < 0))
    denom = n * (n - 1) / 2.0
    return float((concordant - discordant) / denom) if denom else float("nan")


def _audit_scene(scene: geo.TerrainScene, seeds: int, n_candidates: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    adaptive, base = geo.adaptive_spacing_plan(scene)
    base_positions = np.sort(base.line_positions)
    nominal_spacing = float(np.median(np.diff(base_positions))) if len(base_positions) > 1 else 1.0
    rows: list[dict[str, Any]] = []
    start = time.perf_counter()
    for seed in range(seeds):
        candidates = _sample_candidates(scene, base, seed, n_candidates)
        for candidate_idx, positions in enumerate(candidates):
            stride_metrics = _metrics_for_grid(
                scene,
                base.orientation_deg,
                positions,
                stride=geo.GA_EVAL_STRIDE,
                nominal_spacing=nominal_spacing,
            )
            full_metrics = _metrics_for_grid(
                scene,
                base.orientation_deg,
                positions,
                stride=1,
                nominal_spacing=nominal_spacing,
            )
            rows.append(
                {
                    "scene_id": scene.scene_id,
                    "scene_label": SCENE_LABELS.get(scene.scene_id, scene.display_name),
                    "seed": seed,
                    "candidate_idx": candidate_idx,
                    "orientation_deg": float(base.orientation_deg),
                    "line_count": int(len(base_positions)),
                    "stride_score": float(stride_metrics["score"]),
                    "full_score": float(full_metrics["score"]),
                    "stride_ga_fitness": float(stride_metrics["ga_fitness"]),
                    "full_ga_fitness": float(full_metrics["ga_fitness"]),
                    "stride_coverage_pct": float(stride_metrics["coverage_pct"]),
                    "full_coverage_pct": float(full_metrics["coverage_pct"]),
                    "stride_excess_overlap_pct": float(stride_metrics["excess_overlap_pct"]),
                    "full_excess_overlap_pct": float(full_metrics["excess_overlap_pct"]),
                    "full_feasible_97_3": int(full_metrics["feasible_97_3"]),
                    "is_base_layout": int(candidate_idx == 0),
                }
            )
    stride_fitness = np.asarray([row["stride_ga_fitness"] for row in rows], dtype=float)
    full_fitness = np.asarray([row["full_ga_fitness"] for row in rows], dtype=float)
    stride_score = np.asarray([row["stride_score"] for row in rows], dtype=float)
    full_score = np.asarray([row["full_score"] for row in rows], dtype=float)
    stride_order = np.argsort(stride_fitness)
    full_order = np.argsort(full_fitness)
    top_k = min(10, len(rows))
    top_stride = set(stride_order[:top_k].tolist())
    top_full = set(full_order[:top_k].tolist())
    best_stride_idx = int(stride_order[0])
    best_full_idx = int(full_order[0])
    best_stride_full_score = float(full_score[best_stride_idx])
    best_full_score = float(full_score[best_full_idx])
    summary = {
        "scene_id": scene.scene_id,
        "scene_label": SCENE_LABELS.get(scene.scene_id, scene.display_name),
        "n_candidates": len(rows),
        "seeds": seeds,
        "candidates_per_seed": n_candidates,
        "orientation_deg": float(base.orientation_deg),
        "line_count": int(len(base_positions)),
        "spearman_stride_full_fitness": _spearman(stride_fitness, full_fitness),
        "spearman_stride_full_score": _spearman(stride_score, full_score),
        "kendall_stride_full_fitness": _kendall_tau(stride_fitness, full_fitness),
        "top10_overlap_rate": float(len(top_stride & top_full) / top_k),
        "best_stride_candidate_full_score": best_stride_full_score,
        "best_full_candidate_full_score": best_full_score,
        "best_stride_full_score_regret_pct": float(
            100.0 * (best_stride_full_score - best_full_score) / max(abs(best_full_score), 1e-9)
        ),
        "best_stride_full_coverage_pct": float(rows[best_stride_idx]["full_coverage_pct"]),
        "best_stride_full_excess_overlap_pct": float(rows[best_stride_idx]["full_excess_overlap_pct"]),
        "best_stride_full_feasible_97_3": int(rows[best_stride_idx]["full_feasible_97_3"]),
        "runtime_s": float(time.perf_counter() - start),
    }
    return rows, summary


def _make_figure(summary_rows: list[dict[str, Any]]) -> None:
    jhs.apply_rc(base_font=8.3)
    labels = [row["scene_label"] for row in summary_rows]
    metrics = [
        (
            "spearman_stride_full_fitness",
            "Spearman fitness",
            mcolors.Normalize(vmin=0.0, vmax=1.0),
            jhs.PATH_GAIN_CMAP,
            "{:.2f}",
        ),
        (
            "kendall_stride_full_fitness",
            "Kendall tau",
            mcolors.Normalize(vmin=0.0, vmax=1.0),
            jhs.PATH_GAIN_CMAP,
            "{:.2f}",
        ),
        (
            "top10_overlap_rate",
            "Top-10 overlap",
            mcolors.Normalize(vmin=0.0, vmax=1.0),
            jhs.PATH_GAIN_CMAP,
            "{:.2f}",
        ),
        (
            "best_stride_full_score_regret_pct",
            "Best-stride regret (%)",
            mcolors.Normalize(vmin=0.0, vmax=1.0),
            jhs.OVERLAP_CMAP,
            "{:.3f}",
        ),
    ]
    fig = plt.figure(figsize=(7.35, 2.35), facecolor="white")
    grid = fig.add_gridspec(
        1,
        len(metrics) + 1,
        width_ratios=[1.12, 0.92, 0.92, 0.92, 1.03],
        left=0.045,
        right=0.985,
        top=0.76,
        bottom=0.21,
        wspace=0.18,
    )
    label_ax = fig.add_subplot(grid[0, 0])
    label_ax.set_xlim(0, 1)
    label_ax.set_ylim(len(labels) - 0.5, -0.5)
    label_ax.axis("off")
    for i, label in enumerate(labels):
        label_ax.text(0.98, i, label, ha="right", va="center", fontsize=7.1, color=jhs.TEXT)
    axes = [fig.add_subplot(grid[0, i + 1]) for i in range(len(metrics))]
    for ax, (key, title, norm, cmap, fmt) in zip(axes, metrics):
        data = np.asarray([[float(row[key])] for row in summary_rows], dtype=float)
        ax.imshow(data, cmap=cmap, norm=norm, aspect="auto")
        jhs.style_heatmap_axis(ax, title, [""], None, len(labels))
        ax.set_xticklabels([])
        jhs.annotate_cells(ax, data, cmap, norm, fmt, fontsize=6.7)
        for y in np.arange(0.5, len(labels), 1.0):
            ax.axhline(y, color="white", linewidth=0.75)
    fig.text(
        0.045,
        0.92,
        "GA surrogate audit: stride-3 fitness ranking vs. full-grid rescoring of local line-position perturbations",
        ha="left",
        va="center",
        fontsize=8.4,
        fontweight="semibold",
        color=jhs.TEXT,
    )
    fig.text(
        0.045,
        0.055,
        "Regret compares the full-grid score of the stride-selected candidate with the best full-grid candidate in the sampled local cloud.",
        ha="left",
        va="bottom",
        fontsize=6.1,
        color=jhs.MUTED,
    )
    out_path = OUT / "journal_ga_surrogate_audit.png"
    jhs.save_white_rgb(fig, out_path, dpi=430, pad_inches=0.02)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
        jhs.save_white_rgb(fig, pic_dir / "journal_ga_surrogate_audit.png", dpi=430, pad_inches=0.02)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit stride-3 GA surrogate ranking against full-grid rescoring."
    )
    parser.add_argument("--seeds", type=int, default=12, help="Number of local perturbation seeds per scene.")
    parser.add_argument(
        "--candidates-per-seed",
        type=int,
        default=12,
        help="Number of sampled local line-position perturbations per seed including the base layout.",
    )
    parser.add_argument(
        "--scenes",
        choices=("public", "all"),
        default="all",
        help="Use only the two GEBCO scenes or include the USGS high-complexity crop.",
    )
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    scenes = threshold.load_scenes()
    if args.scenes == "public":
        scenes = scenes[:2]
    all_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for scene in scenes:
        rows, summary = _audit_scene(scene, args.seeds, args.candidates_per_seed)
        all_rows.extend(rows)
        summary_rows.append(summary)
    _write_csv(OUT / "ga_surrogate_raw.csv", all_rows)
    _write_csv(OUT / "ga_surrogate_summary.csv", summary_rows)
    _safe_json_dump(
        OUT / "ga_surrogate_summary.json",
        {
            "scope": (
                "Supplemental GA surrogate audit. It samples local perturbations around the deterministic "
                "Adaptive Spacing layout, ranks them by the stride-3 GA fitness used during stochastic "
                "refinement, and then rescors the same candidates on the full evaluator grid."
            ),
            "ga_eval_stride": geo.GA_EVAL_STRIDE,
            "rows": all_rows,
            "summary_rows": summary_rows,
        },
    )
    _make_figure(summary_rows)
    print(f"Wrote GA surrogate audit with {len(all_rows)} raw candidates across {len(summary_rows)} scenes.")


if __name__ == "__main__":
    main()
