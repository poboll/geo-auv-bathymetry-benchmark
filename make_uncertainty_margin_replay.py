from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize, TwoSlopeNorm

import geo_public_bathy_benchmark as geo
import journal_heatmap_style as jhs
import make_structured_prior_error_replay as prior_replay
import make_uncertainty_replay as uncertainty


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "uncertainty_margin_replay"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

BASE_METHODS = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
)
SELECTED_METHOD = "Uncertainty-Aware Margin Hybrid"
METHODS = (*BASE_METHODS, SELECTED_METHOD)
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adapt.",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
    SELECTED_METHOD: "UA-Hyb.",
}

TARGET_OVERLAP_GRID = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
QUANTILE_GRID = (0.18, 0.22, 0.26, 0.30, 0.34)

METHOD_COLORS = {
    "Fixed-Spacing": "#707782",
    "Adaptive Spacing w/o GA": "#1f8f83",
    "Full Geometry-Aware Hybrid GA": "#c66b3d",
    SELECTED_METHOD: "#244f75",
}


@dataclass
class CandidatePlan:
    plan: geo.PlanResult
    target_overlap: float
    quantile: float
    used_ga_cleanup: bool
    nominal_base_coverage_pct: float
    nominal_base_excess_overlap_pct: float
    selection_score: float = float("inf")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_scenes(include_usgs: bool) -> list[geo.TerrainScene]:
    scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    if include_usgs:
        usgs = prior_replay.load_usgs_high_scene()
        if usgs is not None:
            scenes.append(usgs)
    return scenes


