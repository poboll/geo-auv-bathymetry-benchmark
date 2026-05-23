from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm

import geo_public_bathy_benchmark as geo
import make_structured_prior_error_replay as prior_replay
import make_uncertainty_margin_replay as margin_replay
import make_uncertainty_replay as uncertainty


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "current_drift_replay"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)
SELECTED_MARGIN_CSV = ROOT / "uncertainty_margin_replay" / "uncertainty_margin_selected.csv"

METHOD_FIXED = "Fixed-Spacing"
METHOD_HYBRID = "Full Geometry-Aware Hybrid GA"
METHOD_UA = "Current/Uncertainty-Margin Hybrid"
METHODS = (METHOD_FIXED, METHOD_HYBRID, METHOD_UA)
METHOD_LABELS = {
    METHOD_FIXED: "Fixed",
    METHOD_HYBRID: "Hybrid",
    METHOD_UA: "UA-Hybrid",
}

SURVEY_SPEED_MPS = 1.5
CURRENT_SCENARIOS = (
    {
        "scenario": "mild_current",
        "label": "Mild",
        "current_speed_mps": 0.05,
        "controller_residual_gain": 0.55,
        "heading_base_sigma_deg": 0.20,
        "n_mc": 240,
    },
    {
        "scenario": "cross_current",
        "label": "Cross",
        "current_speed_mps": 0.15,
        "controller_residual_gain": 0.70,
        "heading_base_sigma_deg": 0.35,
        "n_mc": 300,
    },
    {
        "scenario": "adverse_current",
        "label": "Adverse",
        "current_speed_mps": 0.30,
        "controller_residual_gain": 0.85,
        "heading_base_sigma_deg": 0.50,
        "n_mc": 300,
    },
)


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


def load_scenes(include_usgs: bool) -> list[geo.TerrainScene]:
    scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    if include_usgs:
        usgs = prior_replay.load_usgs_high_scene()
        if usgs is not None:
            scenes.append(usgs)
    return scenes


