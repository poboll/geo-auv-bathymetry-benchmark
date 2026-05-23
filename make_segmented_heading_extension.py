from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

import geo_public_bathy_benchmark as geo


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "segmented_heading_extension"
PIC_DIRS = [
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
]
METHOD_SINGLE = "Full Geometry-Aware Hybrid GA"
METHOD_SEG_ADAPTIVE = "Segmented Adaptive"
METHOD_SEG_HYBRID = "Segmented Hybrid GA"
METHOD_SEG_CP = "Coverage-Preserving Segmented Hybrid"
METHOD_SEG_TA = "Transition-Aware Segmented Hybrid"
METHOD_ORDER = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    METHOD_SINGLE,
    METHOD_SEG_ADAPTIVE,
    METHOD_SEG_HYBRID,
    METHOD_SEG_CP,
    METHOD_SEG_TA,
)
DEFAULT_SCENES = "synthetic_complex,gebco_monterey_canyon_complex"
DEFAULT_SEGMENT_OVERLAP_TARGETS = (-0.05, 0.0, 0.05, 0.10, 0.15)
DEFAULT_MIN_TURN_RADIUS_M = 100.0
DEFAULT_SEGMENT_CANDIDATE_TOP_K = 4
SURVEY_SPEED_MPS = 1.5
TURN_SPEED_MPS = 0.75
TRANSITION_SELECTOR_OVERLAP_WEIGHT_H_PER_PCT = 0.02
USGS_SEGMENTED_SCENE_IDS = {
    "usgs_southern_cascadia_30m_low",
    "usgs_southern_cascadia_30m_medium",
    "usgs_southern_cascadia_30m_high",
}


def save_white_rgb(fig, path: Path, *, dpi: int = 420, pad_inches: float = 0.018) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white", pad_inches=pad_inches)
    image = Image.open(path).convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    background.convert("RGB").save(path, optimize=True)


@dataclass
class StripPlan:
    index: int
    y0_m: float
    y1_m: float
    local_scene: geo.TerrainScene
    result: geo.PlanResult
    overlap_target: float

    @property
    def n_cells(self) -> int:
        return int(self.local_scene.z.size)

    def payload(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "y0_m": self.y0_m,
            "y1_m": self.y1_m,
            "orientation_deg": float(self.result.orientation_deg),
            "overlap_target": float(self.overlap_target),
            "line_positions_m": [float(v) for v in self.result.line_positions],
            "line_count": int(self.result.line_count),
            "path_length_km": float(self.result.path_length_km),
            "coverage_pct": float(self.result.coverage_pct),
            "excess_overlap_pct": float(self.result.excess_overlap_pct),
        }


@dataclass
class SegmentBase:
    index: int
    y0_m: float
    y1_m: float
    local_scene: geo.TerrainScene
    base: geo.LayoutCandidate
    overlap_target: float
    base_search_time_s: float
    candidate_rank: int = 0


@dataclass
class SegmentCandidate:
    candidate: geo.LayoutCandidate
    overlap_target: float
    local_score: float


def _safe_json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        fieldnames: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _stderr(values: np.ndarray) -> float:
    if len(values) <= 1:
        return 0.0
    return float(values.std(ddof=1) / math.sqrt(len(values)))


def _add_transition_selector_metrics(row: dict[str, Any], selector_radius_m: float) -> dict[str, Any]:
    out = dict(row)
    n_segments = max(int(out.get("n_segments", 1)), 1)
    line_count = max(int(out.get("line_count", 0)), 0)
    line_change_count = max(line_count - n_segments, 0)
    path_without_transition_km = float(out.get("path_without_transition_km", out.get("path_length_km", 0.0)))
    boundary_transition_km = float(out.get("boundary_transition_km", 0.0))
    base_turn_radius_m = float(out.get("min_turn_radius_m", 0.0))
    base_heading_arc_km = float(out.get("turn_transition_km", 0.0))
    if selector_radius_m <= 0.0:
        heading_arc_km = 0.0
        line_change_arc_km = 0.0
    else:
        heading_arc_km = (
            0.0
            if base_turn_radius_m <= 0.0
            else base_heading_arc_km * selector_radius_m / base_turn_radius_m
        )
        line_change_arc_km = line_change_count * math.pi * selector_radius_m / 1000.0
    turn_arc_km = heading_arc_km + line_change_arc_km
    base_motion_km = path_without_transition_km + boundary_transition_km
    vehicle_length_km = base_motion_km + turn_arc_km
    mission_time_h = (
        base_motion_km * 1000.0 / SURVEY_SPEED_MPS + turn_arc_km * 1000.0 / TURN_SPEED_MPS
    ) / 3600.0
    selector_objective = mission_time_h + TRANSITION_SELECTOR_OVERLAP_WEIGHT_H_PER_PCT * max(
        0.0, float(out.get("excess_overlap_pct", 0.0))
    )
    out.update(
        {
            "transition_selector_radius_m": float(selector_radius_m),
            "transition_selector_line_change_count": int(line_change_count),
            "transition_selector_heading_arc_km": float(heading_arc_km),
            "transition_selector_line_change_arc_km": float(line_change_arc_km),
            "transition_selector_turn_arc_km": float(turn_arc_km),
            "transition_selector_vehicle_length_km": float(vehicle_length_km),
            "transition_selector_turn_arc_fraction_pct": (
                100.0 * turn_arc_km / vehicle_length_km if vehicle_length_km > 0.0 else 0.0
            ),
            "transition_selector_mission_time_h": float(mission_time_h),
            "transition_selector_objective": float(selector_objective),
        }
    )
    return out


def _scene_registry() -> dict[str, geo.TerrainScene | geo.PublicSceneSpec]:
    registry: dict[str, geo.TerrainScene | geo.PublicSceneSpec] = {
        scene.scene_id: scene for scene in geo.terrain_generators()
    }
    for spec in geo.PUBLIC_SCENE_SPECS:
        registry[spec.scene_id] = spec
    try:
        import make_gebco_scene_expansion as expansion

        for spec in expansion.EXTRA_GEBCO_SPECS:
            registry[spec.scene_id] = spec
    except Exception:
        pass
    return registry


