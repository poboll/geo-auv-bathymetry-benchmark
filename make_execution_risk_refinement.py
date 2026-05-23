from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm

import geo_public_bathy_benchmark as geo
import make_current_aware_margin_optimizer as current_opt
import make_current_drift_replay as current_replay
import make_uncertainty_margin_replay as margin_replay


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "execution_risk_refinement"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

METHOD_HYBRID = current_replay.METHOD_HYBRID
METHOD_UA = current_replay.METHOD_UA
METHOD_CA = current_opt.METHOD_CA
METHOD_RISK = "Execution-Risk-Aware Hybrid"
METHODS = (METHOD_HYBRID, METHOD_UA, METHOD_CA, METHOD_RISK)
METHOD_LABELS = {
    METHOD_HYBRID: "Hybrid",
    METHOD_UA: "UA-Hybrid",
    METHOD_CA: "CA-Hybrid",
    METHOD_RISK: "ER-Hybrid",
}

TARGET_OVERLAP_GRID = (0.05, 0.075, 0.10, 0.125, 0.15)
QUANTILE_GRID = (0.22, 0.26, 0.30, 0.34, 0.38)
FINAL_SCENARIOS = ("mild_current", "cross_current", "adverse_current")

STRESS_CASES = (
    {
        "case": "nominal",
        "heading_deg": 0.0,
        "bias_frac": 0.00,
        "wave_frac": 0.00,
        "swath_scale": 1.00,
        "coverage_gate": geo.TARGET_COVERAGE_PCT + 1.00,
        "overlap_gate": 2.60,
        "weight": 0.80,
    },
    {
        "case": "cross_left",
        "heading_deg": 0.85,
        "bias_frac": 0.08,
        "wave_frac": 0.04,
        "swath_scale": 0.955,
        "coverage_gate": geo.TARGET_COVERAGE_PCT + 0.75,
        "overlap_gate": geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        "weight": 1.15,
    },
    {
        "case": "cross_right",
        "heading_deg": -0.85,
        "bias_frac": -0.08,
        "wave_frac": -0.04,
        "swath_scale": 0.955,
        "coverage_gate": geo.TARGET_COVERAGE_PCT + 0.75,
        "overlap_gate": geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        "weight": 1.15,
    },
    {
        "case": "adverse_left",
        "heading_deg": 1.65,
        "bias_frac": 0.180,
        "wave_frac": 0.095,
        "swath_scale": 0.890,
        "coverage_gate": geo.TARGET_COVERAGE_PCT + 0.75,
        "overlap_gate": geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        "weight": 1.80,
    },
    {
        "case": "adverse_right",
        "heading_deg": -1.65,
        "bias_frac": -0.180,
        "wave_frac": -0.095,
        "swath_scale": 0.890,
        "coverage_gate": geo.TARGET_COVERAGE_PCT + 0.75,
        "overlap_gate": geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        "weight": 1.80,
    },
)


@dataclass
class CandidateRecord:
    plan: geo.PlanResult
    source: str
    target_overlap: float | None
    quantile: float | None
    deterministic_score: float
    nominal_coverage_pct: float
    nominal_excess_overlap_pct: float
    stress_min_coverage_pct: float
    stress_max_excess_overlap_pct: float


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


