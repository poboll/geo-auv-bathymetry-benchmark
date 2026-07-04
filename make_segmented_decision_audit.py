from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import rcParams
from PIL import Image


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "segmented_heading_extension" / "segmented_heading_raw.csv"
OUT_DIR = ROOT / "segmented_decision_audit"


ORDER = [
    "synthetic_complex",
    "gebco_monterey_canyon_complex",
    "gebco_mariana_trench_complex",
    "gebco_puerto_rico_trench_complex",
    "usgs_southern_cascadia_30m_high",
]


def f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "":
        return float("nan")
    return float(value)


def mean(values: list[float]) -> float:
    vals = [v for v in values if not math.isnan(v)]
    return sum(vals) / len(vals) if vals else float("nan")


def pct_delta(new: float, old: float) -> float:
    if old == 0 or math.isnan(new) or math.isnan(old):
        return float("nan")
    return (new - old) / old * 100.0


def load_rows() -> list[dict[str, str]]:
    with INPUT.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_scene: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_scene[row["scene_id"]].append(row)

    summaries: list[dict[str, object]] = []
    for scene_id in ORDER:
        scene_rows = by_scene[scene_id]
        single = [
            r for r in scene_rows if r["method"] == "Full Geometry-Aware Hybrid GA"
        ]
        fixed = [r for r in scene_rows if r["method"] == "Fixed-Spacing"]
        cp = [
            r
            for r in scene_rows
            if r["method"] == "Coverage-Preserving Segmented Hybrid"
        ]
        ta = [
            r
            for r in scene_rows
            if r["method"] == "Transition-Aware Segmented Hybrid"
        ]
        if not single or not ta:
            continue

        n_seeds = len(ta)
        cp_selected = sum(1 for r in cp if r["selected_from_method"] == "Segmented Hybrid GA")
        ta_selected = sum(1 for r in ta if r["selected_from_method"] == "Segmented Hybrid GA")
        status_counts = Counter(r["acceptance_status"] for r in ta)
        repaired = sum(1 for r in ta if f(r, "feasibility_improved") > 0.5)

        single_coverage = mean([f(r, "coverage_pct") for r in single])
        ta_coverage = mean([f(r, "coverage_pct") for r in ta])
        cp_coverage = mean([f(r, "coverage_pct") for r in cp])
        single_overlap = mean([f(r, "excess_overlap_pct") for r in single])
        ta_overlap = mean([f(r, "excess_overlap_pct") for r in ta])
        cp_overlap = mean([f(r, "excess_overlap_pct") for r in cp])
        single_path = mean([f(r, "path_length_km") for r in single])
        ta_path = mean([f(r, "path_length_km") for r in ta])
        cp_path = mean([f(r, "path_length_km") for r in cp])
        fixed_path = mean([f(r, "path_length_km") for r in fixed])
        single_time = mean([f(r, "transition_selector_mission_time_h") for r in single])
        ta_time = mean([f(r, "transition_selector_mission_time_h") for r in ta])
        cp_time = mean([f(r, "transition_selector_mission_time_h") for r in cp])
        single_gain = -pct_delta(single_path, fixed_path)
        ta_gain = -pct_delta(ta_path, fixed_path)
        cp_gain = -pct_delta(cp_path, fixed_path)

        if repaired == n_seeds:
            decision = "blockwise repair required"
        elif ta_selected > 0:
            decision = "select blockwise when gates justify"
        elif cp_selected > 0:
            decision = "coverage selector finds cleanup; transition gate retains single"
        elif status_counts.get("retained_single_heading_no_safe_segment", 0) == n_seeds:
            decision = "reject blockwise due to coverage gate"
        else:
            decision = "retain single heading"

        summaries.append(
            {
                "scene_id": scene_id,
                "scene_name": ta[0]["scene_name"],
                "scene_group": ta[0]["scene_group"],
                "terrain_class": ta[0]["terrain_class"],
                "n_seeds": n_seeds,
                "single_feasible_rate": mean([f(r, "feasible") for r in single]),
                "ta_feasible_rate": mean([f(r, "feasible") for r in ta]),
                "coverage_preserving_segment_selected_seeds": cp_selected,
                "transition_aware_segment_selected_seeds": ta_selected,
                "feasibility_repair_seeds": repaired,
                "retained_no_safe_segment_seeds": status_counts.get(
                    "retained_single_heading_no_safe_segment", 0
                ),
                "retained_lower_transition_objective_seeds": status_counts.get(
                    "retained_single_heading_lower_transition_objective", 0
                ),
                "single_coverage_pct_mean": single_coverage,
                "ta_coverage_pct_mean": ta_coverage,
                "coverage_delta_pp_ta_minus_single": ta_coverage - single_coverage,
                "cp_coverage_pct_mean": cp_coverage,
                "coverage_delta_pp_cp_minus_single": cp_coverage - single_coverage,
                "single_excess_overlap_pct_mean": single_overlap,
                "ta_excess_overlap_pct_mean": ta_overlap,
                "excess_overlap_delta_pp_ta_minus_single": ta_overlap - single_overlap,
                "cp_excess_overlap_pct_mean": cp_overlap,
                "excess_overlap_delta_pp_cp_minus_single": cp_overlap - single_overlap,
                "single_path_length_km_mean": single_path,
                "ta_path_length_km_mean": ta_path,
                "path_delta_pct_ta_vs_single": pct_delta(ta_path, single_path),
                "cp_path_length_km_mean": cp_path,
                "path_delta_pct_cp_vs_single": pct_delta(cp_path, single_path),
                "fixed_path_length_km_mean": fixed_path,
                "single_mission_time_h_mean": single_time,
                "ta_mission_time_h_mean": ta_time,
                "mission_time_delta_pct_ta_vs_single": pct_delta(ta_time, single_time),
                "cp_mission_time_h_mean": cp_time,
                "mission_time_delta_pct_cp_vs_single": pct_delta(cp_time, single_time),
                "single_path_gain_vs_fixed_pct_mean": single_gain,
                "cp_path_gain_vs_fixed_pct_mean": cp_gain,
                "ta_path_gain_vs_fixed_pct_mean": ta_gain,
                "decision_label": decision,
            }
        )
    return summaries