def load_usgs_extension_scene(scene_id: str) -> geo.TerrainScene:
    if scene_id not in USGS_SEGMENTED_SCENE_IDS:
        raise KeyError(scene_id)
    try:
        import rasterio

        import make_survey_grade_extension as extension
        import make_survey_grade_pilot as pilot
    except Exception as exc:  # pragma: no cover - exercised only when optional GIS deps are absent.
        raise RuntimeError("USGS segmented scene loading requires rasterio and the survey-grade extension scripts.") from exc

    pilot.ensure_extracted()
    with rasterio.open(pilot.RASTER_PATH) as dataset:
        candidates = extension.enumerate_candidate_windows(dataset)
        selected = extension.select_windows(candidates, [0.25, 0.55, 0.80])
        label = scene_id.removeprefix("usgs_southern_cascadia_30m_")
        for selected_label, window, metrics in selected:
            if selected_label == label:
                return extension.scene_from_window(dataset, selected_label, window, metrics)
    known = ", ".join(sorted(USGS_SEGMENTED_SCENE_IDS))
    raise KeyError(f"Unknown USGS segmented scene_id={scene_id!r}. Known USGS ids: {known}")


def load_scenes(scene_ids: list[str]) -> list[geo.TerrainScene]:
    registry = _scene_registry()
    out: list[geo.TerrainScene] = []
    for scene_id in scene_ids:
        if scene_id in USGS_SEGMENTED_SCENE_IDS:
            out.append(load_usgs_extension_scene(scene_id))
            continue
        if scene_id not in registry:
            known = ", ".join(sorted(set(registry) | USGS_SEGMENTED_SCENE_IDS))
            raise KeyError(f"Unknown scene_id={scene_id!r}. Known scenes: {known}")
        item = registry[scene_id]
        if isinstance(item, geo.TerrainScene):
            out.append(item)
        else:
            out.append(geo.load_public_scene(item, ROOT))
    return out


def strip_scene(scene: geo.TerrainScene, n_segments: int, index: int) -> tuple[geo.TerrainScene, float, float]:
    ny = scene.z.shape[0]
    start = int(round(index * ny / n_segments))
    stop = int(round((index + 1) * ny / n_segments))
    stop = min(max(stop, start + 2), ny)
    if index == n_segments - 1:
        stop = ny
    rows = slice(start, stop)
    x = scene.x[rows, :].copy()
    y = scene.y[rows, :].copy()
    z = scene.z[rows, :].copy()
    y0_m = float(y[0, 0])
    y1_m = float(y[-1, 0])
    x = x - float(x[0, 0])
    y = y - y0_m
    local = geo.TerrainScene(
        scene_id=f"{scene.scene_id}_segment_{index + 1:02d}_of_{n_segments:02d}",
        display_name=f"{scene.display_name} segment {index + 1}/{n_segments}",
        scene_group=scene.scene_group,
        terrain_class=scene.terrain_class,
        x=x,
        y=y,
        z=z,
        source=scene.source,
        download_url=scene.download_url,
        raw_file=scene.raw_file,
        manifest_entry={
            "parent_scene_id": scene.scene_id,
            "segment_index": index,
            "segment_count": n_segments,
            "y0_m": y0_m,
            "y1_m": y1_m,
        },
    )
    return local, y0_m, y1_m


def segmented_boundary_transition_km(scene: geo.TerrainScene, n_segments: int) -> float:
    if n_segments <= 1:
        return 0.0
    # Conservative bookkeeping for inter-block transits; the geometry diagnostic
    # should not get a free lunch from splitting a mission into independent blocks.
    return (n_segments - 1) * scene.width_m / 1000.0


def _axial_heading_delta_rad(a_deg: float, b_deg: float) -> float:
    # Survey lines are axial: 0 and 180 degrees describe the same line family.
    delta_deg = abs((a_deg - b_deg + 90.0) % 180.0 - 90.0)
    return math.radians(delta_deg)


def segmented_turn_transition_km(strips: list[StripPlan], min_turn_radius_m: float) -> float:
    if len(strips) <= 1 or min_turn_radius_m <= 0.0:
        return 0.0
    turn_m = 0.0
    for left, right in zip(strips[:-1], strips[1:]):
        turn_m += min_turn_radius_m * _axial_heading_delta_rad(
            float(left.result.orientation_deg),
            float(right.result.orientation_deg),
        )
    return turn_m / 1000.0


def aggregate_strips(
    scene: geo.TerrainScene,
    method: str,
    seed: int,
    n_segments: int,
    strips: list[StripPlan],
    min_turn_radius_m: float,
) -> dict[str, Any]:
    weights = np.asarray([strip.n_cells for strip in strips], dtype=float)
    coverage = np.asarray([strip.result.coverage_pct for strip in strips], dtype=float)
    overlap = np.asarray([strip.result.excess_overlap_pct for strip in strips], dtype=float)
    boundary_transition_km = segmented_boundary_transition_km(scene, n_segments)
    turn_transition_km = segmented_turn_transition_km(strips, min_turn_radius_m)
    transition_km = boundary_transition_km + turn_transition_km
    path_without_transition = float(sum(strip.result.path_length_km for strip in strips))
    path_length = path_without_transition + transition_km
    planning_time = float(sum(strip.result.planning_time_s for strip in strips))
    coverage_pct = float(np.average(coverage, weights=weights))
    excess_overlap_pct = float(np.average(overlap, weights=weights))
    row = {
        "scene_id": scene.scene_id,
        "scene_name": scene.display_name,
        "scene_group": scene.scene_group,
        "terrain_class": scene.terrain_class,
        "method": method,
        "seed": int(seed),
        "n_segments": int(n_segments),
        "orientation_deg": "segmented",
        "path_length_km": path_length,
        "path_without_transition_km": path_without_transition,
        "segment_transition_km": transition_km,
        "boundary_transition_km": boundary_transition_km,
        "turn_transition_km": turn_transition_km,
        "min_turn_radius_m": float(min_turn_radius_m),
        "coverage_pct": coverage_pct,
        "excess_overlap_pct": excess_overlap_pct,
        "planning_time_s": planning_time,
        "line_count": int(sum(strip.result.line_count for strip in strips)),
        "feasible": int(geo._is_feasible(coverage_pct, excess_overlap_pct)),
        "segments_json": json.dumps([strip.payload() for strip in strips], ensure_ascii=False),
        "segment_overlap_targets": ",".join(f"{strip.overlap_target:.2f}" for strip in strips),
        "accepted_layout": 0,
        "acceptance_status": "candidate_not_checked",
        "selected_from_method": method,
        "reference_single_coverage_pct": np.nan,
        "reference_single_excess_overlap_pct": np.nan,
        "reference_single_path_length_km": np.nan,
        "reference_single_feasible": np.nan,
        "coverage_delta_vs_reference_pp": np.nan,
        "excess_overlap_delta_vs_reference_pp": np.nan,
        "path_delta_vs_reference_km": np.nan,
        "feasibility_improved": 0,
    }
    return _add_transition_selector_metrics(row, min_turn_radius_m)