def _lookup_selected_margin(path: Path, scene_id: str) -> tuple[float, float] | None:
    if not path.exists():
        return None
    with path.open("r", newline="", encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            if row.get("scene_id") == scene_id:
                return float(row["selected_target_overlap"]), float(row["selected_quantile"])
    return None


def current_aware_selected_plan(scene: geo.TerrainScene) -> geo.PlanResult:
    selected = _lookup_selected_margin(
        ROOT / "current_aware_margin_optimizer" / "current_aware_margin_selected.csv",
        scene.scene_id,
    )
    if selected is None:
        base_layouts = current_replay.representative_layouts(scene)
        ca, _ = current_opt.select_current_aware_plan(scene, base_layouts[METHOD_HYBRID], selection_mc=60)
        plan = ca.plan
    else:
        target_overlap, quantile = selected
        candidate = margin_replay.margin_hybrid_candidate(scene, target_overlap, quantile, seed=0)
        plan = candidate.plan
    plan.method = METHOD_CA
    return plan


def _spacing_ref(positions: np.ndarray, scene: geo.TerrainScene) -> float:
    if len(positions) > 1:
        return float(np.median(np.diff(np.sort(positions))))
    return max(scene.width_m, scene.height_m)


def _shifted_positions(
    positions: np.ndarray,
    context: geo.CrossTrackContext,
    spacing_ref: float,
    bias_frac: float,
    wave_frac: float,
) -> np.ndarray:
    shifted = np.asarray(positions, dtype=float).copy()
    if len(shifted) == 0:
        return shifted
    if len(shifted) > 1 and wave_frac != 0.0:
        phase = np.linspace(-math.pi, math.pi, len(shifted))
        shifted = shifted + wave_frac * spacing_ref * np.sin(phase)
    shifted = shifted + bias_frac * spacing_ref
    return np.sort(np.clip(shifted, context.vmin, context.vmax))


def deterministic_risk_metrics(
    scene: geo.TerrainScene,
    orientation_deg: float,
    positions: np.ndarray,
    *,
    eval_stride: int = 2,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    positions = np.sort(np.asarray(positions, dtype=float))
    spacing_ref = _spacing_ref(positions, scene)
    path_length_km = geo.plan_length_km(scene, positions, math.radians(orientation_deg))
    stress_rows: list[dict[str, Any]] = []
    # Keep route effort in the objective, but make execution feasibility the
    # primary gate. Earlier smoke runs showed that an absolute path-dominated
    # score can choose short layouts with weak adverse-current lower tails.
    score = 0.05 * path_length_km

    if len(positions) > 1:
        min_spacing = float(np.min(np.diff(positions)))
        score += max(0.0, 0.30 * spacing_ref - min_spacing) * 0.05
    else:
        min_spacing = 0.0
        score += 500.0

    coverages: list[float] = []
    overlaps: list[float] = []

    for stress in STRESS_CASES:
        context = geo.make_context(scene, orientation_deg + float(stress["heading_deg"]))
        v_grid = context.v_grid[::eval_stride, ::eval_stride]
        swath_width = context.swath_width[::eval_stride, ::eval_stride] * float(stress["swath_scale"])
        shifted = _shifted_positions(
            positions,
            context,
            spacing_ref,
            float(stress["bias_frac"]),
            float(stress["wave_frac"]),
        )
        coverage, overlap = geo.coverage_and_overlap(v_grid, shifted, swath_width)
        coverages.append(coverage)
        overlaps.append(overlap)
        coverage_deficit = max(0.0, float(stress["coverage_gate"]) - coverage)
        overlap_excess = max(0.0, overlap - float(stress["overlap_gate"]))
        weight = float(stress["weight"])
        score += weight * (coverage_deficit * 360.0 + overlap_excess * 75.0)
        score += weight * max(0.0, geo.TARGET_COVERAGE_PCT - coverage) * 180.0
        score += weight * max(0.0, overlap - 2.25) * 14.0
        stress_rows.append(
            {
                "case": stress["case"],
                "coverage_pct": float(coverage),
                "excess_overlap_pct": float(overlap),
                "coverage_gate": float(stress["coverage_gate"]),
                "overlap_gate": float(stress["overlap_gate"]),
            }
        )

    context_nominal = geo.make_context(scene, orientation_deg)
    nominal_coverage, nominal_overlap = geo.coverage_and_overlap(
        context_nominal.v_grid,
        positions,
        context_nominal.swath_width,
    )
    score += max(0.0, geo.TARGET_COVERAGE_PCT + 1.00 - nominal_coverage) * 280.0
    score += max(0.0, nominal_overlap - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 140.0

    metrics = {
        "deterministic_score": float(score),
        "path_length_km": float(path_length_km),
        "nominal_coverage_pct": float(nominal_coverage),
        "nominal_excess_overlap_pct": float(nominal_overlap),
        "stress_min_coverage_pct": float(np.min(coverages)),
        "stress_p05_proxy_coverage_pct": float(np.percentile(coverages, 5)),
        "stress_max_excess_overlap_pct": float(np.max(overlaps)),
        "stress_p95_proxy_excess_overlap_pct": float(np.percentile(overlaps, 95)),
        "spacing_ref_m": float(spacing_ref),
        "min_spacing_m": float(min_spacing),
    }
    return metrics, stress_rows


def risk_refine_positions(
    scene: geo.TerrainScene,
    base_plan: geo.PlanResult,
    *,
    seed: int,
    generations: int,
    pop_size: int,
) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng(seed)
    base_positions = np.sort(np.asarray(base_plan.line_positions, dtype=float))
    if len(base_positions) < 2:
        metrics, _ = deterministic_risk_metrics(scene, base_plan.orientation_deg, base_positions)
        return base_positions, float(metrics["deterministic_score"])

    context = geo.make_context(scene, base_plan.orientation_deg)
    spacing_ref = _spacing_ref(base_positions, scene)

    def sanitize(values: np.ndarray) -> np.ndarray:
        return np.sort(np.clip(values, context.vmin, context.vmax))

    population: list[np.ndarray] = [base_positions.copy()]
    for _ in range(max(0, pop_size - 1)):
        global_shift = rng.normal(0.0, 0.035 * spacing_ref)
        smooth = np.interp(
            np.linspace(0.0, 1.0, len(base_positions)),
            np.linspace(0.0, 1.0, 4),
            rng.normal(0.0, 0.055 * spacing_ref, size=4),
        )
        jitter = rng.normal(0.0, 0.035 * spacing_ref, size=len(base_positions))
        population.append(sanitize(base_positions + global_shift + smooth + jitter))

    score_cache: dict[tuple[float, ...], float] = {}

    def fitness(positions: np.ndarray) -> float:
        key = tuple(np.round(positions, 3))
        cached = score_cache.get(key)
        if cached is not None:
            return cached
        metrics, _ = deterministic_risk_metrics(scene, base_plan.orientation_deg, positions)
        value = float(metrics["deterministic_score"])
        score_cache[key] = value
        return value

    def tournament_select() -> np.ndarray:
        picks = rng.choice(len(population), size=min(3, len(population)), replace=False)
        return population[min(picks, key=lambda idx: fitness(population[idx]))]

    best = min(population, key=fitness).copy()
    best_fit = fitness(best)
    for generation in range(generations):
        new_population = [best.copy(), base_positions.copy()]
        mutation_scale = (0.050 - 0.018 * generation / max(generations - 1, 1)) * spacing_ref
        while len(new_population) < pop_size:
            parent_a = tournament_select()
            parent_b = tournament_select()
            alpha = rng.uniform(0.20, 0.80)
            child = alpha * parent_a + (1.0 - alpha) * parent_b
            if rng.random() < 0.55:
                child = child + rng.normal(0.0, mutation_scale, size=len(child))
            if rng.random() < 0.35:
                child = child + rng.normal(0.0, 0.020 * spacing_ref)
            if rng.random() < 0.35:
                coarse = rng.normal(0.0, 0.035 * spacing_ref, size=4)
                child = child + np.interp(
                    np.linspace(0.0, 1.0, len(child)),
                    np.linspace(0.0, 1.0, 4),
                    coarse,
                )
            new_population.append(sanitize(child))
        population = new_population
        candidate = min(population, key=fitness)
        candidate_fit = fitness(candidate)
        if candidate_fit < best_fit:
            best = candidate.copy()
            best_fit = candidate_fit

    return best, float(best_fit)


def _candidate_key(plan: geo.PlanResult) -> tuple[Any, ...]:
    return (
        round(float(plan.orientation_deg), 6),
        int(plan.line_count),
        round(float(plan.path_length_km), 4),
        round(float(plan.coverage_pct), 4),
        round(float(plan.excess_overlap_pct), 4),
    )


def seed_candidates(scene: geo.TerrainScene) -> tuple[dict[str, geo.PlanResult], list[CandidateRecord]]:
    base_layouts = current_replay.representative_layouts(scene)
    ca_plan = current_aware_selected_plan(scene)
    base_layouts[METHOD_CA] = ca_plan

    records: list[CandidateRecord] = []
    seen: set[tuple[Any, ...]] = set()

    def add(plan: geo.PlanResult, source: str, target_overlap: float | None, quantile: float | None) -> None:
        key = _candidate_key(plan)
        if key in seen:
            return
        seen.add(key)
        metrics, _ = deterministic_risk_metrics(scene, plan.orientation_deg, plan.line_positions)
        records.append(
            CandidateRecord(
                plan=plan,
                source=source,
                target_overlap=target_overlap,
                quantile=quantile,
                deterministic_score=float(metrics["deterministic_score"]),
                nominal_coverage_pct=float(metrics["nominal_coverage_pct"]),
                nominal_excess_overlap_pct=float(metrics["nominal_excess_overlap_pct"]),
                stress_min_coverage_pct=float(metrics["stress_min_coverage_pct"]),
                stress_max_excess_overlap_pct=float(metrics["stress_max_excess_overlap_pct"]),
            )
        )

    add(base_layouts[METHOD_HYBRID], "hybrid_reference", None, None)
    add(base_layouts[METHOD_UA], "uncertainty_margin_reference", None, None)
    add(ca_plan, "current_margin_reference", None, None)

    for target_overlap in TARGET_OVERLAP_GRID:
        for quantile in QUANTILE_GRID:
            candidate = margin_replay.margin_hybrid_candidate(scene, target_overlap, quantile, seed=0)
            candidate.plan.method = f"risk_seed_{target_overlap:.3f}_{quantile:.2f}"
            add(candidate.plan, "margin_grid", target_overlap, quantile)

    records.sort(key=lambda item: item.deterministic_score)
    return base_layouts, records


def select_execution_risk_plan(
    scene: geo.TerrainScene,
    *,
    refine_top: int,
    generations: int,
    pop_size: int,
) -> tuple[geo.PlanResult, list[dict[str, Any]], list[dict[str, Any]], dict[str, geo.PlanResult]]:
    base_layouts, candidates = seed_candidates(scene)
    candidate_rows: list[dict[str, Any]] = []
    refined_rows: list[dict[str, Any]] = []

    for rank, candidate in enumerate(candidates, start=1):
        candidate_rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_name": scene.display_name,
                "rank": rank,
                "source": candidate.source,
                "target_overlap": candidate.target_overlap,
                "quantile": candidate.quantile,
                "orientation_deg": candidate.plan.orientation_deg,
                "line_count": candidate.plan.line_count,
                "path_length_km": candidate.plan.path_length_km,
                "nominal_coverage_pct": candidate.nominal_coverage_pct,
                "nominal_excess_overlap_pct": candidate.nominal_excess_overlap_pct,
                "stress_min_coverage_pct": candidate.stress_min_coverage_pct,
                "stress_max_excess_overlap_pct": candidate.stress_max_excess_overlap_pct,
                "deterministic_score": candidate.deterministic_score,
            }
        )

    best_plan: geo.PlanResult | None = None
    best_score = float("inf")
    start = time.perf_counter()
    for refine_rank, candidate in enumerate(candidates[:refine_top], start=1):
        refined_positions, refined_score = risk_refine_positions(
            scene,
            candidate.plan,
            seed=20260512 + refine_rank + sum(ord(ch) for ch in scene.scene_id),
            generations=generations,
            pop_size=pop_size,
        )
        refined = geo.evaluate_plan(
            scene,
            METHOD_RISK,
            0,
            candidate.plan.orientation_deg,
            refined_positions,
            time.perf_counter() - start,
        )
        metrics, stress_rows = deterministic_risk_metrics(scene, refined.orientation_deg, refined.line_positions)
        score = float(metrics["deterministic_score"])
        refined_rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_name": scene.display_name,
                "refine_rank": refine_rank,
                "source": candidate.source,
                "target_overlap": candidate.target_overlap,
                "quantile": candidate.quantile,
                "orientation_deg": refined.orientation_deg,
                "line_count": refined.line_count,
                "path_length_km": refined.path_length_km,
                "coverage_pct": refined.coverage_pct,
                "excess_overlap_pct": refined.excess_overlap_pct,
                "feasible": int(refined.feasible),
                "deterministic_score": score,
                "raw_refined_score": refined_score,
                "stress_min_coverage_pct": metrics["stress_min_coverage_pct"],
                "stress_max_excess_overlap_pct": metrics["stress_max_excess_overlap_pct"],
                "stress_rows_json": json.dumps(stress_rows),
            }
        )
        if score < best_score:
            best_plan = refined
            best_score = score

    if best_plan is None:
        raise RuntimeError(f"No execution-risk candidate selected for {scene.scene_id}")

    reference_records = [
        candidate
        for candidate in candidates
        if candidate.source
        in {
            "hybrid_reference",
            "uncertainty_margin_reference",
            "current_margin_reference",
        }
    ]
    best_reference = min(reference_records, key=lambda item: item.deterministic_score)
    best_metrics, _ = deterministic_risk_metrics(scene, best_plan.orientation_deg, best_plan.line_positions)
    improves_score = float(best_metrics["deterministic_score"]) <= best_reference.deterministic_score * 0.995
    preserves_stress_coverage = (
        float(best_metrics["stress_min_coverage_pct"]) >= best_reference.stress_min_coverage_pct - 0.05
    )
    preserves_stress_overlap = (
        float(best_metrics["stress_max_excess_overlap_pct"]) <= best_reference.stress_max_excess_overlap_pct + 0.05
    )
    if not (improves_score and preserves_stress_coverage and preserves_stress_overlap):
        fallback = geo.evaluate_plan(
            scene,
            METHOD_RISK,
            0,
            best_reference.plan.orientation_deg,
            best_reference.plan.line_positions,
            time.perf_counter() - start,
        )
        fallback_metrics, fallback_stress_rows = deterministic_risk_metrics(
            scene,
            fallback.orientation_deg,
            fallback.line_positions,
        )
        refined_rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_name": scene.display_name,
                "refine_rank": "fallback",
                "source": best_reference.source,
                "target_overlap": best_reference.target_overlap,
                "quantile": best_reference.quantile,
                "orientation_deg": fallback.orientation_deg,
                "line_count": fallback.line_count,
                "path_length_km": fallback.path_length_km,
                "coverage_pct": fallback.coverage_pct,
                "excess_overlap_pct": fallback.excess_overlap_pct,
                "feasible": int(fallback.feasible),
                "deterministic_score": fallback_metrics["deterministic_score"],
                "raw_refined_score": best_score,
                "stress_min_coverage_pct": fallback_metrics["stress_min_coverage_pct"],
                "stress_max_excess_overlap_pct": fallback_metrics["stress_max_excess_overlap_pct"],
                "stress_rows_json": json.dumps(fallback_stress_rows),
                "selection_note": "refinement_rejected_by_reference_guard",
            }
        )
        best_plan = fallback

    best_plan.method = METHOD_RISK
    return best_plan, candidate_rows, refined_rows, base_layouts


