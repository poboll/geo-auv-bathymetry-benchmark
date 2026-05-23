from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import Normalize, TwoSlopeNorm
from PIL import Image

import geo_public_bathy_benchmark as geo
import journal_heatmap_style as jhs
import make_survey_grade_extension as usgs_extension
import make_survey_grade_pilot as usgs_pilot


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "structured_prior_error_replay"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

METHODS = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
)
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adapt.",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
}

SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "scenario": "nominal",
        "label": "Nominal",
        "base_sigma_m": 0.0,
        "slope_sigma_m": 0.0,
        "hotspot_amp_m": 0.0,
        "hotspots": 0,
        "description": "Truth grid used as the planning prior.",
    },
    {
        "scenario": "correlated_bias",
        "label": "Correlated bias",
        "base_sigma_m": 35.0,
        "slope_sigma_m": 0.0,
        "hotspot_amp_m": 0.0,
        "hotspots": 0,
        "description": "Low-frequency spatially correlated bathymetric bias with 35 m RMS target scale.",
    },
    {
        "scenario": "slope_amplified",
        "label": "Slope amplified",
        "base_sigma_m": 18.0,
        "slope_sigma_m": 55.0,
        "hotspot_amp_m": 0.0,
        "hotspots": 0,
        "description": "Correlated map error amplified on high-gradient seabed cells.",
    },
    {
        "scenario": "canyon_wall_bias",
        "label": "Local wall bias",
        "base_sigma_m": 15.0,
        "slope_sigma_m": 35.0,
        "hotspot_amp_m": 90.0,
        "hotspots": 2,
        "description": "Correlated prior error with localized high-slope canyon-wall perturbations.",
    },
)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def resample_noise(shape: tuple[int, int], rng: np.random.Generator, coarse: tuple[int, int]) -> np.ndarray:
    """Generate a smooth zero-mean, unit-variance field on the target grid."""
    coarse_h, coarse_w = coarse
    values = rng.normal(0.0, 1.0, size=(coarse_h, coarse_w))
    scaled = ((values - values.min()) / max(float(values.max() - values.min()), 1e-9) * 255.0).astype("uint8")
    image = Image.fromarray(scaled, mode="L").resize((shape[1], shape[0]), resample=Image.Resampling.BICUBIC)
    field = np.asarray(image, dtype=float) / 255.0
    field = field - float(np.mean(field))
    return field / max(float(np.std(field)), 1e-9)


def slope_weight(scene: geo.TerrainScene) -> np.ndarray:
    dy = float(np.abs(scene.y[1, 0] - scene.y[0, 0])) if scene.y.shape[0] > 1 else 1.0
    dx = float(np.abs(scene.x[0, 1] - scene.x[0, 0])) if scene.x.shape[1] > 1 else 1.0
    gy, gx = np.gradient(scene.z, dy, dx)
    slope = np.hypot(gx, gy)
    ref = max(float(np.nanpercentile(slope, 95)), 1e-9)
    return np.clip(slope / ref, 0.0, 1.0)


def localized_hotspot_field(
    scene: geo.TerrainScene,
    rng: np.random.Generator,
    slope: np.ndarray,
    *,
    hotspot_count: int,
    amp_m: float,
) -> np.ndarray:
    if hotspot_count <= 0 or amp_m <= 0:
        return np.zeros_like(scene.z, dtype=float)

    h, w = scene.z.shape
    candidates = np.argwhere(slope >= np.nanpercentile(slope, 90))
    if len(candidates) == 0:
        candidates = np.argwhere(np.ones_like(slope, dtype=bool))

    yy, xx = np.mgrid[0:h, 0:w]
    field = np.zeros((h, w), dtype=float)
    for _ in range(hotspot_count):
        cy, cx = candidates[int(rng.integers(0, len(candidates)))]
        sy = max(h * float(rng.uniform(0.07, 0.14)), 3.0)
        sx = max(w * float(rng.uniform(0.07, 0.16)), 3.0)
        sign = -1.0 if rng.random() < 0.5 else 1.0
        blob = np.exp(-0.5 * (((yy - cy) / sy) ** 2 + ((xx - cx) / sx) ** 2))
        field += sign * amp_m * blob * (0.35 + 0.65 * slope)
    return field


