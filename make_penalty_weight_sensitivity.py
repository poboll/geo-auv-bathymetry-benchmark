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
OUT = ROOT / "sensitivity"
PIC = ROOT / "latex" / "pic"
COVERAGE_WEIGHTS = (40.0, 80.0, 160.0)
OVERLAP_WEIGHTS = (1.5, 3.0, 6.0)
SEEDS = tuple(range(5))
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


def patch_plan_score(coverage_weight: float, overlap_weight: float):
    original = geo.plan_score

    def weighted_score(path_length_km: float, coverage_pct: float, excess_overlap_pct: float) -> float:
        coverage_penalty = max(0.0, geo.TARGET_COVERAGE_PCT - coverage_pct) * coverage_weight
        overlap_penalty = excess_overlap_pct * overlap_weight
        return path_length_km + coverage_penalty + overlap_penalty

    geo.plan_score = weighted_score
    return original


def restore_plan_score(original) -> None:
    geo.plan_score = original


def result_row(
    result: geo.PlanResult,
    coverage_weight: float,
    overlap_weight: float,
    fixed_path: float | None,
) -> dict[str, float | int | str]:
    path_gain = 0.0 if fixed_path in (None, 0.0) else (fixed_path - result.path_length_km) / fixed_path * 100.0
    return {
        "coverage_penalty_weight": float(coverage_weight),
        "overlap_penalty_weight": float(overlap_weight),
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


def summarize(rows: list[dict[str, float | int | str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[float, float, str, str], list[dict[str, float | int | str]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                float(row["coverage_penalty_weight"]),
                float(row["overlap_penalty_weight"]),
                str(row["scene_id"]),
                str(row["method"]),
            )
        ].append(row)

    out: list[dict[str, Any]] = []
    for (coverage_weight, overlap_weight, scene_id, method), group_rows in sorted(grouped.items()):
        record: dict[str, Any] = {
            "coverage_penalty_weight": coverage_weight,
            "overlap_penalty_weight": overlap_weight,
            "scene_id": scene_id,
            "scene_name": str(group_rows[0]["scene_name"]),
            "method": method,
            "n_runs": len(group_rows),
        }
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
            values = np.asarray([float(row[key]) for row in group_rows], dtype=float)
            record[f"{key}_mean"] = float(values.mean())
            record[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            record[f"{key}_min"] = float(values.min())
            record[f"{key}_max"] = float(values.max())
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
            "axes.titlesize": 7.2,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.0,
            "ytick.labelsize": 6.0,
            "legend.fontsize": 6.1,
            "axes.linewidth": 0.5,
            "savefig.dpi": 420,
        }
    )
    scenes = [
        ("gebco_cascadia_margin_moderate", "Cascadia"),
        ("gebco_monterey_canyon_complex", "Monterey"),
    ]
    metrics = [
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)", (-0.05, 1.15)),
        ("coverage_pct_mean", "Predicted coverage (%)", (96.5, 100.4)),
        ("excess_overlap_pct_mean", "Excess overlap (%)", (-0.04, 0.95)),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7.25, 5.1), facecolor="white", sharex=True)
    x = np.arange(len(OVERLAP_WEIGHTS))
    width = 0.25
    for col, (scene_id, scene_label) in enumerate(scenes):
        for row_idx, (metric_key, ylabel, ylim) in enumerate(metrics):
            ax = axes[row_idx, col]
            ax.set_facecolor("white")
            ax.grid(True, axis="y", color="#d8e0e7", linewidth=0.42, alpha=0.78)
            ax.set_axisbelow(True)
            for spine in ax.spines.values():
                spine.set_color("#b8c4cf")
                spine.set_linewidth(0.48)
            if row_idx == 0:
                ax.set_title(scene_label, fontweight="bold", color="#202a33")
            for idx, method in enumerate(METHODS):
                vals = []
                errs = []
                for overlap_weight in OVERLAP_WEIGHTS:
                    matches = [
                        row
                        for row in summary_rows
                        if row["scene_id"] == scene_id
                        and row["method"] == method
                        and float(row["coverage_penalty_weight"]) == 80.0
                        and float(row["overlap_penalty_weight"]) == overlap_weight
                    ]
                    if matches:
                        vals.append(float(matches[0][metric_key]))
                        errs.append(float(matches[0].get(metric_key.replace("_mean", "_std"), 0.0)))
                    else:
                        vals.append(np.nan)
                        errs.append(0.0)
                ax.bar(
                    x + (idx - 1) * width,
                    vals,
                    width=width,
                    color=METHOD_COLORS[method],
                    label=METHOD_LABELS[method],
                    yerr=errs if any(v > 0 for v in errs) else None,
                    error_kw={"elinewidth": 0.55, "capsize": 2.0, "capthick": 0.55},
                )
            ax.set_ylim(*ylim)
            ax.set_xticks(x)
            ax.set_xticklabels([str(v) for v in OVERLAP_WEIGHTS])
            if col == 0:
                ax.set_ylabel(ylabel)
            if row_idx == 2:
                ax.set_xlabel("Overlap penalty weight")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.995))
    fig.text(
        0.5,
        0.045,
        "Bars show public-scene summaries at the default coverage penalty weight 80; CSV/JSON include the full 3x3 coverage/overlap weight grid.",
        ha="center",
        va="bottom",
        fontsize=6.1,
        color="#4c5965",
    )
    fig.subplots_adjust(top=0.90, bottom=0.13, left=0.08, right=0.985, hspace=0.38, wspace=0.18)
    fig.savefig(PIC / "journal_penalty_weight_sensitivity.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / "penalty_weight_sensitivity.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    PIC.mkdir(parents=True, exist_ok=True)
    public_scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    raw_rows: list[dict[str, float | int | str]] = []
    for coverage_weight in COVERAGE_WEIGHTS:
        for overlap_weight in OVERLAP_WEIGHTS:
            original_score = patch_plan_score(coverage_weight, overlap_weight)
            try:
                for scene in public_scenes:
                    fixed = geo.fixed_spacing_plan(scene)
                    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
                    fixed_path = fixed.path_length_km
                    raw_rows.append(result_row(fixed, coverage_weight, overlap_weight, fixed_path))
                    raw_rows.append(result_row(adaptive, coverage_weight, overlap_weight, fixed_path))
                    for seed in SEEDS:
                        hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed)
                        raw_rows.append(result_row(hybrid, coverage_weight, overlap_weight, fixed_path))
            finally:
                restore_plan_score(original_score)

    summary_rows = summarize(raw_rows)
    write_csv(OUT / "penalty_weight_sensitivity_raw.csv", raw_rows)
    write_csv(OUT / "penalty_weight_sensitivity_summary.csv", summary_rows)
    with (OUT / "penalty_weight_sensitivity.json").open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "scope": "Public GEBCO scenes only; objective-weight diagnostic, not deployment validation.",
                "coverage_penalty_weights": list(COVERAGE_WEIGHTS),
                "overlap_penalty_weights": list(OVERLAP_WEIGHTS),
                "hybrid_ga_seeds": list(SEEDS),
                "raw_rows": raw_rows,
                "summary_rows": summary_rows,
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    make_figure(summary_rows)
    print(f"Wrote {OUT / 'penalty_weight_sensitivity_summary.csv'}")
    print(f"Wrote {PIC / 'journal_penalty_weight_sensitivity.png'}")


if __name__ == "__main__":
    main()