def adaptive_candidate(
    scene: geo.TerrainScene,
    target_overlap: float,
    quantile: float,
) -> geo.LayoutCandidate:
    best = geo.LayoutCandidate(
        orientation_deg=float(geo.ANGLE_CANDIDATES[0]),
        line_positions=np.asarray([], dtype=float),
        coverage_pct=0.0,
        excess_overlap_pct=float("inf"),
        score=float("inf"),
    )
    for angle in geo.ANGLE_CANDIDATES:
        context = geo.make_context(scene, float(angle))
        profile_v, profile_w = geo.cross_track_profile(context, quantile)
        positions = geo.adaptive_line_positions(
            context.vmin,
            context.vmax,
            profile_v,
            profile_w,
            overlap_target=target_overlap,
        )
        coverage_pct, overlap_pct = geo.coverage_and_overlap(context.v_grid, positions, context.swath_width)
        path_length_km = geo.plan_length_km(scene, positions, context.phi_rad)
        coverage_penalty = max(0.0, geo.TARGET_COVERAGE_PCT + 0.5 - coverage_pct) * 120.0
        overlap_penalty = max(0.0, overlap_pct - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 60.0
        score = path_length_km + coverage_penalty + overlap_penalty + overlap_pct * 2.0
        if score < best.score:
            best = geo.LayoutCandidate(
                orientation_deg=float(angle),
                line_positions=positions,
                coverage_pct=coverage_pct,
                excess_overlap_pct=overlap_pct,
                score=score,
            )
    return best


def margin_hybrid_candidate(
    scene: geo.TerrainScene,
    target_overlap: float,
    quantile: float,
    seed: int,
) -> CandidatePlan:
    base = adaptive_candidate(scene, target_overlap, quantile)
    base_plan = geo.evaluate_plan(
        scene,
        SELECTED_METHOD,
        seed,
        base.orientation_deg,
        base.line_positions,
        0.0,
    )

    rng = np.random.default_rng(10_000 + seed)
    refined = geo.ga_refine_layout(
        scene,
        base.orientation_deg,
        base.line_positions,
        rng,
        generations=max(6, geo.GA_GENERATIONS // 2),
        pop_size=max(8, geo.GA_POP_SIZE),
    )
    refined_plan = geo.evaluate_plan(scene, SELECTED_METHOD, seed, base.orientation_deg, refined, 0.0)

    preserves_margin = (
        refined_plan.feasible
        and refined_plan.coverage_pct >= base_plan.coverage_pct - 0.20
        and refined_plan.excess_overlap_pct <= max(base_plan.excess_overlap_pct + 0.25, geo.EXCESS_OVERLAP_FEASIBLE_PCT)
    )
    shortens_layout = refined_plan.path_length_km <= base_plan.path_length_km
    chosen = refined_plan if preserves_margin and shortens_layout else base_plan
    return CandidatePlan(
        plan=chosen,
        target_overlap=target_overlap,
        quantile=quantile,
        used_ga_cleanup=bool(chosen is refined_plan),
        nominal_base_coverage_pct=float(base_plan.coverage_pct),
        nominal_base_excess_overlap_pct=float(base_plan.excess_overlap_pct),
    )


def representative_layouts(scene: geo.TerrainScene) -> dict[str, geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed=0)
    return {
        "Fixed-Spacing": fixed,
        "Adaptive Spacing w/o GA": adaptive,
        "Full Geometry-Aware Hybrid GA": hybrid,
    }


def scenario_by_name(name: str) -> dict[str, Any]:
    for scenario in uncertainty.SCENARIOS:
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
    metrics: dict[str, dict[str, float]] = {}
    for scenario_name in scenario_names:
        scenario = scenario_by_name(scenario_name)
        scenario["n_mc"] = n_mc if scenario_name != "nominal" else 1
        # Common random numbers across methods/candidates for a given
        # scene/scenario make robust-margin comparisons less noisy and avoid
        # attributing Monte Carlo stream differences to the line layout.
        rng = np.random.default_rng(seed + sum(ord(ch) for ch in scene.scene_id + scenario_name))
        coverage_vals: list[float] = []
        overlap_vals: list[float] = []
        feasible_vals: list[int] = []
        for _ in range(int(scenario["n_mc"])):
            coverage, overlap, feasible, _, _, _ = uncertainty.evaluate_noisy(scene, plan, scenario, rng)
            coverage_vals.append(coverage)
            overlap_vals.append(overlap)
            feasible_vals.append(feasible)
        cov = uncertainty.summarize(np.asarray(coverage_vals, dtype=float))
        ov = uncertainty.summarize(np.asarray(overlap_vals, dtype=float))
        metrics[scenario_name] = {
            "coverage_pct_mean": cov["mean"],
            "coverage_pct_p05": cov["p05"],
            "coverage_pct_p50": cov["p50"],
            "coverage_pct_p95": cov["p95"],
            "excess_overlap_pct_mean": ov["mean"],
            "excess_overlap_pct_p50": ov["p50"],
            "excess_overlap_pct_p95": ov["p95"],
            "feasible_rate": float(np.mean(feasible_vals)),
        }
    return metrics


def robust_selection_score(
    candidate: CandidatePlan,
    hybrid_reference: geo.PlanResult,
    metrics: dict[str, dict[str, float]],
) -> float:
    moderate = metrics["moderate_noise"]
    strong = metrics["strong_noise"]
    path_cost_pct = (
        (candidate.plan.path_length_km - hybrid_reference.path_length_km) / hybrid_reference.path_length_km * 100.0
        if hybrid_reference.path_length_km > 0.0
        else 0.0
    )
    score = 0.0
    score += (1.0 - moderate["feasible_rate"]) * 160.0
    score += (1.0 - strong["feasible_rate"]) * 65.0
    score += max(0.0, geo.TARGET_COVERAGE_PCT - moderate["coverage_pct_p05"]) * 12.0
    score += max(0.0, geo.TARGET_COVERAGE_PCT - strong["coverage_pct_p05"]) * 8.0
    score += max(0.0, moderate["excess_overlap_pct_p95"] - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 14.0
    score += max(0.0, strong["excess_overlap_pct_p95"] - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 8.0
    score += max(0.0, path_cost_pct) * 0.45
    score += max(0.0, candidate.plan.excess_overlap_pct - 1.5) * 4.0
    score += max(0.0, geo.TARGET_COVERAGE_PCT + 0.5 - candidate.plan.coverage_pct) * 20.0
    return float(score)


def select_uncertainty_margin_plan(
    scene: geo.TerrainScene,
    hybrid_reference: geo.PlanResult,
    selection_mc: int,
) -> tuple[CandidatePlan, list[dict[str, Any]]]:
    candidate_rows: list[dict[str, Any]] = []
    best: CandidatePlan | None = None

    for target_overlap in TARGET_OVERLAP_GRID:
        for quantile in QUANTILE_GRID:
            candidate = margin_hybrid_candidate(scene, target_overlap, quantile, seed=0)
            metrics = replay_plan(
                scene,
                candidate.plan,
                ("moderate_noise", "strong_noise"),
                n_mc=selection_mc,
                seed=20260511,
            )
            score = robust_selection_score(candidate, hybrid_reference, metrics)
            candidate.selection_score = score
            candidate_rows.append(
                {
                    "scene_id": scene.scene_id,
                    "scene_name": scene.display_name,
                    "target_overlap": target_overlap,
                    "quantile": quantile,
                    "used_ga_cleanup": int(candidate.used_ga_cleanup),
                    "orientation_deg": candidate.plan.orientation_deg,
                    "line_count": candidate.plan.line_count,
                    "path_length_km": candidate.plan.path_length_km,
                    "coverage_pct": candidate.plan.coverage_pct,
                    "excess_overlap_pct": candidate.plan.excess_overlap_pct,
                    "moderate_feasible_rate": metrics["moderate_noise"]["feasible_rate"],
                    "moderate_coverage_p05": metrics["moderate_noise"]["coverage_pct_p05"],
                    "moderate_overlap_p95": metrics["moderate_noise"]["excess_overlap_pct_p95"],
                    "strong_feasible_rate": metrics["strong_noise"]["feasible_rate"],
                    "strong_coverage_p05": metrics["strong_noise"]["coverage_pct_p05"],
                    "strong_overlap_p95": metrics["strong_noise"]["excess_overlap_pct_p95"],
                    "selection_score": score,
                }
            )
            if best is None or score < best.selection_score:
                best = candidate

    if best is None:
        raise RuntimeError(f"No uncertainty-margin candidate generated for {scene.scene_id}")
    return best, candidate_rows


def summarize_final(
    scene: geo.TerrainScene,
    plan: geo.PlanResult,
    scenario_names: tuple[str, ...],
    n_mc: int,
    seed: int,
    *,
    selection_meta: dict[str, Any] | None = None,
    fixed_reference: geo.PlanResult | None = None,
    hybrid_reference: geo.PlanResult | None = None,
) -> list[dict[str, Any]]:
    metrics = replay_plan(scene, plan, scenario_names, n_mc=n_mc, seed=seed)
    rows: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        scenario_n = 1 if scenario_name == "nominal" else n_mc
        item = metrics[scenario_name]
        path_gain_vs_fixed = np.nan
        path_cost_vs_hybrid = np.nan
        if fixed_reference is not None and fixed_reference.path_length_km > 0:
            path_gain_vs_fixed = (fixed_reference.path_length_km - plan.path_length_km) / fixed_reference.path_length_km * 100.0
        if hybrid_reference is not None and hybrid_reference.path_length_km > 0:
            path_cost_vs_hybrid = (plan.path_length_km - hybrid_reference.path_length_km) / hybrid_reference.path_length_km * 100.0
        row = {
            "scene_id": scene.scene_id,
            "scene_name": scene.display_name,
            "method": plan.method,
            "method_label": METHOD_LABELS.get(plan.method, plan.method),
            "scenario": scenario_name,
            "n_mc": scenario_n,
            "orientation_deg": float(plan.orientation_deg),
            "line_count": int(plan.line_count),
            "path_length_km": float(plan.path_length_km),
            "path_gain_vs_fixed_pct": float(path_gain_vs_fixed),
            "path_cost_vs_hybrid_pct": float(path_cost_vs_hybrid),
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
    scenes = load_scenes(include_usgs=include_usgs)
    candidate_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    scenario_names = ("nominal", "moderate_noise", "strong_noise")

    for scene in scenes:
        layouts = representative_layouts(scene)
        selected, candidates = select_uncertainty_margin_plan(
            scene,
            layouts["Full Geometry-Aware Hybrid GA"],
            selection_mc=selection_mc,
        )
        candidate_rows.extend(candidates)
        selection_meta = {
            "selected_target_overlap": float(selected.target_overlap),
            "selected_quantile": float(selected.quantile),
            "selected_used_ga_cleanup": int(selected.used_ga_cleanup),
            "selected_selection_score": float(selected.selection_score),
            "selected_base_coverage_pct": float(selected.nominal_base_coverage_pct),
            "selected_base_excess_overlap_pct": float(selected.nominal_base_excess_overlap_pct),
        }
        selected_rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_name": scene.display_name,
                **selection_meta,
                "selected_orientation_deg": float(selected.plan.orientation_deg),
                "selected_line_count": int(selected.plan.line_count),
                "selected_path_length_km": float(selected.plan.path_length_km),
                "selected_coverage_pct": float(selected.plan.coverage_pct),
                "selected_excess_overlap_pct": float(selected.plan.excess_overlap_pct),
            }
        )

        for method in BASE_METHODS:
            summary_rows.extend(
                summarize_final(
                    scene,
                    layouts[method],
                    scenario_names,
                    n_mc=final_mc,
                    seed=20260512,
                    fixed_reference=layouts["Fixed-Spacing"],
                    hybrid_reference=layouts["Full Geometry-Aware Hybrid GA"],
                )
            )
        summary_rows.extend(
            summarize_final(
                scene,
                selected.plan,
                scenario_names,
                n_mc=final_mc,
                seed=20260512,
                selection_meta=selection_meta,
                fixed_reference=layouts["Fixed-Spacing"],
                hybrid_reference=layouts["Full Geometry-Aware Hybrid GA"],
            )
        )

    return summary_rows, candidate_rows, selected_rows


def make_figure(summary_rows: list[dict[str, Any]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)

    scenarios = ["moderate_noise", "strong_noise"]
    scene_order = list(dict.fromkeys(str(row["scene_id"]) for row in summary_rows))
    scene_names = {str(row["scene_id"]): str(row["scene_name"]) for row in summary_rows}
    lookup = {(row["scene_id"], row["scenario"], row["method"]): row for row in summary_rows}
    scene_short_labels = {
        "gebco_cascadia_margin_moderate": "Casc.",
        "gebco_monterey_canyon_complex": "Mont.",
        "usgs_southern_cascadia_30m_high": "USGS-H",
    }
    scenario_short_labels = {
        "moderate_noise": "Mod.",
        "strong_noise": "Strong",
    }
    row_labels: list[str] = []
    for scene_id in scene_order:
        for scenario in scenarios:
            row_labels.append(f"{scene_short_labels.get(scene_id, scene_names[scene_id])} {scenario_short_labels.get(scenario, scenario)}")

    def matrix(metric: str) -> np.ndarray:
        rows: list[list[float]] = []
        for scene_id in scene_order:
            for scenario in scenarios:
                rows.append([float(lookup[(scene_id, scenario, method)][metric]) for method in METHODS])
        return np.asarray(rows, dtype=float)

    feasible = matrix("feasible_rate")
    coverage_margin_p05 = matrix("coverage_pct_p05") - geo.TARGET_COVERAGE_PCT
    overlap_p95 = matrix("excess_overlap_pct_p95")
    path_cost = matrix("path_cost_vs_hybrid_pct")

    jhs.apply_rc(base_font=8.70)
    fig = plt.figure(figsize=(7.25, 3.90), facecolor=jhs.BG)
    grid = fig.add_gridspec(2, 2, wspace=0.055, hspace=0.155)

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
            "(b) P05 coverage margin (pp)",
            coverage_margin_p05,
            jhs.COVERAGE_CMAP,
            TwoSlopeNorm(vmin=min(float(np.min(coverage_margin_p05)), -3.0), vcenter=0.0, vmax=max(float(np.max(coverage_margin_p05)), 3.0)),
            "{:+.2f}",
            lambda value: value < 0.0,
        ),
        (
            "(c) P95 excess-overlap tail (%)",
            overlap_p95,
            jhs.OVERLAP_CMAP,
            Normalize(vmin=0.0, vmax=max(float(np.max(overlap_p95)), geo.EXCESS_OVERLAP_FEASIBLE_PCT)),
            "{:.2f}",
            lambda value: value > geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        ),
        (
            "(d) Path cost vs Hybrid (%)",
            path_cost,
            jhs.TIME_CMAP,
            Normalize(vmin=min(float(np.nanmin(path_cost)), 0.0), vmax=max(float(np.nanmax(path_cost)), 1.0)),
            "{:+.2f}",
            lambda value: value > 2.0,
        ),
    ]

    col_labels = [METHOD_LABELS[method] for method in METHODS]
    for panel_idx, (title, data, cmap, norm, fmt, mark_bad) in enumerate(panels):
        ax = fig.add_subplot(grid[panel_idx // 2, panel_idx % 2])
        ax.imshow(data, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
        jhs.style_heatmap_axis(
            ax,
            title,
            col_labels,
            row_labels if panel_idx in (0, 2) else None,
            data.shape[0],
            group_every=len(scenarios),
        )
        jhs.annotate_cells(ax, data, cmap, norm, fmt, mark_bad=mark_bad, fontsize=6.85)
    fig.subplots_adjust(left=0.120, right=0.997, top=0.932, bottom=0.062, wspace=0.055, hspace=0.155)

    out_path = OUT / "uncertainty_margin_replay.png"
    jhs.save_white_rgb(fig, out_path, pad_inches=0.018)
    for pic_dir in PIC_DIRS:
        jhs.save_white_rgb(fig, pic_dir / "journal_uncertainty_margin_replay.png", pad_inches=0.018)
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]], selected_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Uncertainty-aware Margin Replay\n\n",
        "This experiment asks whether a declared execution-error envelope can be used to select an execution-aware pre-mission line-layout margin before field execution.\n\n",
        "It does not claim closed-loop vehicle control. It selects target-overlap and swath-quantile margins, optionally accepting GA cleanup only when nominal coverage and overlap gates are preserved.\n\n",
        "## Selected Margins\n\n",
        "| Scene | Target overlap | Quantile | GA cleanup | Lines | Nominal coverage | Nominal excess overlap |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for row in selected_rows:
        lines.append(
            f"| {row['scene_name']} | {float(row['selected_target_overlap']):.2f} | "
            f"{float(row['selected_quantile']):.2f} | {int(row['selected_used_ga_cleanup'])} | "
            f"{int(row['selected_line_count'])} | {float(row['selected_coverage_pct']):.2f} | "
            f"{float(row['selected_excess_overlap_pct']):.2f} |\n"
        )

    lines.extend(
        [
            "\n## Replay Summary\n\n",
            "| Scene | Scenario | Method | Feasible | P05 coverage margin pp | P95 excess overlap | Path cost vs Hybrid |\n",
            "|---|---|---:|---:|---:|---:|---:|\n",
        ]
    )
    for row in summary_rows:
        if row["scenario"] == "nominal":
            continue
        lines.append(
            f"| {row['scene_name']} | {row['scenario']} | {row['method_label']} | "
            f"{float(row['feasible_rate']):.2f} | "
            f"{float(row['coverage_pct_p05']) - geo.TARGET_COVERAGE_PCT:+.2f} | "
            f"{float(row['excess_overlap_pct_p95']):.2f} | "
            f"{float(row['path_cost_vs_hybrid_pct']):+.2f} |\n"
        )
    lines.append(
        "\nInterpretation: useful if UA-Hybrid raises strong-noise feasibility without making moderate-noise overlap unsafe. If strong-noise cells remain bordered, that is an evidence boundary rather than a styling problem: it means the manuscript should call for vehicle/controller-level margins rather than claiming field readiness.\n"
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection-mc", type=int, default=120)
    parser.add_argument("--final-mc", type=int, default=300)
    parser.add_argument("--skip-usgs", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    summary_rows, candidate_rows, selected_rows = run_experiment(
        include_usgs=not args.skip_usgs,
        selection_mc=args.selection_mc,
        final_mc=args.final_mc,
    )
    write_csv(OUT / "uncertainty_margin_candidates.csv", candidate_rows)
    write_csv(OUT / "uncertainty_margin_selected.csv", selected_rows)
    write_csv(OUT / "uncertainty_margin_summary.csv", summary_rows)
    (OUT / "uncertainty_margin_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    make_figure(summary_rows)
    write_report(summary_rows, selected_rows)
    compact = [
        {
            "scene": row["scene_name"],
            "method": row["method_label"],
            "scenario": row["scenario"],
            "feasible": round(float(row["feasible_rate"]), 3),
            "p05_cov_margin": round(float(row["coverage_pct_p05"]) - geo.TARGET_COVERAGE_PCT, 3),
            "p95_overlap": round(float(row["excess_overlap_pct_p95"]), 3),
            "path_cost_vs_hybrid": round(float(row["path_cost_vs_hybrid_pct"]), 3),
        }
        for row in summary_rows
        if row["scenario"] != "nominal" and row["method"] in {"Full Geometry-Aware Hybrid GA", SELECTED_METHOD}
    ]
    print(json.dumps({"out_dir": str(OUT), "comparison": compact}, indent=2))


if __name__ == "__main__":
    main()