def summarize_plan(
    scene: geo.TerrainScene,
    plan: geo.PlanResult,
    *,
    final_mc: int,
    fixed_reference: geo.PlanResult,
    hybrid_reference: geo.PlanResult,
) -> list[dict[str, Any]]:
    rows = current_opt.summarize_plan(
        scene,
        plan,
        FINAL_SCENARIOS,
        n_mc=final_mc,
        seed=20260515,
        fixed_reference=fixed_reference,
        hybrid_reference=hybrid_reference,
    )
    for row in rows:
        row["method_label"] = METHOD_LABELS.get(str(row["method"]), str(row["method_label"]))
    return rows


def run_experiment(
    *,
    include_usgs: bool,
    refine_top: int,
    generations: int,
    pop_size: int,
    final_mc: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scenes = current_replay.load_scenes(include_usgs=include_usgs)
    candidate_rows: list[dict[str, Any]] = []
    refined_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for scene in scenes:
        risk_plan, scene_candidate_rows, scene_refined_rows, base_layouts = select_execution_risk_plan(
            scene,
            refine_top=refine_top,
            generations=generations,
            pop_size=pop_size,
        )
        candidate_rows.extend(scene_candidate_rows)
        refined_rows.extend(scene_refined_rows)
        fixed_reference = base_layouts[current_replay.METHOD_FIXED]
        hybrid_reference = base_layouts[METHOD_HYBRID]
        for method in (METHOD_HYBRID, METHOD_UA, METHOD_CA):
            plan = base_layouts[method]
            plan.method = method
            summary_rows.extend(
                summarize_plan(
                    scene,
                    plan,
                    final_mc=final_mc,
                    fixed_reference=fixed_reference,
                    hybrid_reference=hybrid_reference,
                )
            )
        summary_rows.extend(
            summarize_plan(
                scene,
                risk_plan,
                final_mc=final_mc,
                fixed_reference=fixed_reference,
                hybrid_reference=hybrid_reference,
            )
        )
        metrics, _ = deterministic_risk_metrics(scene, risk_plan.orientation_deg, risk_plan.line_positions)
        selected_rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_name": scene.display_name,
                "orientation_deg": risk_plan.orientation_deg,
                "line_count": risk_plan.line_count,
                "path_length_km": risk_plan.path_length_km,
                "coverage_pct": risk_plan.coverage_pct,
                "excess_overlap_pct": risk_plan.excess_overlap_pct,
                "deterministic_score": metrics["deterministic_score"],
                "stress_min_coverage_pct": metrics["stress_min_coverage_pct"],
                "stress_max_excess_overlap_pct": metrics["stress_max_excess_overlap_pct"],
            }
        )

    return summary_rows, candidate_rows, refined_rows, selected_rows


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
    scenario_labels = {str(item["scenario"]): str(item["label"]) for item in current_replay.CURRENT_SCENARIOS}
    lookup = {(row["scene_id"], row["scenario"], row["method"]): row for row in summary_rows}
    row_labels = [
        f"{_short_scene_name(scene_names[scene_id])}\n{scenario_labels[scenario]}"
        for scene_id in scene_order
        for scenario in FINAL_SCENARIOS
    ]

    def matrix(metric: str) -> np.ndarray:
        return np.asarray(
            [
                [float(lookup[(scene_id, scenario, method)][metric]) for method in METHODS]
                for scene_id in scene_order
                for scenario in FINAL_SCENARIOS
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
            "xtick.labelsize": 5.2,
            "ytick.labelsize": 5.2,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    fig = plt.figure(figsize=(7.28, 5.35), facecolor="white")
    grid = fig.add_gridspec(1, 4, width_ratios=[1.0, 1.0, 1.0, 0.90], wspace=0.060)
    fig.text(
        0.032,
        0.985,
        "Execution-risk-aware refinement check",
        ha="left",
        va="top",
        fontsize=8.35,
        fontweight="bold",
        color="#1f2933",
    )
    fig.text(
        0.032,
        0.956,
        "ER-Hybrid injects deterministic current/heading/footprint stress cases into candidate-layout refinement, then all methods are replayed with independent Monte Carlo current draws.",
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
            lambda value: value < 0.95,
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
        for boundary in range(len(FINAL_SCENARIOS), data.shape[0], len(FINAL_SCENARIOS)):
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
        "Bordered cells flag feasibility below 0.95, negative lower-tail coverage margin, P95 overlap above 3%, or path cost above 2%. ER-Hybrid is a numerical risk objective, not field control.",
        ha="left",
        va="bottom",
        fontsize=4.65,
        color="#65717f",
    )
    fig.subplots_adjust(left=0.170, right=0.995, top=0.858, bottom=0.067)

    out_path = OUT / "execution_risk_refinement.png"
    fig.savefig(out_path, dpi=420, bbox_inches="tight", facecolor="white", pad_inches=0.035)
    for pic_dir in PIC_DIRS:
        fig.savefig(pic_dir / "journal_execution_risk_refinement.png", dpi=420, bbox_inches="tight", facecolor="white", pad_inches=0.035)
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]], selected_rows: list[dict[str, Any]]) -> None:
    by_key = {(row["scene_id"], row["scenario"], row["method"]): row for row in summary_rows}
    lines = [
        "# Execution-risk-aware Refinement\n\n",
        "This diagnostic moves part of the current/heading/footprint execution risk into candidate-layout refinement rather than using it only as post-hoc replay.\n\n",
        "ER-Hybrid should be treated as a numerical stress-objective check. It does not model closed-loop control, hydrodynamics, sound-speed uncertainty, or mission logs.\n\n",
        "## Selected Layouts\n\n",
        "| Scene | Heading | Lines | Path km | Nominal coverage | Nominal excess overlap | Stress min coverage | Stress max overlap |\n",
        "|---|---:|---:|---:|---:|---:|---:|---:|\n",
    ]
    for row in selected_rows:
        lines.append(
            f"| {row['scene_name']} | {float(row['orientation_deg']):.1f} | {int(row['line_count'])} | "
            f"{float(row['path_length_km']):.2f} | {float(row['coverage_pct']):.2f} | "
            f"{float(row['excess_overlap_pct']):.2f} | {float(row['stress_min_coverage_pct']):.2f} | "
            f"{float(row['stress_max_excess_overlap_pct']):.2f} |\n"
        )

    lines.extend(
        [
            "\n## Current Replay Summary\n\n",
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

    lines.append("\n## Interpretation\n\n")
    for scene_id in sorted({str(row["scene_id"]) for row in summary_rows}):
        scene_name = next(row["scene_name"] for row in summary_rows if row["scene_id"] == scene_id)
        adverse_hybrid = by_key[(scene_id, "adverse_current", METHOD_HYBRID)]
        adverse_risk = by_key[(scene_id, "adverse_current", METHOD_RISK)]
        delta_feasible = float(adverse_risk["feasible_rate"]) - float(adverse_hybrid["feasible_rate"])
        delta_overlap = float(adverse_risk["excess_overlap_pct_p95"]) - float(adverse_hybrid["excess_overlap_pct_p95"])
        delta_cost = float(adverse_risk["path_cost_vs_hybrid_pct"])
        lines.append(
            f"- {scene_name}: adverse-current feasible-rate change versus Hybrid is {delta_feasible:+.3f}, "
            f"P95 overlap change is {delta_overlap:+.2f} percentage points, and path-cost change is {delta_cost:+.2f} percent.\n"
        )
    lines.append(
        "\nManuscript decision rule: promote ER-Hybrid only if it improves adverse-current feasibility or lower-tail coverage without violating the 3 percent overlap gate or adding more than 2 percent path cost. Otherwise retain it as supplemental negative/boundary evidence that true execution-aware planning needs controller or mission-log data.\n"
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refine-top", type=int, default=4)
    parser.add_argument("--generations", type=int, default=14)
    parser.add_argument("--pop-size", type=int, default=14)
    parser.add_argument("--final-mc", type=int, default=300)
    parser.add_argument("--skip-usgs", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    summary_rows, candidate_rows, refined_rows, selected_rows = run_experiment(
        include_usgs=not args.skip_usgs,
        refine_top=args.refine_top,
        generations=args.generations,
        pop_size=args.pop_size,
        final_mc=args.final_mc,
    )
    write_csv(OUT / "execution_risk_candidates.csv", candidate_rows)
    write_csv(OUT / "execution_risk_refined_candidates.csv", refined_rows)
    write_csv(OUT / "execution_risk_selected.csv", selected_rows)
    write_csv(OUT / "execution_risk_summary.csv", summary_rows)
    (OUT / "execution_risk_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
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
        if row["method"] in {METHOD_HYBRID, METHOD_UA, METHOD_CA, METHOD_RISK}
    ]
    print(json.dumps({"out_dir": str(OUT), "comparison": compact}, indent=2))


if __name__ == "__main__":
    main()