def write_csv(rows: list[dict[str, object]]) -> None:
    fieldnames = list(rows[0].keys())
    with (OUT_DIR / "segmented_decision_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: list[dict[str, object]]) -> None:
    payload = {
        "source": str(INPUT.relative_to(ROOT)),
        "scope": "decision audit derived from segmented-heading raw rows",
        "claim_boundary": (
            "Public-grid numerical fixed-line planning audit; not a controller, "
            "mission-log replay, deployment, hydrographic QA, or operational-safety claim."
        ),
        "summary": rows,
    }
    (OUT_DIR / "segmented_decision_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def write_readme(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Segmented decision audit",
        "",
        "This directory summarizes the gate-aware blockwise fixed-line extension from",
        "`segmented_heading_extension/segmented_heading_raw.csv`. It does not rerun",
        "the planner; it recomputes the decision logic that determines when a",
        "segmented-heading layout is accepted, rejected, or used only as a",
        "coverage-preserving but transition-cost-dominated alternative.",
        "",
        "The audit is a public-grid numerical planning artifact. It is not an AUV",
        "controller, Dubins planner, mission-log replay, sea/lake/deployment validation,",
        "hydrographic QA, or operational-safety result.",
        "",
        "## Key results",
        "",
        "| Scene | CP selected | TA selected | Feasibility repairs | TA C (%) | TA Oex (%) | TA time delta vs single (%) | Decision |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {scene_name} | {cp}/{n} | {ta}/{n} | {repair}/{n} | {cov:.2f} | {overlap:.3f} | {dt:.2f} | {decision} |".format(
                scene_name=row["scene_name"],
                cp=row["coverage_preserving_segment_selected_seeds"],
                ta=row["transition_aware_segment_selected_seeds"],
                repair=row["feasibility_repair_seeds"],
                n=row["n_seeds"],
                cov=row["ta_coverage_pct_mean"],
                overlap=row["ta_excess_overlap_pct_mean"],
                dt=row["mission_time_delta_pct_ta_vs_single"],
                decision=row["decision_label"],
            )
        )
    lines.extend(
        [
            "",
            "Regeneration command:",
            "",
            "```bash",
            "conda run -n uu python make_segmented_decision_audit.py",
            "```",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def make_figure(rows: list[dict[str, object]]) -> None:
    rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "axes.edgecolor": "#4b5563",
            "axes.labelcolor": "#263238",
            "xtick.color": "#374151",
            "ytick.color": "#374151",
        }
    )
    labels = [
        str(r["scene_name"])
        .replace("GEBCO ", "")
        .replace("USGS Cascadia 30 m High", "USGS High")
        .replace("Complex Terrain", "Synthetic Complex")
        for r in rows
    ]
    n = [int(r["n_seeds"]) for r in rows]
    cp = [int(r["coverage_preserving_segment_selected_seeds"]) for r in rows]
    ta = [int(r["transition_aware_segment_selected_seeds"]) for r in rows]
    repair = [int(r["feasibility_repair_seeds"]) for r in rows]
    time_delta = [float(r["mission_time_delta_pct_ta_vs_single"]) for r in rows]
    cp_overlap_cleanup = [
        -float(r["excess_overlap_delta_pp_cp_minus_single"]) for r in rows
    ]

    y = list(range(len(rows)))
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4), gridspec_kw={"wspace": 0.36})
    fig.patch.set_facecolor("white")

    ax = axes[0]
    ax.barh(y, n, color="#e5e7eb", height=0.70, label="30 seeds")
    ax.barh(y, cp, color="#8fb8b2", height=0.50, label="coverage-preserving")
    ax.barh(y, ta, color="#2f6f73", height=0.30, label="transition-aware")
    for yi, value in enumerate(ta):
        ax.text(value + 0.6, yi, f"{value}/30", va="center", fontsize=8)
    for yi, value in enumerate(repair):
        if value:
            ax.text(16, yi - 0.28, "repair", va="center", fontsize=8, color="#7c2d12")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 34)
    ax.set_xlabel("Selected blockwise layout seeds")
    ax.set_title("(a) Gate outcome", loc="left", fontsize=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.grid(axis="x", color="#edf2f7", linewidth=0.8)

    ax = axes[1]
    ax.axvline(0, color="#4b5563", linewidth=0.8)
    ax.scatter(
        cp_overlap_cleanup,
        y,
        s=66,
        color="#2f6f73",
        marker="s",
        label="CP overlap cleanup (pp)",
        zorder=3,
    )
    ax.scatter(
        time_delta,
        [yi + 0.16 for yi in y],
        s=66,
        color="#bc6c25",
        label="TA mission-time change (%)",
        zorder=3,
    )
    for yi, (cleanup, tdelta) in enumerate(zip(cp_overlap_cleanup, time_delta)):
        ax.plot([0, cleanup], [yi, yi], color="#b7cbc7", linewidth=1.2, zorder=1)
        ax.plot([0, tdelta], [yi + 0.16, yi + 0.16], color="#e5c29f", linewidth=1.2, zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Change relative to single-heading")
    ax.set_title("(b) Quantified trade-off", loc="left", fontsize=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=7.2, loc="lower right")
    ax.grid(axis="x", color="#edf2f7", linewidth=0.8)

    output = OUT_DIR / "journal_segmented_decision_audit.png"
    fig.savefig(output, dpi=320, bbox_inches="tight")
    plt.close(fig)
    image = Image.open(output).convert("RGB")
    image.save(output)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = summarize(load_rows())
    write_csv(rows)
    write_json(rows)
    write_readme(rows)
    make_figure(rows)
    print(f"summary_rows={len(rows)}")
    print(f"output_dir={OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
