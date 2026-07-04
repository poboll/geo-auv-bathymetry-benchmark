from __future__ import annotations

import argparse
import csv
import json
import math
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np

import geo_public_bathy_benchmark as geo
import make_threshold_local_failure_extension as threshold


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "submission_boundary_diagnostics"
WMAX_VALUES_M = (1200.0, 1800.0, 2400.0)
SCENE_LABELS = {
    "gebco_cascadia_margin_moderate": "GEBCO Cascadia",
    "gebco_monterey_canyon_complex": "GEBCO Monterey",
    "usgs_southern_cascadia_30m_high": "USGS High",
}
MAIN_METHODS = (
    "Fixed-Spacing",
    "Simple Greedy",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
)
HYBRID = "Full Geometry-Aware Hybrid GA"
ADAPTIVE = "Adaptive Spacing w/o GA"


def _safe_json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _directional_swath_width_with_cap(
    scene: geo.TerrainScene,
    phi_rad: float,
    beam_angle_deg: float = geo.BEAM_ANGLE_DEG,
    *,
    wmin_m: float = 30.0,
    wmax_m: float = 1800.0,
) -> np.ndarray:
    dx = float(scene.x[0, 1] - scene.x[0, 0])
    dy = float(scene.y[1, 0] - scene.y[0, 0])
    dz_dy, dz_dx = np.gradient(scene.z, dy, dx)

    cross_track_dx = -math.sin(phi_rad)
    cross_track_dy = math.cos(phi_rad)
    dz_dv = dz_dx * cross_track_dx + dz_dy * cross_track_dy

    a1 = np.arctan(dz_dv)
    half = math.radians(beam_angle_deg / 2.0)

    denom_port = np.sin(np.pi / 2.0 + a1 - half)
    denom_star = np.sin(np.pi / 2.0 - a1 - half)
    denom_port = np.sign(denom_port) * np.maximum(np.abs(denom_port), 1e-3)
    denom_star = np.sign(denom_star) * np.maximum(np.abs(denom_star), 1e-3)

    width = ((scene.z * math.sin(half) / denom_port) + (scene.z * math.sin(half) / denom_star)) * np.cos(a1)
    width = np.nan_to_num(width, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(width, wmin_m, wmax_m)


@contextmanager
def swath_cap(wmax_m: float) -> Iterator[None]:
    original = geo.directional_swath_width

    def capped(
        scene: geo.TerrainScene,
        phi_rad: float,
        beam_angle_deg: float = geo.BEAM_ANGLE_DEG,
    ) -> np.ndarray:
        return _directional_swath_width_with_cap(scene, phi_rad, beam_angle_deg, wmax_m=wmax_m)

    geo.directional_swath_width = capped
    try:
        yield
    finally:
        geo.directional_swath_width = original


def _plan_score(plan: geo.PlanResult) -> float:
    return geo.plan_score(plan.path_length_km, plan.coverage_pct, plan.excess_overlap_pct)


def _plan_row(scene: geo.TerrainScene, plan: geo.PlanResult, wmax_m: float) -> dict[str, Any]:
    return {
        "wmax_m": float(wmax_m),
        "scene_id": scene.scene_id,
        "scene_label": SCENE_LABELS.get(scene.scene_id, scene.display_name),
        "method": plan.method,
        "seed": int(plan.seed),
        "orientation_deg": float(plan.orientation_deg),
        "line_count": int(plan.line_count),
        "path_length_km": float(plan.path_length_km),
        "coverage_pct": float(plan.coverage_pct),
        "excess_overlap_pct": float(plan.excess_overlap_pct),
        "score": float(_plan_score(plan)),
        "feasible_97_3": int(plan.feasible),
    }


def _run_scene_methods(scene: geo.TerrainScene, seed_count: int, wmax_m: float) -> list[geo.PlanResult]:
    fixed = geo.fixed_spacing_plan(scene)
    simple, _ = geo.simple_greedy_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    plans = [fixed, simple, adaptive]
    for seed in range(seed_count):
        plans.append(geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed))
    return plans


