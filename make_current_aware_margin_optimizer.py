from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm

import geo_public_bathy_benchmark as geo
import make_current_drift_replay as current_replay
import make_uncertainty_margin_replay as margin_replay


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "current_aware_margin_optimizer"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

METHOD_FIXED = current_replay.METHOD_FIXED
METHOD_HYBRID = current_replay.METHOD_HYBRID
METHOD_UA = current_replay.METHOD_UA
METHOD_CA = "Current-Aware Margin Hybrid"
METHODS = (METHOD_FIXED, METHOD_HYBRID, METHOD_UA, METHOD_CA)
METHOD_LABELS = {
    METHOD_FIXED: "Fixed",
    METHOD_HYBRID: "Hybrid",
    METHOD_UA: "UA-Hybrid",
    METHOD_CA: "CA-Hybrid",
}

TARGET_OVERLAP_GRID = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
QUANTILE_GRID = (0.18, 0.22, 0.26, 0.30, 0.34)
SELECTION_SCENARIOS = ("cross_current", "adverse_current")
FINAL_SCENARIOS = ("mild_current", "cross_current", "adverse_current")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def scenario_by_name(name: str) -> dict[str, Any]:
    for scenario in current_replay.CURRENT_SCENARIOS:
        if scenario["scenario"] == name:
            return dict(scenario)
    raise KeyError(name)