def single_result_row(
    result: geo.PlanResult,
    n_segments: int = 1,
    min_turn_radius_m: float = DEFAULT_MIN_TURN_RADIUS_M,
) -> dict[str, Any]:
    row = {
        "scene_id": result.scene_id,
        "scene_name": result.scene_name,
        "scene_group": result.scene_group,
        "terrain_class": result.terrain_class,
        "method": result.method,
        "seed": int(result.seed),
        "n_segments": int(n_segments),
        "orientation_deg": f"{float(result.orientation_deg):.6f}",
        "path_length_km": float(result.path_length_km),
        "path_without_transition_km": float(result.path_length_km),
        "segment_transition_km": 0.0,
        "boundary_transition_km": 0.0,
        "turn_transition_km": 0.0,
        "min_turn_radius_m": 0.0,
        "coverage_pct": float(result.coverage_pct),
        "excess_overlap_pct": float(result.excess_overlap_pct),
        "planning_time_s": float(result.planning_time_s),
        "line_count": int(result.line_count),
        "feasible": int(result.feasible),
        "segments_json": "",
        "segment_overlap_targets": "",
        "accepted_layout": int(result.feasible),
        "acceptance_status": "single_heading_reference",
        "selected_from_method": result.method,
        "reference_single_coverage_pct": float(result.coverage_pct),
        "reference_single_excess_overlap_pct": float(result.excess_overlap_pct),
        "reference_single_path_length_km": float(result.path_length_km),
        "reference_single_feasible": int(result.feasible),
        "coverage_delta_vs_reference_pp": 0.0,
        "excess_overlap_delta_vs_reference_pp": 0.0,
        "path_delta_vs_reference_km": 0.0,
        "feasibility_improved": 0,
    }
    return _add_transition_selector_metrics(row, min_turn_radius_m)


def best_segment_adaptive_layout(
    scene: geo.TerrainScene,
    overlap_targets: tuple[float, ...] = DEFAULT_SEGMENT_OVERLAP_TARGETS,
) -> tuple[geo.LayoutCandidate, float]:
    candidates = segment_adaptive_layout_candidates(scene, overlap_targets, top_k=1)
    return candidates[0].candidate, candidates[0].overlap_target


def segment_candidate_score(scene: geo.TerrainScene, candidate: geo.LayoutCandidate) -> float:
    context = geo.make_context(scene, float(candidate.orientation_deg))
    path_length = geo.plan_length_km(scene, candidate.line_positions, context.phi_rad)
    coverage_penalty = max(0.0, geo.TARGET_COVERAGE_PCT - candidate.coverage_pct) * 90.0
    overlap_penalty = candidate.excess_overlap_pct * 8.0 + max(
        0.0,
        candidate.excess_overlap_pct - geo.EXCESS_OVERLAP_FEASIBLE_PCT,
    ) * 120.0
    return float(path_length + coverage_penalty + overlap_penalty)