def _summarize_wmax(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[float, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((float(row["wmax_m"]), row["scene_id"], row["method"]), []).append(row)

    summary: list[dict[str, Any]] = []
    metric_keys = (
        "path_length_km",
        "coverage_pct",
        "excess_overlap_pct",
        "score",
        "feasible_97_3",
        "line_count",
        "orientation_deg",
    )
    for (wmax_m, scene_id, method), items in sorted(grouped.items()):
        record: dict[str, Any] = {
            "wmax_m": wmax_m,
            "scene_id": scene_id,
            "scene_label": SCENE_LABELS.get(scene_id, scene_id),
            "method": method,
            "n_runs": len(items),
        }
        for key in metric_keys:
            vals = np.asarray([float(item[key]) for item in items], dtype=float)
            record[f"{key}_mean"] = float(np.mean(vals))
            record[f"{key}_min"] = float(np.min(vals))
            record[f"{key}_max"] = float(np.max(vals))
        summary.append(record)
    return summary


def _gate_accepts(raw: geo.PlanResult, adaptive: geo.PlanResult) -> bool:
    return (
        raw.feasible
        and raw.coverage_pct >= adaptive.coverage_pct - 0.05
        and raw.excess_overlap_pct <= adaptive.excess_overlap_pct + 0.05
        and raw.path_length_km <= adaptive.path_length_km
    )


def _practical_rows(scene: geo.TerrainScene, seed_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    raw_rows: list[dict[str, Any]] = []
    for seed in range(seed_count):
        raw = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed)
        accepted = _gate_accepts(raw, adaptive)
        selected = raw if accepted else adaptive
        raw_rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_label": SCENE_LABELS.get(scene.scene_id, scene.display_name),
                "seed": seed,
                "adaptive_path_km": float(adaptive.path_length_km),
                "hybrid_path_km": float(raw.path_length_km),
                "gated_path_km": float(selected.path_length_km),
                "path_gain_vs_adaptive_pct": float(
                    100.0 * (adaptive.path_length_km - raw.path_length_km) / max(adaptive.path_length_km, 1e-9)
                ),
                "coverage_delta_pp": float(raw.coverage_pct - adaptive.coverage_pct),
                "overlap_delta_pp": float(raw.excess_overlap_pct - adaptive.excess_overlap_pct),
                "score_delta_vs_adaptive": float(_plan_score(raw) - _plan_score(adaptive)),
                "hybrid_feasible_97_3": int(raw.feasible),
                "path_shorter": int(raw.path_length_km < adaptive.path_length_km),
                "coverage_no_worse_005pp": int(raw.coverage_pct >= adaptive.coverage_pct - 0.05),
                "overlap_no_worse_005pp": int(raw.excess_overlap_pct <= adaptive.excess_overlap_pct + 0.05),
                "score_better": int(_plan_score(raw) < _plan_score(adaptive)),
                "gate_accept": int(accepted),
                "gated_fallback_to_adaptive": int(not accepted),
            }
        )
    summary_rows = _summarize_practical(raw_rows)
    return raw_rows, summary_rows


def _summarize_practical(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["scene_id"], []).append(row)
    summary: list[dict[str, Any]] = []
    metric_keys = (
        "path_gain_vs_adaptive_pct",
        "coverage_delta_pp",
        "overlap_delta_pp",
        "score_delta_vs_adaptive",
    )
    count_keys = (
        "hybrid_feasible_97_3",
        "path_shorter",
        "coverage_no_worse_005pp",
        "overlap_no_worse_005pp",
        "score_better",
        "gate_accept",
        "gated_fallback_to_adaptive",
    )
    for scene_id, items in sorted(grouped.items()):
        record: dict[str, Any] = {
            "scene_id": scene_id,
            "scene_label": items[0]["scene_label"],
            "n_seeds": len(items),
            "adaptive_path_km": float(items[0]["adaptive_path_km"]),
        }
        for key in metric_keys:
            vals = np.asarray([float(item[key]) for item in items], dtype=float)
            record[f"{key}_mean"] = float(np.mean(vals))
            record[f"{key}_median"] = float(np.median(vals))
            record[f"{key}_min"] = float(np.min(vals))
            record[f"{key}_max"] = float(np.max(vals))
        for key in count_keys:
            vals = np.asarray([int(item[key]) for item in items], dtype=int)
            record[f"{key}_count"] = int(np.sum(vals))
            record[f"{key}_rate"] = float(np.mean(vals))
        summary.append(record)
    return summary