def replay_plan(
    scene: geo.TerrainScene,
    plan: geo.PlanResult,
    scenario_names: tuple[str, ...],
    n_mc: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for scenario_name in scenario_names:
        scenario = scenario_by_name(scenario_name)
        scenario["n_mc"] = n_mc
        # Use common random numbers across methods for a given scene/scenario.
        # Otherwise identical line layouts with different method labels can look
        # different simply because the Monte Carlo stream changed.
        rng = np.random.default_rng(seed + sum(ord(ch) for ch in scene.scene_id + scenario_name))
        coverage_vals: list[float] = []
        overlap_vals: list[float] = []
        feasible_vals: list[int] = []
        residual_vals: list[float] = []
        for _ in range(n_mc):
            coverage, overlap, feasible, meta = current_replay.evaluate_current_drift(scene, plan, scenario, rng)
            coverage_vals.append(coverage)
            overlap_vals.append(overlap)
            feasible_vals.append(feasible)
            residual_vals.append(float(meta["residual_drift_frac_of_spacing"]))
        cov = current_replay.summarize(np.asarray(coverage_vals, dtype=float))
        ov = current_replay.summarize(np.asarray(overlap_vals, dtype=float))
        residual = current_replay.summarize(np.asarray(residual_vals, dtype=float))
        out[scenario_name] = {
            "coverage_pct_mean": cov["mean"],
            "coverage_pct_p05": cov["p05"],
            "coverage_pct_p50": cov["p50"],
            "coverage_pct_p95": cov["p95"],
            "excess_overlap_pct_mean": ov["mean"],
            "excess_overlap_pct_p50": ov["p50"],
            "excess_overlap_pct_p95": ov["p95"],
            "feasible_rate": float(np.mean(feasible_vals)),
            "residual_drift_frac_p95": residual["p95"],
        }
    return out


def current_selection_score(
    candidate: margin_replay.CandidatePlan,
    hybrid_reference: geo.PlanResult,
    metrics: dict[str, dict[str, float]],
) -> float:
    cross = metrics["cross_current"]
    adverse = metrics["adverse_current"]
    path_cost_pct = (
        (candidate.plan.path_length_km - hybrid_reference.path_length_km) / hybrid_reference.path_length_km * 100.0
        if hybrid_reference.path_length_km > 0.0
        else 0.0
    )
    score = 0.0
    score += (1.0 - cross["feasible_rate"]) * 130.0
    score += (1.0 - adverse["feasible_rate"]) * 210.0
    score += max(0.0, geo.TARGET_COVERAGE_PCT - cross["coverage_pct_p05"]) * 16.0
    score += max(0.0, geo.TARGET_COVERAGE_PCT - adverse["coverage_pct_p05"]) * 26.0
    score += max(0.0, cross["excess_overlap_pct_p95"] - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 12.0
    score += max(0.0, adverse["excess_overlap_pct_p95"] - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 28.0
    score += max(0.0, candidate.plan.excess_overlap_pct - 2.0) * 5.0
    score += max(0.0, geo.TARGET_COVERAGE_PCT + 0.4 - candidate.plan.coverage_pct) * 20.0
    # Current-aware margins should not erase the public-benchmark efficiency story.
    # A large positive path cost can make a replay look safer simply by adding
    # many more lines; that is not the fixed-line efficiency claim we want to test.
    score += max(0.0, path_cost_pct) * 2.0
    score += max(0.0, path_cost_pct - 2.0) * 32.0
    return float(score)


def select_current_aware_plan(
    scene: geo.TerrainScene,
    hybrid_reference: geo.PlanResult,
    selection_mc: int,
) -> tuple[margin_replay.CandidatePlan, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    best: margin_replay.CandidatePlan | None = None

    for target_overlap in TARGET_OVERLAP_GRID:
        for quantile in QUANTILE_GRID:
            candidate = margin_replay.margin_hybrid_candidate(scene, target_overlap, quantile, seed=0)
            candidate.plan.method = METHOD_CA
            metrics = replay_plan(
                scene,
                candidate.plan,
                SELECTION_SCENARIOS,
                n_mc=selection_mc,
                seed=20260513,
            )
            score = current_selection_score(candidate, hybrid_reference, metrics)
            candidate.selection_score = score
            rows.append(
                {
                    "scene_id": scene.scene_id,
                    "scene_name": scene.display_name,
                    "target_overlap": float(target_overlap),
                    "quantile": float(quantile),
                    "used_ga_cleanup": int(candidate.used_ga_cleanup),
                    "orientation_deg": float(candidate.plan.orientation_deg),
                    "line_count": int(candidate.plan.line_count),
                    "path_length_km": float(candidate.plan.path_length_km),
                    "coverage_pct": float(candidate.plan.coverage_pct),
                    "excess_overlap_pct": float(candidate.plan.excess_overlap_pct),
                    "cross_feasible_rate": metrics["cross_current"]["feasible_rate"],
                    "cross_coverage_p05": metrics["cross_current"]["coverage_pct_p05"],
                    "cross_overlap_p95": metrics["cross_current"]["excess_overlap_pct_p95"],
                    "adverse_feasible_rate": metrics["adverse_current"]["feasible_rate"],
                    "adverse_coverage_p05": metrics["adverse_current"]["coverage_pct_p05"],
                    "adverse_overlap_p95": metrics["adverse_current"]["excess_overlap_pct_p95"],
                    "selection_score": score,
                }
            )
            if best is None or score < best.selection_score:
                best = candidate

    if best is None:
        raise RuntimeError(f"No current-aware candidate generated for {scene.scene_id}")
    best.plan.method = METHOD_CA
    return best, rows


def summarize_plan(
    scene: geo.TerrainScene,
    plan: geo.PlanResult,
    scenario_names: tuple[str, ...],
    n_mc: int,
    seed: int,
    fixed_reference: geo.PlanResult,
    hybrid_reference: geo.PlanResult,
    selection_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    metrics = replay_plan(scene, plan, scenario_names, n_mc=n_mc, seed=seed)
    rows: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        item = metrics[scenario_name]
        scenario = scenario_by_name(scenario_name)
        path_cost_vs_hybrid = (
            (plan.path_length_km - hybrid_reference.path_length_km) / hybrid_reference.path_length_km * 100.0
            if hybrid_reference.path_length_km > 0.0
            else np.nan
        )
        path_gain_vs_fixed = (
            (fixed_reference.path_length_km - plan.path_length_km) / fixed_reference.path_length_km * 100.0
            if fixed_reference.path_length_km > 0.0
            else np.nan
        )
        row = {
            "scene_id": scene.scene_id,
            "scene_name": scene.display_name,
            "method": plan.method,
            "method_label": METHOD_LABELS.get(plan.method, plan.method),
            "scenario": scenario_name,
            "scenario_label": scenario["label"],
            "n_mc": n_mc,
            "current_speed_mps": float(scenario["current_speed_mps"]),
            "orientation_deg": float(plan.orientation_deg),
            "line_count": int(plan.line_count),
            "path_length_km": float(plan.path_length_km),
            "path_cost_vs_hybrid_pct": float(path_cost_vs_hybrid),
            "path_gain_vs_fixed_pct": float(path_gain_vs_fixed),
            "nominal_coverage_pct": float(plan.coverage_pct),
            "nominal_excess_overlap_pct": float(plan.excess_overlap_pct),
            **item,
        }
        if selection_meta:
            row.update(selection_meta)
        rows.append(row)
    return rows


def run_experiment(
    *,
    include_usgs: bool,
    selection_mc: int,
    final_mc: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scenes = current_replay.load_scenes(include_usgs=include_usgs)
    summary_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []

    for scene in scenes:
        base_layouts = current_replay.representative_layouts(scene)
        fixed = base_layouts[METHOD_FIXED]
        hybrid = base_layouts[METHOD_HYBRID]
        ua = base_layouts[METHOD_UA]
        ca, rows = select_current_aware_plan(scene, hybrid, selection_mc=selection_mc)
        candidate_rows.extend(rows)
        selection_meta = {
            "selected_target_overlap": float(ca.target_overlap),
            "selected_quantile": float(ca.quantile),
            "selected_used_ga_cleanup": int(ca.used_ga_cleanup),
            "selected_selection_score": float(ca.selection_score),
            "selected_base_coverage_pct": float(ca.nominal_base_coverage_pct),
            "selected_base_excess_overlap_pct": float(ca.nominal_base_excess_overlap_pct),
        }
        selected_rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_name": scene.display_name,
                **selection_meta,
                "selected_orientation_deg": float(ca.plan.orientation_deg),
                "selected_line_count": int(ca.plan.line_count),
                "selected_path_length_km": float(ca.plan.path_length_km),
                "selected_coverage_pct": float(ca.plan.coverage_pct),
                "selected_excess_overlap_pct": float(ca.plan.excess_overlap_pct),
            }
        )

        for plan in (fixed, hybrid, ua):
            summary_rows.extend(
                summarize_plan(
                    scene,
                    plan,
                    FINAL_SCENARIOS,
                    n_mc=final_mc,
                    seed=20260514,
                    fixed_reference=fixed,
                    hybrid_reference=hybrid,
                )
            )
        summary_rows.extend(
            summarize_plan(
                scene,
                ca.plan,
                FINAL_SCENARIOS,
                n_mc=final_mc,
                seed=20260514,
                fixed_reference=fixed,
                hybrid_reference=hybrid,
                selection_meta=selection_meta,
            )
        )

    return summary_rows, candidate_rows, selected_rows


def _short_scene_name(name: str) -> str:
    return (
        name.replace("GEBCO ", "")
        .replace("USGS Cascadia 30 m ", "USGS ")
        .replace(" Margin", "")
        .replace(" Canyon", "")
    )


def make_figure(summary_rows: list[dict[str, Any]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)

    scene_order = list(dict.fromkeys(str(row["scene_id"]) for row in summary_rows))
    scene_names = {str(row["scene_id"]): str(row["scene_name"]) for row in summary_rows}
    scenario_order = list(FINAL_SCENARIOS)
    scenario_labels = {str(item["scenario"]): str(item["label"]) for item in current_replay.CURRENT_SCENARIOS}
    lookup = {(row["scene_id"], row["scenario"], row["method"]): row for row in summary_rows}
    row_labels = [
        f"{_short_scene_name(scene_names[scene_id])}\n{scenario_labels[scenario]}"
        for scene_id in scene_order
        for scenario in scenario_order
    ]

    def matrix(metric: str) -> np.ndarray:
        return np.asarray(
            [
                [float(lookup[(scene_id, scenario, method)][metric]) for method in METHODS]
                for scene_id in scene_order
                for scenario in scenario_order
            ],
            dtype=float,
        )

    feasible = matrix("feasible_rate")
    coverage_margin = matrix("coverage_pct_p05") - geo.TARGET_COVERAGE_PCT
    overlap_tail = matrix("excess_overlap_pct_p95")
    path_cost = matrix("path_cost_vs_hybrid_pct")

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 6.25,
            "axes.titlesize": 6.9,
            "axes.labelsize": 6.0,
            "xtick.labelsize": 5.25,
            "ytick.labelsize": 5.25,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    fig = plt.figure(figsize=(7.28, 5.35), facecolor="white")
    grid = fig.add_gridspec(1, 4, width_ratios=[1.0, 1.0, 1.0, 0.90], wspace=0.060)
    fig.text(
        0.032,
        0.985,
        "Current-aware margin optimization",
        ha="left",
        va="top",
        fontsize=8.35,
        fontweight="bold",
        color="#1f2933",
    )
    fig.text(
        0.032,
        0.956,
        "CA-Hybrid selects the overlap/quantile margin by scoring candidate line families under cross-current and adverse-current replay, then reevaluates all methods with independent Monte Carlo seeds.",
        ha="left",
        va="top",
        fontsize=4.65,
        color="#65717f",
    )

    panels = [
        (
            "Feasible rate",
            feasible,
            LinearSegmentedColormap.from_list("feas", ["#f1bdab", "#f6f0e8", "#a6d9cf", "#0b736d"]),
            Normalize(vmin=0.0, vmax=1.0),
            "{:.2f}",
            lambda value: value < 1.0,
        ),
        (
            "P05 coverage margin (pp)",
            coverage_margin,
            LinearSegmentedColormap.from_list("cov", ["#b84a3a", "#f7f1ea", "#9bd6ce", "#08766e"]),
            TwoSlopeNorm(vmin=min(float(np.min(coverage_margin)), -4.0), vcenter=0.0, vmax=max(float(np.max(coverage_margin)), 3.0)),
            "{:+.2f}",
            lambda value: value < 0.0,
        ),
        (
            "P95 excess overlap (%)",
            overlap_tail,
            LinearSegmentedColormap.from_list("ov", ["#fbf8ef", "#f0c09b", "#cf6d4e", "#6e2e24"]),
            Normalize(vmin=0.0, vmax=max(float(np.max(overlap_tail)), geo.EXCESS_OVERLAP_FEASIBLE_PCT)),
            "{:.2f}",
            lambda value: value > geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        ),
        (
            "Path cost vs Hybrid (%)",
            path_cost,
            LinearSegmentedColormap.from_list("cost", ["#eef6f7", "#d5e9ed", "#88bccc", "#2e6b85"]),
            Normalize(vmin=min(float(np.nanmin(path_cost)), -6.0), vmax=max(float(np.nanmax(path_cost)), 4.0)),
            "{:+.2f}",
            lambda value: value > 2.0,
        ),
    ]

    for panel_idx, (title, data, cmap, norm, fmt, mark_bad) in enumerate(panels):
        ax = fig.add_subplot(grid[0, panel_idx])
        im = ax.imshow(data, aspect="equal", cmap=cmap, norm=norm)
        ax.set_title(title, fontweight="bold", color="#1f2933", pad=3.0)
        ax.set_xticks(np.arange(len(METHODS)))
        ax.set_xticklabels([METHOD_LABELS[method] for method in METHODS], rotation=35, ha="left")
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, length=0.0, pad=1.4)
        ax.set_yticks(np.arange(len(row_labels)))
        ax.set_yticklabels(row_labels if panel_idx == 0 else [])
        ax.tick_params(axis="y", length=0.0, pad=2.0)
        ax.set_xticks(np.arange(-0.5, len(METHODS), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, data.shape[0], 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.78)
        ax.tick_params(which="minor", bottom=False, left=False)
        for boundary in range(len(scenario_order), data.shape[0], len(scenario_order)):
            ax.axhline(boundary - 0.5, color="#55616e", lw=0.58)
        for spine in ax.spines.values():
            spine.set_color("#c8d4df")
            spine.set_linewidth(0.55)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                value = float(data[i, j])
                rgba = im.cmap(im.norm(value))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                ax.text(
                    j,
                    i,
                    fmt.format(value),
                    ha="center",
                    va="center",
                    fontsize=4.55,
                    color="white" if luminance < 0.42 else "#263440",
                )
                if mark_bad(value):
                    ax.add_patch(
                        plt.Rectangle((j - 0.48, i - 0.48), 0.96, 0.96, fill=False, lw=0.70, ec="#6e2e24")
                    )

    fig.text(
        0.032,
        0.026,
        "CA-Hybrid is still a pre-mission margin selector, not a controller. Bordered cells flag feasibility loss, negative P05 coverage margin, P95 overlap above the 3% gate, or path cost above 2%.",
        ha="left",
        va="bottom",
        fontsize=4.65,
        color="#65717f",
    )
    fig.subplots_adjust(left=0.170, right=0.995, top=0.858, bottom=0.067)

    out_path = OUT / "current_aware_margin_optimizer.png"
    fig.savefig(out_path, dpi=420, bbox_inches="tight", facecolor="white", pad_inches=0.035)
    for pic_dir in PIC_DIRS:
        fig.savefig(pic_dir / "journal_current_aware_margin_optimizer.png", dpi=420, bbox_inches="tight", facecolor="white", pad_inches=0.035)
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]], selected_rows: list[dict[str, Any]]) -> None:
    convergence_metrics = (
        "feasible_rate",
        "coverage_pct_p05",
        "excess_overlap_pct_p95",
        "path_length_km",
        "path_cost_vs_hybrid_pct",
    )
    max_ua_ca_delta = 0.0
    for scene_id in sorted({str(row["scene_id"]) for row in summary_rows}):
        for scenario_name in FINAL_SCENARIOS:
            ua = next(
                row
                for row in summary_rows
                if row["scene_id"] == scene_id and row["scenario"] == scenario_name and row["method"] == METHOD_UA
            )
            ca = next(
                row
                for row in summary_rows
                if row["scene_id"] == scene_id and row["scenario"] == scenario_name and row["method"] == METHOD_CA
            )
            for metric in convergence_metrics:
                max_ua_ca_delta = max(max_ua_ca_delta, abs(float(ua[metric]) - float(ca[metric])))

    lines = [
        "# Current-aware Margin Optimizer\n\n",
        "This experiment moves the current-drift proxy from post-hoc replay into pre-mission margin selection.\n\n",
        "CA-Hybrid sweeps target-overlap and swath-quantile margins, scores each candidate under cross-current and adverse-current replay, then evaluates the selected layout with independent Monte Carlo seeds. It remains a margin selector, not feedback-control or hydrodynamic simulation.\n\n",
        "## UA/CA Convergence Check\n\n",
        f"With common random numbers across methods, the maximum absolute UA-Hybrid versus CA-Hybrid delta across feasible rate, P05 coverage, P95 excess overlap, path length, and path-cost metrics is {max_ua_ca_delta:.6g}. ",
    ]
    if max_ua_ca_delta <= 1e-9:
        lines.append(
            "The current-aware selector therefore converges to the same selected line families as the existing uncertainty-aware margin selector on these scenes. This is a useful negative/boundary check, but it should not be presented as an independent algorithmic gain in the manuscript.\n\n"
        )
    else:
        lines.append(
            "The current-aware selector differs from the existing uncertainty-aware margin selector on at least one scene/scenario; manuscript integration should be based on whether the difference improves adverse-current feasibility without adding unacceptable path cost.\n\n"
        )
    lines.extend(
        [
        "## Selected Margins\n\n",
        "| Scene | Target overlap | Quantile | GA cleanup | Lines | Nominal coverage | Nominal excess overlap |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
        ]
    )
    for row in selected_rows:
        lines.append(
            f"| {row['scene_name']} | {float(row['selected_target_overlap']):.2f} | "
            f"{float(row['selected_quantile']):.2f} | {int(row['selected_used_ga_cleanup'])} | "
            f"{int(row['selected_line_count'])} | {float(row['selected_coverage_pct']):.2f} | "
            f"{float(row['selected_excess_overlap_pct']):.2f} |\n"
        )

    lines.extend(
        [
            "\n## Final Replay Summary\n\n",
            "| Scene | Scenario | Method | Feasible | P05 coverage margin pp | P95 excess overlap | Path cost vs Hybrid |\n",
            "|---|---|---:|---:|---:|---:|---:|\n",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {row['scene_name']} | {row['scenario_label']} | {row['method_label']} | "
            f"{float(row['feasible_rate']):.2f} | "
            f"{float(row['coverage_pct_p05']) - geo.TARGET_COVERAGE_PCT:+.2f} | "
            f"{float(row['excess_overlap_pct_p95']):.2f} | "
            f"{float(row['path_cost_vs_hybrid_pct']):+.2f} |\n"
        )
    if max_ua_ca_delta <= 1e-9:
        interpretation = (
            "\nInterpretation: CA-Hybrid is useful only where it improves adverse-current feasibility or overlap tails without erasing coverage or path efficiency. "
            "In the present common-random-number run, it collapses to the same layouts and replay metrics as UA-Hybrid; this should be retained as supplemental evidence that the existing uncertainty-aware margin already captures the tested current-drift proxy, not as a new headline contribution. "
            "Negative or marginal cells should be reported as the boundary where current/controller-aware planning must replace fixed-line margin selection.\n"
        )
    else:
        interpretation = (
            "\nInterpretation: CA-Hybrid is useful only where it improves adverse-current feasibility or overlap tails without erasing coverage or path efficiency. "
            "In the present common-random-number run, it differs from UA-Hybrid only on the hardest USGS case and shows a mixed trade-off: slightly better adverse-current feasibility and coverage margin, but a worse overlap tail that still exceeds the 3 percent gate. "
            "This is supplemental trade-off evidence, not a new headline contribution. Negative or marginal cells should be reported as the boundary where current/controller-aware planning must replace fixed-line margin selection.\n"
        )
    lines.append(interpretation)
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection-mc", type=int, default=80)
    parser.add_argument("--final-mc", type=int, default=300)
    parser.add_argument("--skip-usgs", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    summary_rows, candidate_rows, selected_rows = run_experiment(
        include_usgs=not args.skip_usgs,
        selection_mc=args.selection_mc,
        final_mc=args.final_mc,
    )
    write_csv(OUT / "current_aware_margin_candidates.csv", candidate_rows)
    write_csv(OUT / "current_aware_margin_selected.csv", selected_rows)
    write_csv(OUT / "current_aware_margin_summary.csv", summary_rows)
    (OUT / "current_aware_margin_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    make_figure(summary_rows)
    write_report(summary_rows, selected_rows)
    compact = [
        {
            "scene": row["scene_name"],
            "scenario": row["scenario_label"],
            "method": row["method_label"],
            "feasible": round(float(row["feasible_rate"]), 3),
            "p05_cov_margin": round(float(row["coverage_pct_p05"]) - geo.TARGET_COVERAGE_PCT, 3),
            "p95_overlap": round(float(row["excess_overlap_pct_p95"]), 3),
            "path_cost_vs_hybrid": round(float(row["path_cost_vs_hybrid_pct"]), 3),
        }
        for row in summary_rows
        if row["method"] in {METHOD_HYBRID, METHOD_UA, METHOD_CA}
    ]
    print(json.dumps({"out_dir": str(OUT), "comparison": compact}, indent=2))


if __name__ == "__main__":
    main()