def _selected_margin_lookup() -> dict[str, dict[str, float]]:
    if not SELECTED_MARGIN_CSV.exists():
        return {}
    rows: dict[str, dict[str, float]] = {}
    with SELECTED_MARGIN_CSV.open("r", newline="", encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            rows[str(row["scene_id"])] = {
                "target_overlap": float(row["selected_target_overlap"]),
                "quantile": float(row["selected_quantile"]),
            }
    return rows


def representative_layouts(scene: geo.TerrainScene) -> dict[str, geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed=0)

    selected = _selected_margin_lookup().get(scene.scene_id)
    if selected is None:
        ua = hybrid
    else:
        ua_candidate = margin_replay.margin_hybrid_candidate(
            scene,
            target_overlap=selected["target_overlap"],
            quantile=selected["quantile"],
            seed=0,
        )
        ua = ua_candidate.plan
        ua.method = METHOD_UA

    return {
        METHOD_FIXED: fixed,
        METHOD_HYBRID: hybrid,
        METHOD_UA: ua,
    }


def _current_cross_component(
    plan_orientation_deg: float,
    current_direction_deg: float,
    current_speed_mps: float,
) -> float:
    # The survey line is axial; the sine term approximates the component that
    # pushes the vehicle across the planned line family.
    return current_speed_mps * math.sin(math.radians(current_direction_deg - plan_orientation_deg))


def evaluate_current_drift(
    scene: geo.TerrainScene,
    plan: geo.PlanResult,
    scenario: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[float, float, int, dict[str, float]]:
    positions = np.asarray(plan.line_positions, dtype=float)
    spacing_ref = float(np.median(np.diff(positions))) if len(positions) > 1 else max(scene.width_m, scene.height_m)
    current_direction_deg = float(rng.uniform(0.0, 180.0))
    cross_component = _current_cross_component(
        plan.orientation_deg,
        current_direction_deg,
        float(scenario["current_speed_mps"]),
    )
    residual_ratio = abs(cross_component) / max(SURVEY_SPEED_MPS, 1e-9) * float(
        scenario["controller_residual_gain"]
    )
    residual_frac = float(np.clip(residual_ratio, 0.0, 0.20))
    heading_sigma = float(scenario["heading_base_sigma_deg"]) + residual_frac * 4.6
    heading_error = float(rng.normal(0.0, heading_sigma))
    context = geo.make_context(scene, plan.orientation_deg + heading_error)

    shifted = positions.copy()
    if len(shifted):
        global_bias = rng.normal(0.0, 0.45 * residual_frac * spacing_ref)
        line_field = uncertainty.low_frequency_vector(len(shifted), rng, 0.70 * residual_frac * spacing_ref)
        independent = rng.normal(0.0, 0.35 * residual_frac * spacing_ref, size=len(shifted))
        shifted = np.sort(np.clip(shifted + global_bias + line_field + independent, context.vmin, context.vmax))

    local_scale = 1.0 + uncertainty.low_frequency_noise(context.swath_width.shape, rng, 0.35 * residual_frac)
    terrain_shrink = 1.0 - abs(rng.normal(0.0, 0.42 * residual_frac)) * uncertainty.terrain_difficulty_weight(scene)
    global_scale = 1.0 + rng.normal(0.0, 0.24 * residual_frac)
    scale = np.clip(global_scale * local_scale * terrain_shrink, 0.68, 1.18)
    coverage, overlap = geo.coverage_and_overlap(context.v_grid, shifted, context.swath_width * scale)
    feasible = int(coverage >= geo.TARGET_COVERAGE_PCT and overlap <= geo.EXCESS_OVERLAP_FEASIBLE_PCT)
    meta = {
        "current_direction_deg": current_direction_deg,
        "cross_current_component_mps": cross_component,
        "residual_drift_frac_of_spacing": residual_frac,
        "heading_error_deg": heading_error,
        "heading_sigma_deg": heading_sigma,
        "global_swath_scale": float(global_scale),
        "spacing_ref_m": spacing_ref,
    }
    return coverage, overlap, feasible, meta


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


def run_experiment(include_usgs: bool, n_mc_override: int | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    scenes = load_scenes(include_usgs=include_usgs)

    for scene in scenes:
        layouts = representative_layouts(scene)
        hybrid_ref = layouts[METHOD_HYBRID]
        fixed_ref = layouts[METHOD_FIXED]
        for method in METHODS:
            plan = layouts[method]
            for scenario in CURRENT_SCENARIOS:
                n_mc = int(n_mc_override or scenario["n_mc"])
                # Use common random numbers across methods for each scene and
                # current scenario. This prevents nominally identical or very
                # similar layouts from appearing different because the Monte
                # Carlo current directions/noise fields changed with the label.
                rng = np.random.default_rng(
                    20260511
                    + sum(ord(ch) for ch in scene.scene_id + str(scenario["scenario"]))
                )
                coverage_vals: list[float] = []
                overlap_vals: list[float] = []
                feasible_vals: list[int] = []
                residual_vals: list[float] = []
                cross_vals: list[float] = []
                for trial in range(n_mc):
                    coverage, overlap, feasible, meta = evaluate_current_drift(scene, plan, scenario, rng)
                    coverage_vals.append(coverage)
                    overlap_vals.append(overlap)
                    feasible_vals.append(feasible)
                    residual_vals.append(float(meta["residual_drift_frac_of_spacing"]))
                    cross_vals.append(abs(float(meta["cross_current_component_mps"])))
                    raw_rows.append(
                        {
                            "scene_id": scene.scene_id,
                            "scene_name": scene.display_name,
                            "method": method,
                            "method_label": METHOD_LABELS[method],
                            "scenario": scenario["scenario"],
                            "trial": trial,
                            "current_speed_mps": float(scenario["current_speed_mps"]),
                            "controller_residual_gain": float(scenario["controller_residual_gain"]),
                            "coverage_pct": coverage,
                            "excess_overlap_pct": overlap,
                            "feasible": feasible,
                            "orientation_deg_nominal": plan.orientation_deg,
                            "line_count": plan.line_count,
                            "path_length_km": plan.path_length_km,
                            **meta,
                        }
                    )

                cov = summarize(np.asarray(coverage_vals, dtype=float))
                ov = summarize(np.asarray(overlap_vals, dtype=float))
                residual = summarize(np.asarray(residual_vals, dtype=float))
                cross = summarize(np.asarray(cross_vals, dtype=float))
                path_cost_vs_hybrid = (
                    (plan.path_length_km - hybrid_ref.path_length_km) / hybrid_ref.path_length_km * 100.0
                    if hybrid_ref.path_length_km > 0
                    else np.nan
                )
                path_gain_vs_fixed = (
                    (fixed_ref.path_length_km - plan.path_length_km) / fixed_ref.path_length_km * 100.0
                    if fixed_ref.path_length_km > 0
                    else np.nan
                )
                summary_rows.append(
                    {
                        "scene_id": scene.scene_id,
                        "scene_name": scene.display_name,
                        "method": method,
                        "method_label": METHOD_LABELS[method],
                        "scenario": scenario["scenario"],
                        "scenario_label": scenario["label"],
                        "n_mc": n_mc,
                        "current_speed_mps": float(scenario["current_speed_mps"]),
                        "controller_residual_gain": float(scenario["controller_residual_gain"]),
                        "orientation_deg_nominal": plan.orientation_deg,
                        "line_count": plan.line_count,
                        "path_length_km": plan.path_length_km,
                        "path_cost_vs_hybrid_pct": path_cost_vs_hybrid,
                        "path_gain_vs_fixed_pct": path_gain_vs_fixed,
                        "nominal_coverage_pct": plan.coverage_pct,
                        "nominal_excess_overlap_pct": plan.excess_overlap_pct,
                        "coverage_pct_mean": cov["mean"],
                        "coverage_pct_std": cov["std"],
                        "coverage_pct_p05": cov["p05"],
                        "coverage_pct_p50": cov["p50"],
                        "coverage_pct_p95": cov["p95"],
                        "coverage_pct_min": cov["min"],
                        "excess_overlap_pct_mean": ov["mean"],
                        "excess_overlap_pct_std": ov["std"],
                        "excess_overlap_pct_p05": ov["p05"],
                        "excess_overlap_pct_p50": ov["p50"],
                        "excess_overlap_pct_p95": ov["p95"],
                        "excess_overlap_pct_max": ov["max"],
                        "feasible_rate": float(np.mean(feasible_vals)),
                        "residual_drift_frac_mean": residual["mean"],
                        "residual_drift_frac_p95": residual["p95"],
                        "abs_cross_current_component_mps_mean": cross["mean"],
                        "abs_cross_current_component_mps_p95": cross["p95"],
                    }
                )
    return raw_rows, summary_rows


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
    scenario_order = [str(item["scenario"]) for item in CURRENT_SCENARIOS]
    scenario_labels = {str(item["scenario"]): str(item["label"]) for item in CURRENT_SCENARIOS}
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
    residual_tail = matrix("residual_drift_frac_p95") * 100.0

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 6.35,
            "axes.titlesize": 7.0,
            "axes.labelsize": 6.0,
            "xtick.labelsize": 5.45,
            "ytick.labelsize": 5.30,
            "axes.linewidth": 0.45,
            "savefig.dpi": 420,
        }
    )
    fig = plt.figure(figsize=(7.28, 4.75), facecolor="white")
    grid = fig.add_gridspec(1, 4, width_ratios=[1.0, 1.0, 1.0, 0.88], wspace=0.065)
    fig.text(
        0.032,
        0.985,
        "Current-drift replay of fixed-line MBES layouts",
        ha="left",
        va="top",
        fontsize=8.4,
        fontweight="bold",
        color="#1f2933",
    )
    fig.text(
        0.032,
        0.956,
        "A first-order execution proxy converts mild, cross, and adverse currents into residual cross-track line drift, heading perturbation, and terrain-coupled footprint shrinkage; values are replayed on the same public-grid evaluator.",
        ha="left",
        va="top",
        fontsize=4.65,
        color="#65717f",
    )

    panels = [
        (
            "Feasible rate",
            feasible,
            LinearSegmentedColormap.from_list("feas", ["#e8b4a4", "#fbfcfb", "#b8ded8", "#0b736d"]),
            Normalize(vmin=0.0, vmax=1.0),
            "{:.2f}",
            lambda value: value < 1.0,
        ),
        (
            "P05 coverage margin (pp)",
            coverage_margin,
            LinearSegmentedColormap.from_list("cov", ["#b84a3a", "#fbfcfb", "#a8dcd5", "#08766e"]),
            TwoSlopeNorm(vmin=min(float(np.min(coverage_margin)), -4.0), vcenter=0.0, vmax=max(float(np.max(coverage_margin)), 3.0)),
            "{:+.2f}",
            lambda value: value < 0.0,
        ),
        (
            "P95 excess overlap (%)",
            overlap_tail,
            LinearSegmentedColormap.from_list("ov", ["#fbfcfb", "#f0d4c2", "#c8644e", "#6e2e24"]),
            Normalize(vmin=0.0, vmax=max(float(np.max(overlap_tail)), geo.EXCESS_OVERLAP_FEASIBLE_PCT)),
            "{:.2f}",
            lambda value: value > geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        ),
        (
            "P95 residual drift (% spacing)",
            residual_tail,
            LinearSegmentedColormap.from_list("drift", ["#fbfcfb", "#d4e7e7", "#7baeb9", "#235e76"]),
            Normalize(vmin=0.0, vmax=max(float(np.max(residual_tail)), 1.0)),
            "{:.1f}",
            lambda value: value > 10.0,
        ),
    ]

    for panel_idx, (title, data, cmap, norm, fmt, mark_bad) in enumerate(panels):
        ax = fig.add_subplot(grid[0, panel_idx])
        im = ax.imshow(data, aspect="equal", cmap=cmap, norm=norm)
        ax.set_title(title, fontweight="bold", color="#1f2933", pad=3.0)
        ax.set_xticks(np.arange(len(METHODS)))
        ax.set_xticklabels([METHOD_LABELS[method] for method in METHODS], rotation=34, ha="left")
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
                    fontsize=4.8,
                    color="white" if luminance < 0.42 else "#263440",
                )
                if mark_bad(value):
                    ax.add_patch(
                        plt.Rectangle((j - 0.48, i - 0.48), 0.96, 0.96, fill=False, lw=0.70, ec="#6e2e24")
                    )

    fig.text(
        0.032,
        0.026,
        "This replay is an execution-risk diagnostic, not a hydrodynamic simulator or sea trial. Bordered cells flag feasibility loss, negative P05 coverage margin, P95 overlap above the 3% gate, or large residual drift.",
        ha="left",
        va="bottom",
        fontsize=4.65,
        color="#65717f",
    )
    fig.subplots_adjust(left=0.170, right=0.995, top=0.830, bottom=0.090)

    out_path = OUT / "current_drift_replay.png"
    fig.savefig(out_path, dpi=420, bbox_inches="tight", facecolor="white", pad_inches=0.035)
    for pic_dir in PIC_DIRS:
        fig.savefig(pic_dir / "journal_current_drift_replay.png", dpi=420, bbox_inches="tight", facecolor="white", pad_inches=0.035)
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Current-drift Replay\n\n",
        "This diagnostic asks whether the fixed-line layouts retain coverage and overlap margin when a first-order current proxy is injected after planning.\n\n",
        "The proxy does not claim hydrodynamic simulation. It maps current speed and direction into residual cross-track line drift, heading perturbation, low-frequency footprint variation, and terrain-coupled footprint shrinkage, then recomputes the same coverage and overlap metrics on the benchmark evaluator. For fair method comparison, each scene/scenario uses common random numbers across methods.\n\n",
        "| Scene | Scenario | Method | Feasible | P05 coverage margin pp | P95 excess overlap | P95 residual drift (% spacing) |\n",
        "|---|---|---:|---:|---:|---:|---:|\n",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['scene_name']} | {row['scenario_label']} | {row['method_label']} | "
            f"{float(row['feasible_rate']):.2f} | "
            f"{float(row['coverage_pct_p05']) - geo.TARGET_COVERAGE_PCT:+.2f} | "
            f"{float(row['excess_overlap_pct_p95']):.2f} | "
            f"{100.0 * float(row['residual_drift_frac_p95']):.1f} |\n"
        )
    lines.append(
        "\nInterpretation: if the adverse-current cells remain bordered, the correct manuscript claim is not that the planner is field-ready. It is that the fixed-line geometry needs a current/controller-aware execution layer before operational deployment.\n"
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-usgs", action="store_true")
    parser.add_argument("--n-mc", type=int, default=None)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    raw_rows, summary_rows = run_experiment(include_usgs=not args.skip_usgs, n_mc_override=args.n_mc)
    write_csv(OUT / "current_drift_raw.csv", raw_rows)
    write_csv(OUT / "current_drift_summary.csv", summary_rows)
    (OUT / "current_drift_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    make_figure(summary_rows)
    write_report(summary_rows)
    compact = [
        {
            "scene": row["scene_name"],
            "scenario": row["scenario_label"],
            "method": row["method_label"],
            "feasible": round(float(row["feasible_rate"]), 3),
            "p05_cov_margin": round(float(row["coverage_pct_p05"]) - geo.TARGET_COVERAGE_PCT, 3),
            "p95_overlap": round(float(row["excess_overlap_pct_p95"]), 3),
        }
        for row in summary_rows
        if row["method"] in {METHOD_HYBRID, METHOD_UA}
    ]
    print(json.dumps({"out_dir": str(OUT), "comparison": compact}, indent=2))


if __name__ == "__main__":
    main()