def _write_report(
    wmax_summary: list[dict[str, Any]],
    practical_summary: list[dict[str, Any]],
    seed_count: int,
) -> None:
    hybrid_rows = [row for row in wmax_summary if row["method"] == HYBRID]
    lines = [
        "# Submission Boundary Diagnostics\n\n",
        "This diagnostic is a submission-facing audit, not a replacement for the main benchmark. ",
        "It reruns the two primary GEBCO scenes and the USGS high-complexity crop under alternative ",
        "declared swath-width caps and summarizes whether raw Hybrid GA refinements would pass a ",
        "conservative operational acceptance gate against the deterministic Adaptive Spacing baseline.\n\n",
        f"- Hybrid seeds per scene/cap: 0--{seed_count - 1}\n",
        "- Swath-width caps tested: 1200, 1800, and 2400 m.\n",
        "- Gate diagnostic: accept raw Hybrid only if it is feasible, no worse than Adaptive by 0.05 pp in ",
        "coverage and excess overlap, and no longer in path length; otherwise fall back to Adaptive.\n\n",
        "## Wmax sensitivity summary for Hybrid GA\n\n",
        "| Scene | Wmax (m) | Feas. rate | Path (km) | Coverage (%) | Excess overlap (%) | Lines |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for row in sorted(hybrid_rows, key=lambda item: (item["scene_id"], item["wmax_m"])):
        lines.append(
            f"| {row['scene_label']} | {row['wmax_m']:.0f} | {row['feasible_97_3_mean']:.2f} | "
            f"{row['path_length_km_mean']:.2f} | {row['coverage_pct_mean']:.2f} | "
            f"{row['excess_overlap_pct_mean']:.3f} | {row['line_count_mean']:.1f} |\n"
        )
    lines.extend(
        [
            "\n## Adaptive-vs-Hybrid practical significance and gate diagnostic\n\n",
            "| Scene | Seeds | Median path gain vs Adaptive (%) | Median coverage delta (pp) | Median overlap delta (pp) | Score-better rate | Gate accept rate |\n",
            "|---|---:|---:|---:|---:|---:|---:|\n",
        ]
    )
    for row in practical_summary:
        lines.append(
            f"| {row['scene_label']} | {row['n_seeds']} | "
            f"{row['path_gain_vs_adaptive_pct_median']:.4f} | "
            f"{row['coverage_delta_pp_median']:.4f} | "
            f"{row['overlap_delta_pp_median']:.4f} | "
            f"{row['score_better_rate']:.2f} | {row['gate_accept_rate']:.2f} |\n"
        )
    lines.extend(
        [
            "\n## Reviewer-facing interpretation\n\n",
            "- Changing the declared Wmax cap changes absolute line density and path totals, so the cap must remain a declared evaluator parameter.\n",
            "- The qualitative regime interpretation is the main object of this audit: GEBCO remains a low-overlap public-prior benchmark, whereas USGS High remains the overlap-stressed transfer case.\n",
            "- The conservative gate generally prevents raw GA seeds from being interpreted as operationally superior unless their route reduction is not purchased by lower coverage or higher overlap.\n",
            "- These outputs should be cited as reproducibility artifacts and boundary diagnostics, not as deployment validation.\n",
        ]
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-count", type=int, default=20)
    args = parser.parse_args()
    if args.seed_count < 1:
        raise ValueError("--seed-count must be at least 1")

    OUT.mkdir(parents=True, exist_ok=True)
    scenes = threshold.load_scenes()

    all_wmax_rows: list[dict[str, Any]] = []
    manifests = []
    for scene in scenes:
        manifests.append(scene.manifest_entry)
        for wmax_m in WMAX_VALUES_M:
            print(f"running Wmax={wmax_m:.0f} m scene={scene.scene_id}", flush=True)
            with swath_cap(wmax_m):
                for plan in _run_scene_methods(scene, args.seed_count, wmax_m):
                    all_wmax_rows.append(_plan_row(scene, plan, wmax_m))

    practical_raw: list[dict[str, Any]] = []
    practical_summary: list[dict[str, Any]] = []
    with swath_cap(1800.0):
        for scene in scenes:
            print(f"running gate diagnostic scene={scene.scene_id}", flush=True)
            raw_rows, summary_rows = _practical_rows(scene, args.seed_count)
            practical_raw.extend(raw_rows)
            practical_summary.extend(summary_rows)

    wmax_summary = _summarize_wmax(all_wmax_rows)
    _write_csv(OUT / "wmax_sensitivity_raw.csv", all_wmax_rows)
    _write_csv(OUT / "wmax_sensitivity_summary.csv", wmax_summary)
    _write_csv(OUT / "ga_gate_practical_significance_raw.csv", practical_raw)
    _write_csv(OUT / "ga_gate_practical_significance.csv", practical_summary)
    _safe_json_dump(
        OUT / "submission_boundary_diagnostics_summary.json",
        {
            "seed_count": args.seed_count,
            "wmax_values_m": list(WMAX_VALUES_M),
            "wmax_summary_rows": wmax_summary,
            "ga_gate_practical_significance": practical_summary,
            "manifests": manifests,
        },
    )
    _write_report(wmax_summary, practical_summary, args.seed_count)
    print(
        json.dumps(
            {
                "out_dir": str(OUT),
                "seed_count": args.seed_count,
                "wmax_rows": len(all_wmax_rows),
                "practical_rows": len(practical_raw),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