def segment_adaptive_layout_candidates(
    scene: geo.TerrainScene,
    overlap_targets: tuple[float, ...] = DEFAULT_SEGMENT_OVERLAP_TARGETS,
    top_k: int = DEFAULT_SEGMENT_CANDIDATE_TOP_K,
) -> list[SegmentCandidate]:
    top_k = max(1, int(top_k))
    raw: list[SegmentCandidate] = []
    best = geo.LayoutCandidate(
        orientation_deg=float(geo.ANGLE_CANDIDATES[0]),
        line_positions=np.asarray([], dtype=float),
        coverage_pct=0.0,
        excess_overlap_pct=float("inf"),
        score=float("inf"),
    )
    best_target = float(overlap_targets[0])
    for angle in geo.ANGLE_CANDIDATES:
        context = geo.make_context(scene, float(angle))
        for quantile in geo.ADAPTIVE_QUANTILES:
            profile_v, profile_w = geo.cross_track_profile(context, quantile)
            for overlap_target in overlap_targets:
                positions = geo.adaptive_line_positions(
                    context.vmin,
                    context.vmax,
                    profile_v,
                    profile_w,
                    overlap_target=overlap_target,
                )
                coverage_pct, overlap_pct = geo.coverage_and_overlap(
                    context.v_grid,
                    positions,
                    context.swath_width,
                )
                path_length = geo.plan_length_km(scene, positions, context.phi_rad)
                coverage_penalty = max(0.0, geo.TARGET_COVERAGE_PCT - coverage_pct) * 90.0
                overlap_penalty = overlap_pct * 8.0 + max(0.0, overlap_pct - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 120.0
                score = path_length + coverage_penalty + overlap_penalty
                candidate = geo.LayoutCandidate(
                    orientation_deg=float(angle),
                    line_positions=positions,
                    coverage_pct=coverage_pct,
                    excess_overlap_pct=overlap_pct,
                    score=score,
                )
                raw.append(SegmentCandidate(candidate, float(overlap_target), float(score)))
                if score < best.score:
                    best = candidate
                    best_target = float(overlap_target)

    raw.sort(key=lambda item: item.local_score)
    selected: list[SegmentCandidate] = []
    seen: set[tuple[int, int, float]] = set()
    seen_orientations: set[int] = set()
    for item in raw:
        orientation_key = int(round(item.candidate.orientation_deg))
        key = (orientation_key, int(len(item.candidate.line_positions)), round(item.overlap_target, 3))
        if key in seen:
            continue
        if orientation_key not in seen_orientations or len(selected) >= max(1, top_k // 2):
            selected.append(item)
            seen.add(key)
            seen_orientations.add(orientation_key)
        if len(selected) >= top_k:
            break
    if not selected:
        selected = [SegmentCandidate(best, best_target, float(best.score))]
    return selected


def strict_segment_score(result: geo.PlanResult) -> float:
    coverage_penalty = max(0.0, geo.TARGET_COVERAGE_PCT - result.coverage_pct) * 90.0
    overlap_penalty = result.excess_overlap_pct * 8.0 + max(
        0.0,
        result.excess_overlap_pct - geo.EXCESS_OVERLAP_FEASIBLE_PCT,
    ) * 120.0
    return float(result.path_length_km + coverage_penalty + overlap_penalty)


def _decorate_acceptance(row: dict[str, Any], reference_row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    ref_coverage = float(reference_row["coverage_pct"])
    ref_overlap = float(reference_row["excess_overlap_pct"])
    ref_path = float(reference_row["path_length_km"])
    ref_feasible = int(reference_row["feasible"])
    coverage = float(out["coverage_pct"])
    overlap = float(out["excess_overlap_pct"])
    feasible = int(geo._is_feasible(coverage, overlap))
    feasibility_improved = int(ref_feasible == 0 and feasible == 1)
    coverage_ok = coverage >= geo.TARGET_COVERAGE_PCT
    overlap_ok = overlap <= geo.EXCESS_OVERLAP_FEASIBLE_PCT
    coverage_preserved = coverage + 1e-9 >= ref_coverage
    accepted = bool(coverage_ok and overlap_ok and (coverage_preserved or feasibility_improved))
    if accepted:
        status = "accepted_feasibility_repair" if feasibility_improved else "accepted_coverage_preserving"
    elif not coverage_ok:
        status = "rejected_low_global_coverage"
    elif not overlap_ok:
        status = "rejected_excess_overlap"
    else:
        status = "rejected_coverage_regression"
    out.update(
        {
            "accepted_layout": int(accepted),
            "acceptance_status": status,
            "reference_single_coverage_pct": ref_coverage,
            "reference_single_excess_overlap_pct": ref_overlap,
            "reference_single_path_length_km": ref_path,
            "reference_single_feasible": ref_feasible,
            "coverage_delta_vs_reference_pp": coverage - ref_coverage,
            "excess_overlap_delta_vs_reference_pp": overlap - ref_overlap,
            "path_delta_vs_reference_km": float(out["path_length_km"]) - ref_path,
            "feasibility_improved": feasibility_improved,
        }
    )
    return out


def select_coverage_preserving_row(
    single_row: dict[str, Any],
    segmented_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted_segments = [row for row in segmented_rows if int(row.get("accepted_layout", 0)) == 1]
    if accepted_segments:
        # A safe blockwise layout is not automatically better than the original
        # fixed-pattern plan; retain the single-heading layout when it has the
        # lower objective after coverage and overlap gates are satisfied. An
        # infeasible single-heading layout is never allowed to beat a feasible
        # blockwise repair just because it is shorter.
        candidate_pool = ([single_row] if int(single_row["feasible"]) == 1 else []) + accepted_segments
        chosen = min(
            candidate_pool,
            key=lambda row: float(row["path_length_km"]) + 3.0 * float(row["excess_overlap_pct"]),
        )
        if str(chosen["method"]) == METHOD_SINGLE:
            out = dict(single_row)
            out["method"] = METHOD_SEG_CP
            out["selected_from_method"] = str(single_row["method"])
            out["accepted_layout"] = int(single_row["feasible"])
            out["acceptance_status"] = "retained_single_heading_lower_objective"
            return out
        out = dict(chosen)
        out["method"] = METHOD_SEG_CP
        out["selected_from_method"] = str(chosen["method"])
        out["acceptance_status"] = f"selected_{chosen['acceptance_status']}"
        return out

    out = dict(single_row)
    out["method"] = METHOD_SEG_CP
    out["selected_from_method"] = str(single_row["method"])
    if int(single_row["feasible"]) == 1:
        out["accepted_layout"] = 1
        out["acceptance_status"] = "retained_single_heading_no_safe_segment"
    else:
        out["accepted_layout"] = 0
        out["acceptance_status"] = "fallback_single_heading_no_safe_segment"
    return out


def select_transition_aware_row(
    single_row: dict[str, Any],
    segmented_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted_segments = [row for row in segmented_rows if int(row.get("accepted_layout", 0)) == 1]
    candidate_pool = (
        ([single_row] if int(single_row["feasible"]) == 1 else []) + accepted_segments
        if accepted_segments
        else [single_row]
    )
    chosen = min(candidate_pool, key=lambda row: float(row["transition_selector_objective"]))
    out = dict(chosen)
    out["method"] = METHOD_SEG_TA
    out["selected_from_method"] = str(chosen["method"])
    if str(chosen["method"]) == METHOD_SINGLE:
        out["accepted_layout"] = int(single_row["feasible"])
        if accepted_segments:
            out["acceptance_status"] = "retained_single_heading_lower_transition_objective"
        elif int(single_row["feasible"]) == 1:
            out["acceptance_status"] = "retained_single_heading_no_safe_segment"
        else:
            out["acceptance_status"] = "fallback_single_heading_no_safe_segment"
    else:
        out["acceptance_status"] = f"selected_transition_aware_{chosen['acceptance_status']}"
    return out


def _aggregate_candidate_combo(
    scene: geo.TerrainScene,
    n_segments: int,
    bases: list[SegmentBase],
    min_turn_radius_m: float,
) -> dict[str, Any]:
    strips: list[StripPlan] = []
    for segment in bases:
        result = geo.evaluate_plan(
            segment.local_scene,
            METHOD_SEG_ADAPTIVE,
            -1,
            segment.base.orientation_deg,
            segment.base.line_positions,
            segment.base_search_time_s,
        )
        strips.append(
            StripPlan(
                segment.index,
                segment.y0_m,
                segment.y1_m,
                segment.local_scene,
                result,
                segment.overlap_target,
            )
        )
    return aggregate_strips(scene, METHOD_SEG_ADAPTIVE, -1, n_segments, strips, min_turn_radius_m)


def _transition_aware_combo_score(candidate_row: dict[str, Any], reference_row: dict[str, Any]) -> float:
    coverage = float(candidate_row["coverage_pct"])
    overlap = float(candidate_row["excess_overlap_pct"])
    ref_coverage = float(reference_row["coverage_pct"])
    ref_feasible = int(reference_row["feasible"])
    coverage_floor = geo.TARGET_COVERAGE_PCT if ref_feasible == 0 else max(geo.TARGET_COVERAGE_PCT, ref_coverage)
    coverage_penalty = max(0.0, coverage_floor - coverage) * 140.0
    overlap_penalty = overlap * 6.0 + max(0.0, overlap - geo.EXCESS_OVERLAP_FEASIBLE_PCT) * 180.0
    turn_penalty = float(candidate_row["turn_transition_km"]) * 2.0
    return float(candidate_row["path_length_km"]) + coverage_penalty + overlap_penalty + turn_penalty


def run_segmented_adaptive(
    scene: geo.TerrainScene,
    n_segments: int,
    bases: list[SegmentBase],
    min_turn_radius_m: float,
) -> dict[str, Any]:
    strips: list[StripPlan] = []
    for segment in bases:
        result = geo.evaluate_plan(
            segment.local_scene,
            METHOD_SEG_ADAPTIVE,
            -1,
            segment.base.orientation_deg,
            segment.base.line_positions,
            segment.base_search_time_s,
        )
        strips.append(
            StripPlan(
                segment.index,
                segment.y0_m,
                segment.y1_m,
                segment.local_scene,
                result,
                segment.overlap_target,
            )
        )
    return aggregate_strips(scene, METHOD_SEG_ADAPTIVE, -1, n_segments, strips, min_turn_radius_m)


def run_segmented_hybrid(
    scene: geo.TerrainScene,
    n_segments: int,
    seed: int,
    bases: list[SegmentBase],
    min_turn_radius_m: float,
) -> dict[str, Any]:
    strips: list[StripPlan] = []
    for segment in bases:
        start = time.perf_counter()
        base_result = geo.evaluate_plan(
            segment.local_scene,
            METHOD_SEG_HYBRID,
            seed,
            segment.base.orientation_deg,
            segment.base.line_positions,
            segment.base_search_time_s,
        )
        refined = geo.full_geometry_aware_hybrid_ga_plan(
            segment.local_scene,
            segment.base,
            seed * 100 + segment.index,
        )
        elapsed = segment.base_search_time_s + (time.perf_counter() - start)
        result = refined if strict_segment_score(refined) < strict_segment_score(base_result) else base_result
        result.planning_time_s = elapsed
        result.method = METHOD_SEG_HYBRID
        result.seed = seed
        strips.append(
            StripPlan(
                segment.index,
                segment.y0_m,
                segment.y1_m,
                segment.local_scene,
                result,
                segment.overlap_target,
            )
        )
    return aggregate_strips(scene, METHOD_SEG_HYBRID, seed, n_segments, strips, min_turn_radius_m)


def prepare_segment_bases(
    scene: geo.TerrainScene,
    n_segments: int,
    overlap_targets: tuple[float, ...],
    min_turn_radius_m: float,
    reference_row: dict[str, Any],
    top_k: int,
) -> list[SegmentBase]:
    candidate_sets: list[list[SegmentBase]] = []
    for idx in range(n_segments):
        local, y0_m, y1_m = strip_scene(scene, n_segments, idx)
        start = time.perf_counter()
        candidates = segment_adaptive_layout_candidates(local, overlap_targets, top_k=top_k)
        elapsed = time.perf_counter() - start
        segment_options: list[SegmentBase] = []
        for rank, candidate in enumerate(candidates):
            segment_options.append(
                SegmentBase(
                    index=idx,
                    y0_m=y0_m,
                    y1_m=y1_m,
                    local_scene=local,
                    base=candidate.candidate,
                    overlap_target=candidate.overlap_target,
                    base_search_time_s=elapsed,
                    candidate_rank=rank,
                )
            )
        candidate_sets.append(segment_options)

    best_combo: list[SegmentBase] | None = None
    best_score = float("inf")
    for combo in itertools.product(*candidate_sets):
        combo_list = list(combo)
        candidate_row = _aggregate_candidate_combo(scene, n_segments, combo_list, min_turn_radius_m)
        score = _transition_aware_combo_score(candidate_row, reference_row)
        if score < best_score:
            best_score = score
            best_combo = combo_list
    if best_combo is None:
        raise RuntimeError(f"No segmented candidate combination generated for {scene.scene_id} with {n_segments} segments")
    return best_combo


def run_scene(
    scene: geo.TerrainScene,
    seeds: tuple[int, ...],
    segment_counts: tuple[int, ...],
    overlap_targets: tuple[float, ...],
    min_turn_radius_m: float,
    segment_candidate_top_k: int,
) -> list[dict[str, Any]]:
    print(f"running segmented-heading diagnostic for {scene.scene_id}", flush=True)
    rows: list[dict[str, Any]] = []
    fixed = geo.fixed_spacing_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    rows.append(single_result_row(fixed, min_turn_radius_m=min_turn_radius_m))
    rows.append(single_result_row(adaptive, min_turn_radius_m=min_turn_radius_m))
    single_by_seed: dict[int, dict[str, Any]] = {}
    for seed in seeds:
        single_row = single_result_row(
            geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed),
            min_turn_radius_m=min_turn_radius_m,
        )
        single_by_seed[seed] = single_row
        rows.append(single_row)
    segmented_by_seed: dict[int, list[dict[str, Any]]] = {seed: [] for seed in seeds}
    for n_segments in segment_counts:
        reference_row = single_by_seed[seeds[0]]
        bases = prepare_segment_bases(
            scene,
            n_segments,
            overlap_targets,
            min_turn_radius_m,
            reference_row,
            segment_candidate_top_k,
        )
        adaptive_segmented = run_segmented_adaptive(scene, n_segments, bases, min_turn_radius_m)
        rows.append(_decorate_acceptance(adaptive_segmented, reference_row))
        for seed in seeds:
            segmented_row = run_segmented_hybrid(scene, n_segments, seed, bases, min_turn_radius_m)
            segmented_row = _decorate_acceptance(segmented_row, single_by_seed[seed])
            segmented_by_seed[seed].append(segmented_row)
            rows.append(segmented_row)
    for seed in seeds:
        rows.append(select_coverage_preserving_row(single_by_seed[seed], segmented_by_seed[seed]))
        rows.append(select_transition_aware_row(single_by_seed[seed], segmented_by_seed[seed]))
    return rows


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    fixed_lookup: dict[str, float] = {}
    for row in rows:
        grouped[(str(row["scene_id"]), str(row["method"]), int(row["n_segments"]))].append(row)
        if row["method"] == "Fixed-Spacing":
            fixed_lookup[str(row["scene_id"])] = float(row["path_length_km"])

    summary_rows: list[dict[str, Any]] = []
    for (scene_id, method, n_segments), group_rows in sorted(grouped.items()):
        fixed_path = fixed_lookup.get(scene_id, np.nan)
        record: dict[str, Any] = {
            "scene_id": scene_id,
            "scene_name": group_rows[0]["scene_name"],
            "scene_group": group_rows[0]["scene_group"],
            "terrain_class": group_rows[0]["terrain_class"],
            "method": method,
            "n_segments": n_segments,
            "n_runs": len(group_rows),
        }
        for key in (
            "path_length_km",
            "path_without_transition_km",
            "segment_transition_km",
            "boundary_transition_km",
            "turn_transition_km",
            "coverage_pct",
            "excess_overlap_pct",
            "planning_time_s",
            "line_count",
            "feasible",
            "accepted_layout",
            "coverage_delta_vs_reference_pp",
            "excess_overlap_delta_vs_reference_pp",
            "path_delta_vs_reference_km",
            "feasibility_improved",
            "transition_selector_line_change_count",
            "transition_selector_heading_arc_km",
            "transition_selector_line_change_arc_km",
            "transition_selector_turn_arc_km",
            "transition_selector_vehicle_length_km",
            "transition_selector_turn_arc_fraction_pct",
            "transition_selector_mission_time_h",
            "transition_selector_objective",
        ):
            values = np.asarray([float(row[key]) for row in group_rows], dtype=float)
            record[f"{key}_mean"] = float(values.mean())
            record[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            record[f"{key}_stderr"] = _stderr(values)
            record[f"{key}_min"] = float(values.min())
            record[f"{key}_max"] = float(values.max())
        if np.isfinite(fixed_path) and fixed_path > 0:
            record["path_gain_vs_fixed_pct_mean"] = float(
                (fixed_path - record["path_length_km_mean"]) / fixed_path * 100.0
            )
        else:
            record["path_gain_vs_fixed_pct_mean"] = np.nan
        summary_rows.append(record)
    return summary_rows


def _score_row(row: dict[str, Any]) -> float:
    return float(row["path_length_km"]) + max(0.0, 97.0 - float(row["coverage_pct"])) * 80.0 + float(
        row["excess_overlap_pct"]
    ) * 3.0


def _representative_raw(rows: list[dict[str, Any]], scene_id: str, method: str, n_segments: int) -> dict[str, Any]:
    candidates = [
        row
        for row in rows
        if row["scene_id"] == scene_id and row["method"] == method and int(row["n_segments"]) == n_segments
    ]
    if not candidates:
        raise ValueError(f"No raw rows for {scene_id=} {method=} {n_segments=}")
    feasible = [row for row in candidates if int(row["feasible"]) == 1]
    candidates = feasible or candidates
    return sorted(candidates, key=_score_row)[len(candidates) // 2]


def _draw_single_layout(ax, scene: geo.TerrainScene, row: dict[str, Any], *, color: str) -> None:
    geo._render_bathymetry(ax, scene, contour_count=18, contour_step=3, contour_alpha=0.18)
    result = geo.evaluate_plan(
        scene,
        str(row["method"]),
        int(row["seed"]),
        float(row["orientation_deg"]),
        np.asarray(json.loads(row["segments_json"]) if row["segments_json"] else [], dtype=float),
        float(row["planning_time_s"]),
    )
    if not row["segments_json"]:
        # Reconstruct single-heading line positions by recomputing the representative seed.
        _adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
        if row["method"] == METHOD_SINGLE:
            result = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, int(row["seed"]))
        else:
            result = geo.evaluate_plan(
                scene,
                str(row["method"]),
                int(row["seed"]),
                float(row["orientation_deg"]),
                np.asarray([], dtype=float),
                float(row["planning_time_s"]),
            )
    phi = math.radians(result.orientation_deg)
    for pos in result.line_positions[:: max(1, len(result.line_positions) // 24)]:
        xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
        if xs.size:
            ax.plot(xs / geo.NM_TO_M, ys / geo.NM_TO_M, color=color, linewidth=1.05, alpha=0.92)


def _draw_segmented_layout(ax, scene: geo.TerrainScene, row: dict[str, Any]) -> None:
    geo._render_bathymetry(ax, scene, contour_count=18, contour_step=3, contour_alpha=0.18)
    segments = json.loads(str(row["segments_json"]))
    colors = plt.cm.viridis(np.linspace(0.14, 0.86, len(segments)))
    for segment, color in zip(segments, colors):
        y0 = float(segment["y0_m"])
        y1 = float(segment["y1_m"])
        ax.axhline(y0 / geo.NM_TO_M, color="#ffffff", linewidth=1.0, alpha=0.70, zorder=3)
        ax.axhline(y1 / geo.NM_TO_M, color="#ffffff", linewidth=1.0, alpha=0.70, zorder=3)
        phi = math.radians(float(segment["orientation_deg"]))
        height = max(y1 - y0, 1.0)
        positions = np.asarray(segment["line_positions_m"], dtype=float)
        for pos in positions[:: max(1, len(positions) // 12)]:
            xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, height)
            if xs.size:
                ax.plot(
                    xs / geo.NM_TO_M,
                    (ys + y0) / geo.NM_TO_M,
                    color=color,
                    linewidth=1.15,
                    alpha=0.94,
                    solid_capstyle="round",
                    zorder=4,
                )


def make_figure(scenes: list[geo.TerrainScene], raw_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> None:
    scene = next((item for item in scenes if item.scene_id == "synthetic_complex"), scenes[0])
    candidates = [
        row
        for row in summary_rows
        if row["scene_id"] == scene.scene_id
        and row["method"] == METHOD_SEG_TA
        and int(row["n_segments"]) > 1
        and float(row["feasible_mean"]) >= 1.0
    ]
    if not candidates:
        candidates = [
            row
            for row in summary_rows
            if row["scene_id"] == scene.scene_id
            and row["method"] == METHOD_SEG_CP
            and int(row["n_segments"]) > 1
            and float(row["feasible_mean"]) >= 1.0
        ]
    if not candidates:
        candidates = [
            row
            for row in summary_rows
            if row["scene_id"] == scene.scene_id and row["method"] == METHOD_SEG_HYBRID and float(row["feasible_mean"]) >= 1.0
        ]
    if not candidates:
        candidates = [row for row in summary_rows if row["scene_id"] == scene.scene_id and row["method"] == METHOD_SEG_HYBRID]
    best_summary = min(candidates, key=lambda row: float(row["path_length_km_mean"]))
    best_segments = int(best_summary["n_segments"])
    single_row = _representative_raw(raw_rows, scene.scene_id, METHOD_SINGLE, 1)
    if any(row["method"] == METHOD_SEG_TA for row in candidates):
        segmented_method = METHOD_SEG_TA
    elif any(row["method"] == METHOD_SEG_CP for row in candidates):
        segmented_method = METHOD_SEG_CP
    else:
        segmented_method = METHOD_SEG_HYBRID
    segmented_row = _representative_raw(raw_rows, scene.scene_id, segmented_method, best_segments)

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "font.size": 7.2,
            "axes.labelsize": 7.6,
            "axes.titlesize": 8.2,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.35, 4.05), facecolor="white")
    _draw_single_layout(axes[0], scene, single_row, color="#c26a3d")
    _draw_segmented_layout(axes[1], scene, segmented_row)
    for ax, title, row in (
        (axes[0], "Single-heading Hybrid GA", single_row),
        (axes[1], f"{best_segments}-segment transition-aware Hybrid", segmented_row),
    ):
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("East-West (NM)")
        ax.set_ylabel("North-South (NM)")
        ax.set_title(title, fontweight="bold", color="#16212b", pad=4)
        ax.text(
            0.03,
            0.04,
            f"Path {float(row['path_length_km']):.1f} km\n"
            f"Coverage {float(row['coverage_pct']):.2f}%\n"
            f"Excess overlap {float(row['excess_overlap_pct']):.2f}%\n"
            f"Mission proxy {float(row['transition_selector_mission_time_h']):.1f} h",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=7.55,
            color="#16212b",
            bbox={
                "boxstyle": "round,pad=0.28",
                "facecolor": "#ffffff",
                "edgecolor": "#c9d4de",
                "linewidth": 0.8,
                "alpha": 0.96,
            },
        )
        geo._add_scale_bar(ax, 1.0, anchor=(0.68, 0.08))
    axes[1].set_ylabel("")
    axes[1].tick_params(axis="y", labelleft=False)
    fig.text(
        0.020,
        0.965,
        "Transition-aware segmented-heading repair",
        ha="left",
        va="top",
        fontsize=10.8,
        fontweight="bold",
        color="#16212b",
    )
    fig.text(
        0.020,
        0.918,
        "The selected blockwise layout must pass coverage/overlap gates and is then ranked by a declared turn-radius mission-time proxy.",
        ha="left",
        va="top",
        fontsize=7.25,
        color="#52616f",
    )
    fig.text(
        0.020,
        0.030,
        "Segmented layouts split the survey box into cross-track blocks; path length includes conservative boundary transit and minimum-turn-radius arc terms.",
        ha="left",
        va="bottom",
        fontsize=6.9,
        color="#52616f",
    )
    fig.subplots_adjust(left=0.065, right=0.992, bottom=0.135, top=0.855, wspace=0.035)
    out_path = OUT / "segmented_heading_complex_repair.png"
    save_white_rgb(fig, out_path)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
        save_white_rgb(fig, pic_dir / "journal_segmented_heading_complex_repair.png")
    plt.close(fig)


def write_report(
    scenes: list[geo.TerrainScene],
    seeds: tuple[int, ...],
    segment_counts: tuple[int, ...],
    min_turn_radius_m: float,
    segment_candidate_top_k: int,
    summary_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# Segmented-heading extension\n\n",
        "This diagnostic targets the main algorithmic weakness exposed by the current manuscript: a single-heading ",
        "fixed-pattern lawnmower can remain infeasible in complex relief. The segmented variant keeps the method ",
        "auditable by splitting the survey domain into a small number of y-blocks, choosing a terrain-aware heading ",
        "inside each block, and adding a conservative inter-block transit term to the reported path length.\n\n",
        f"- Scenes: {', '.join(scene.scene_id for scene in scenes)}\n",
        f"- Hybrid seeds: {seeds[0]}--{seeds[-1]}\n",
        f"- Segment counts: {', '.join(str(v) for v in segment_counts)}\n",
        f"- Segment candidate top-k per block: {segment_candidate_top_k}\n",
        f"- Minimum turn radius used for transition scoring: {min_turn_radius_m:.1f} m\n",
        "- Acceptance gate: global coverage >= 97%, global excess overlap <= 3%, and no coverage regression relative to the single-heading Hybrid GA unless segmentation changes an infeasible single-heading layout into a feasible one.\n",
        "- Coverage-preserving selector after the acceptance gate: choose the lower path-plus-overlap score, `L + 3 O_ex`, between the single-heading layout and accepted segmented candidates.\n",
        f"- Transition-aware selector after the acceptance gate: choose the lower mission-time proxy at `R_min={min_turn_radius_m:.0f} m`, including survey/transit distance at {SURVEY_SPEED_MPS:.1f} m/s, heading-change arcs and line-change arcs at {TURN_SPEED_MPS:.2f} m/s, plus a small overlap tie-breaker.\n",
        "- Boundary: numerical geometry diagnostic, not AUV controller validation or sea-trial evidence.\n\n",
        "## Summary\n\n",
        "| Scene | Method | Segments | Runs | Path km | Mission proxy h | Coverage % | Excess overlap % | Feasible rate |\n",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n",
    ]
    for row in summary_rows:
        if row["method"] not in (METHOD_SINGLE, METHOD_SEG_ADAPTIVE, METHOD_SEG_HYBRID, METHOD_SEG_CP, METHOD_SEG_TA):
            continue
        lines.append(
            f"| {row['scene_name']} | {row['method']} | {row['n_segments']} | {row['n_runs']} | "
            f"{float(row['path_length_km_mean']):.2f} | {float(row['transition_selector_mission_time_h_mean']):.2f} | "
            f"{float(row['coverage_pct_mean']):.2f} | "
            f"{float(row['excess_overlap_pct_mean']):.3f} | {float(row['feasible_mean']):.2f} |\n"
        )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run segmented-heading diagnostics for complex AUV MBES layouts.")
    parser.add_argument("--scenes", default=DEFAULT_SCENES, help="Comma-separated scene ids.")
    parser.add_argument("--seed-count", type=int, default=20, help="Number of Hybrid GA seeds, starting at zero.")
    parser.add_argument("--segments", default="2,3,4", help="Comma-separated segment counts.")
    parser.add_argument(
        "--segment-overlap-targets",
        default=",".join(str(value) for value in DEFAULT_SEGMENT_OVERLAP_TARGETS),
        help="Comma-separated per-segment overlap targets searched by the segmented planner.",
    )
    parser.add_argument(
        "--min-turn-radius-m",
        type=float,
        default=DEFAULT_MIN_TURN_RADIUS_M,
        help="Minimum turn radius used for Dubins-like inter-segment heading-change arcs.",
    )
    parser.add_argument(
        "--segment-candidate-top-k",
        type=int,
        default=DEFAULT_SEGMENT_CANDIDATE_TOP_K,
        help="Number of adaptive layout candidates retained per segment for transition-aware combination scoring.",
    )
    args = parser.parse_args()
    if args.seed_count < 1:
        raise ValueError("--seed-count must be at least 1")
    seeds = tuple(range(args.seed_count))
    segment_counts = tuple(int(item) for item in args.segments.split(",") if item.strip())
    overlap_targets = tuple(float(item) for item in args.segment_overlap_targets.split(",") if item.strip())
    if not segment_counts or min(segment_counts) < 2:
        raise ValueError("--segments must include integers >= 2")
    if not overlap_targets:
        raise ValueError("--segment-overlap-targets must include at least one value")
    if args.min_turn_radius_m < 0:
        raise ValueError("--min-turn-radius-m must be non-negative")
    if args.segment_candidate_top_k < 1:
        raise ValueError("--segment-candidate-top-k must be at least one")
    scene_ids = [item.strip() for item in args.scenes.split(",") if item.strip()]

    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = load_scenes(scene_ids)
    raw_rows: list[dict[str, Any]] = []
    for scene in scenes:
        raw_rows.extend(
            run_scene(
                scene,
                seeds,
                segment_counts,
                overlap_targets,
                args.min_turn_radius_m,
                args.segment_candidate_top_k,
            )
        )
    summary_rows = summarize(raw_rows)

    _write_csv(OUT / "segmented_heading_raw.csv", raw_rows)
    _write_csv(OUT / "segmented_heading_summary.csv", summary_rows)
    _safe_json_dump(
        OUT / "segmented_heading_summary.json",
        {
            "scope": "Segmented-heading geometry diagnostic for complex terrain; not sea-trial evidence.",
            "elapsed_s": time.perf_counter() - start,
            "scenes": [scene.manifest_entry for scene in scenes],
            "hybrid_ga_seeds": list(seeds),
            "segment_counts": list(segment_counts),
            "segment_overlap_targets": list(overlap_targets),
            "min_turn_radius_m": float(args.min_turn_radius_m),
            "segment_candidate_top_k": int(args.segment_candidate_top_k),
            "acceptance_gate": {
                "target_coverage_pct": geo.TARGET_COVERAGE_PCT,
                "excess_overlap_feasible_pct": geo.EXCESS_OVERLAP_FEASIBLE_PCT,
                "coverage_regression_policy": "Reject segmentation when single-heading Hybrid GA is already feasible and segmentation lowers global coverage.",
            },
            "transition_aware_selector": {
                "radius_m": float(args.min_turn_radius_m),
                "survey_speed_mps": SURVEY_SPEED_MPS,
                "turn_speed_mps": TURN_SPEED_MPS,
                "overlap_weight_h_per_pct": TRANSITION_SELECTOR_OVERLAP_WEIGHT_H_PER_PCT,
                "objective": "mission_time_h + overlap_weight_h_per_pct * excess_overlap_pct after coverage/overlap acceptance gate",
            },
            "raw_rows": raw_rows,
            "summary_rows": summary_rows,
        },
    )
    make_figure(scenes, raw_rows, summary_rows)
    write_report(scenes, seeds, segment_counts, args.min_turn_radius_m, args.segment_candidate_top_k, summary_rows)
    print(
        json.dumps(
            {
                "out_dir": str(OUT),
                "rows": len(raw_rows),
                "summary_rows": len(summary_rows),
                "elapsed_s": round(time.perf_counter() - start, 3),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