def make_prior_scene(
    truth: geo.TerrainScene,
    scenario: dict[str, Any],
    rng: np.random.Generator,
    seed: int,
) -> tuple[geo.TerrainScene, dict[str, float]]:
    base_sigma = float(scenario["base_sigma_m"])
    slope_sigma = float(scenario["slope_sigma_m"])
    hotspot_amp = float(scenario["hotspot_amp_m"])
    hotspots = int(scenario["hotspots"])

    slope = slope_weight(truth)
    shape = truth.z.shape
    coarse = (min(18, max(5, shape[0] // 8)), min(18, max(5, shape[1] // 8)))
    base = resample_noise(shape, rng, coarse) * base_sigma
    slope_error = resample_noise(shape, rng, coarse) * slope_sigma * (0.25 + 0.75 * slope)
    hotspot = localized_hotspot_field(truth, rng, slope, hotspot_count=hotspots, amp_m=hotspot_amp)
    error = base + slope_error + hotspot

    if str(scenario["scenario"]) == "nominal":
        error = np.zeros_like(truth.z, dtype=float)

    prior_z = np.clip(truth.z + error, 1.0, None)
    rmse = float(np.sqrt(np.mean((prior_z - truth.z) ** 2)))
    mae = float(np.mean(np.abs(prior_z - truth.z)))
    p95 = float(np.percentile(np.abs(prior_z - truth.z), 95))

    manifest = dict(truth.manifest_entry)
    manifest.update(
        {
            "scene_id": f"{truth.scene_id}_prior_error_{scenario['scenario']}_seed{seed}",
            "prior_error_scenario": scenario["scenario"],
            "prior_error_description": scenario["description"],
            "prior_error_seed": seed,
            "prior_error_rmse_m": rmse,
            "prior_error_mae_m": mae,
            "prior_error_abs_p95_m": p95,
            "prior_error_policy": "Plan on a spatially perturbed prior and replay the same line family on the truth grid.",
        }
    )
    prior = geo.TerrainScene(
        scene_id=str(manifest["scene_id"]),
        display_name=f"{truth.display_name} {scenario['label']} Prior",
        scene_group=truth.scene_group,
        terrain_class=truth.terrain_class,
        x=truth.x.copy(),
        y=truth.y.copy(),
        z=prior_z,
        source=truth.source,
        download_url=truth.download_url,
        raw_file=truth.raw_file,
        manifest_entry=manifest,
    )
    return prior, {"prior_rmse_m": rmse, "prior_mae_m": mae, "prior_abs_p95_m": p95}


def load_usgs_high_scene() -> geo.TerrainScene | None:
    try:
        usgs_pilot.ensure_extracted()
        with rasterio.open(usgs_pilot.RASTER_PATH) as dataset:
            candidates = usgs_extension.enumerate_candidate_windows(dataset)
            if not candidates:
                return None
            idx = int(round(0.80 * (len(candidates) - 1)))
            _, window, metrics = candidates[idx]
            metrics = dict(metrics)
            metrics["requested_complexity_quantile"] = 0.80
            return usgs_extension.scene_from_window(dataset, "high", window, metrics)
    except Exception as exc:  # pragma: no cover - this is a data-availability guard.
        print(f"[structured-prior] skipping USGS high scene: {exc}", flush=True)
        return None


def load_scenes(include_usgs: bool) -> list[geo.TerrainScene]:
    scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    if include_usgs:
        usgs = load_usgs_high_scene()
        if usgs is not None:
            scenes.append(usgs)
    return scenes


def plan_methods(prior: geo.TerrainScene, seed: int) -> list[geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(prior)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(prior)
    hybrid = geo.full_geometry_aware_hybrid_ga_plan(prior, adaptive_base, seed=seed)
    return [fixed, adaptive, hybrid]


def run_replay(seed_count: int, include_usgs: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scenes = load_scenes(include_usgs)
    raw_rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []

    for scene in scenes:
        truth_fixed = geo.fixed_spacing_plan(scene)
        truth_adaptive, truth_adaptive_base = geo.adaptive_spacing_plan(scene)
        truth_hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, truth_adaptive_base, seed=0)
        truth_refs = {
            "Fixed-Spacing": truth_fixed,
            "Adaptive Spacing w/o GA": truth_adaptive,
            "Full Geometry-Aware Hybrid GA": truth_hybrid,
        }

        for scenario in SCENARIOS:
            for seed in range(seed_count):
                rng_seed = 20260511 + seed * 101 + sum(ord(ch) for ch in scene.scene_id + str(scenario["scenario"]))
                rng = np.random.default_rng(rng_seed)
                prior, error_stats = make_prior_scene(scene, scenario, rng, seed)
                if seed == 0:
                    manifests.append(prior.manifest_entry)
                plans = plan_methods(prior, seed)
                for planned in plans:
                    replayed = geo.evaluate_plan(
                        scene,
                        planned.method,
                        seed,
                        planned.orientation_deg,
                        planned.line_positions,
                        planned.planning_time_s,
                    )
                    truth_ref = truth_refs[planned.method]
                    raw_rows.append(
                        {
                            "scene_id": scene.scene_id,
                            "scene_name": scene.display_name,
                            "scenario": str(scenario["scenario"]),
                            "scenario_label": str(scenario["label"]),
                            "method": planned.method,
                            "method_label": METHOD_LABELS[planned.method],
                            "seed": seed,
                            "orientation_deg": float(planned.orientation_deg),
                            "line_count": int(planned.line_count),
                            "prior_rmse_m": error_stats["prior_rmse_m"],
                            "prior_mae_m": error_stats["prior_mae_m"],
                            "prior_abs_p95_m": error_stats["prior_abs_p95_m"],
                            "planned_path_length_km": float(planned.path_length_km),
                            "replay_path_length_km": float(replayed.path_length_km),
                            "path_gain_vs_truth_fixed_pct": float(
                                (truth_fixed.path_length_km - replayed.path_length_km) / truth_fixed.path_length_km * 100.0
                            ),
                            "planned_coverage_pct": float(planned.coverage_pct),
                            "replay_coverage_pct": float(replayed.coverage_pct),
                            "coverage_loss_pp": float(planned.coverage_pct - replayed.coverage_pct),
                            "truth_nominal_method_coverage_pct": float(truth_ref.coverage_pct),
                            "planned_excess_overlap_pct": float(planned.excess_overlap_pct),
                            "replay_excess_overlap_pct": float(replayed.excess_overlap_pct),
                            "overlap_increase_pp": float(replayed.excess_overlap_pct - planned.excess_overlap_pct),
                            "truth_nominal_method_excess_overlap_pct": float(truth_ref.excess_overlap_pct),
                            "planned_feasible": int(planned.feasible),
                            "replay_feasible": int(replayed.feasible),
                            "truth_nominal_method_feasible": int(truth_ref.feasible),
                            "planning_time_s": float(planned.planning_time_s),
                        }
                    )

    return raw_rows, summarize(raw_rows), manifests


def summarize(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        grouped[(str(row["scene_id"]), str(row["scenario"]), str(row["method"]))].append(row)

    summary_rows: list[dict[str, Any]] = []
    order = {str(item["scenario"]): idx for idx, item in enumerate(SCENARIOS)}
    for (scene_id, scenario, method), rows in sorted(
        grouped.items(), key=lambda item: (item[1][0]["scene_name"], order[item[0][1]], METHODS.index(item[0][2]))
    ):
        out: dict[str, Any] = {
            "scene_id": scene_id,
            "scene_name": rows[0]["scene_name"],
            "scenario": scenario,
            "scenario_label": rows[0]["scenario_label"],
            "method": method,
            "method_label": METHOD_LABELS[method],
            "n_runs": len(rows),
        }
        for key in (
            "orientation_deg",
            "line_count",
            "prior_rmse_m",
            "prior_mae_m",
            "prior_abs_p95_m",
            "planned_path_length_km",
            "replay_path_length_km",
            "path_gain_vs_truth_fixed_pct",
            "planned_coverage_pct",
            "replay_coverage_pct",
            "coverage_loss_pp",
            "planned_excess_overlap_pct",
            "replay_excess_overlap_pct",
            "overlap_increase_pp",
            "planned_feasible",
            "replay_feasible",
            "planning_time_s",
        ):
            values = np.asarray([float(row[key]) for row in rows], dtype=float)
            out[f"{key}_mean"] = float(values.mean())
            out[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            out[f"{key}_min"] = float(values.min())
            out[f"{key}_max"] = float(values.max())
        summary_rows.append(out)
    return summary_rows


def metric_matrix(
    summary_rows: list[dict[str, Any]],
    scene_order: list[str],
    scenario_order: list[str],
    metric: str,
) -> np.ndarray:
    rows = []
    lookup = {(row["scene_id"], row["scenario"], row["method"]): row for row in summary_rows}
    for scene_id in scene_order:
        for scenario in scenario_order:
            rows.append([float(lookup[(scene_id, scenario, method)][metric]) for method in METHODS])
    return np.asarray(rows, dtype=float)


def make_figure(summary_rows: list[dict[str, Any]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for directory in PIC_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

    scene_order = list(dict.fromkeys(str(row["scene_id"]) for row in summary_rows))
    scene_names = {str(row["scene_id"]): str(row["scene_name"]) for row in summary_rows}
    scenario_order = [str(item["scenario"]) for item in SCENARIOS]
    scenario_labels = {str(item["scenario"]): str(item["label"]) for item in SCENARIOS}

    scene_short_labels = {
        "gebco_cascadia_margin_moderate": "Casc.",
        "gebco_monterey_canyon_complex": "Mont.",
        "usgs_southern_cascadia_30m_high": "USGS-H",
    }
    scenario_short_labels = {
        "nominal": "Nom.",
        "correlated_bias": "Corr.",
        "slope_amplified": "Slope",
        "canyon_wall_bias": "Wall",
    }
    row_labels = []
    for scene_id in scene_order:
        for scenario in scenario_order:
            row_labels.append(
                f"{scene_short_labels.get(scene_id, scene_names[scene_id])} {scenario_short_labels.get(scenario, scenario_labels[scenario])}"
            )

    feasible = metric_matrix(summary_rows, scene_order, scenario_order, "replay_feasible_mean")
    coverage_margin = metric_matrix(summary_rows, scene_order, scenario_order, "replay_coverage_pct_mean") - geo.TARGET_COVERAGE_PCT
    overlap = metric_matrix(summary_rows, scene_order, scenario_order, "replay_excess_overlap_pct_mean")
    path_gain = metric_matrix(summary_rows, scene_order, scenario_order, "path_gain_vs_truth_fixed_pct_mean")

    jhs.apply_rc(base_font=8.10)
    fig = plt.figure(figsize=(7.25, 3.95), facecolor=jhs.BG)
    grid = fig.add_gridspec(2, 2, wspace=0.08, hspace=0.20)
    panels = [
        ("(a) Replay feasible rate", feasible, jhs.COVERAGE_CMAP, Normalize(vmin=0.0, vmax=1.0), "{:.2f}", lambda value: value < 1.0),
        (
            "(b) Coverage margin (pp)",
            coverage_margin,
            jhs.COVERAGE_CMAP,
            TwoSlopeNorm(vmin=min(float(np.min(coverage_margin)), -1.0), vcenter=0.0, vmax=max(float(np.max(coverage_margin)), 1.0)),
            "{:+.2f}",
            lambda value: value < 0.0,
        ),
        (
            "(c) Excess-overlap violation (%)",
            overlap,
            jhs.OVERLAP_CMAP,
            Normalize(vmin=0.0, vmax=max(float(np.max(overlap)), geo.EXCESS_OVERLAP_FEASIBLE_PCT)),
            "{:.2f}",
            lambda value: value > geo.EXCESS_OVERLAP_FEASIBLE_PCT,
        ),
        (
            "(d) Path gain vs Fixed (%)",
            path_gain,
            jhs.PATH_GAIN_CMAP,
            Normalize(vmin=min(0.0, float(np.min(path_gain))), vmax=max(1.0, float(np.max(path_gain)))),
            "{:.1f}",
            None,
        ),
    ]

    col_labels = [METHOD_LABELS[method] for method in METHODS]
    for panel_idx, (title, data, cmap, norm, fmt, mark_bad) in enumerate(panels):
        ax = fig.add_subplot(grid[panel_idx // 2, panel_idx % 2])
        ax.imshow(data, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        jhs.style_heatmap_axis(
            ax,
            title,
            col_labels,
            row_labels if panel_idx in (0, 2) else None,
            data.shape[0],
            group_every=len(scenario_order),
        )
        jhs.annotate_cells(ax, data, cmap, norm, fmt, mark_bad=mark_bad, fontsize=6.25)
    fig.subplots_adjust(left=0.135, right=0.996, top=0.920, bottom=0.060, wspace=0.08, hspace=0.20)

    out_path = OUT / "structured_prior_error_replay.png"
    jhs.save_white_rgb(fig, out_path, pad_inches=0.018)
    for directory in PIC_DIRS:
        jhs.save_white_rgb(fig, directory / "journal_structured_prior_error_replay.png", pad_inches=0.018)
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]], seed_count: int, include_usgs: bool) -> None:
    lines = [
        "# Structured Prior-error Replay\n\n",
        "This diagnostic plans on spatially perturbed prior bathymetry and replays the same line family on the truth grid.\n\n",
        f"- Seeds per scenario: {seed_count}\n",
        f"- USGS high-complexity crop included: {include_usgs}\n",
        "- Scenarios: nominal, correlated low-frequency bias, slope-amplified bias, localized canyon-wall bias.\n\n",
        "| Scene | Scenario | Method | Feasible | Coverage margin pp | Excess overlap % | Path gain vs truth Fixed % | Prior RMSE m |\n",
        "|---|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['scene_name']} | {row['scenario_label']} | {row['method_label']} | "
            f"{float(row['replay_feasible_mean']):.2f} | "
            f"{float(row['replay_coverage_pct_mean']) - geo.TARGET_COVERAGE_PCT:+.2f} | "
            f"{float(row['replay_excess_overlap_pct_mean']):.2f} | "
            f"{float(row['path_gain_vs_truth_fixed_pct_mean']):.2f} | "
            f"{float(row['prior_rmse_m_mean']):.1f} |\n"
        )
    lines.append(
        "\nInterpretation: this is a prior-map robustness stress test, not a field validation. "
        "It is intended to identify whether the geometry-aware line family survives spatially structured map error before stronger mission-log or simulator evidence is available.\n"
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-count", type=int, default=20)
    parser.add_argument("--skip-usgs", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    raw_rows, summary_rows, manifests = run_replay(seed_count=args.seed_count, include_usgs=not args.skip_usgs)
    write_csv(OUT / "structured_prior_error_raw.csv", raw_rows)
    write_csv(OUT / "structured_prior_error_summary.csv", summary_rows)
    (OUT / "structured_prior_error_summary.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")
    (OUT / "structured_prior_error_manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    make_figure(summary_rows)
    write_report(summary_rows, seed_count=args.seed_count, include_usgs=not args.skip_usgs)

    compact = [
        {
            "scene": row["scene_name"],
            "scenario": row["scenario"],
            "method": row["method_label"],
            "feasible": round(float(row["replay_feasible_mean"]), 3),
            "coverage_margin_pp": round(float(row["replay_coverage_pct_mean"]) - geo.TARGET_COVERAGE_PCT, 3),
            "excess_overlap_pct": round(float(row["replay_excess_overlap_pct_mean"]), 3),
        }
        for row in summary_rows
        if row["method"] == "Full Geometry-Aware Hybrid GA"
    ]
    print(json.dumps({"out_dir": str(OUT), "hybrid_summary": compact}, indent=2))


if __name__ == "__main__":
    main()
