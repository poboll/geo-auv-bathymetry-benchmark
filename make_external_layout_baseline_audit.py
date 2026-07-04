from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

import geo_public_bathy_benchmark as geo
import journal_heatmap_style as jhs
import make_gebco_scene_expansion as gebco_expansion
import make_usgs_cascadia_pilot as pilot


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "external_layout_baseline_audit"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)
USGS_MANIFEST = ROOT / "usgs_cascadia_extension" / "public_scene_manifest.json"

HEADING_CANDIDATES_5 = tuple(range(0, 180, 5))
FIXED_WIDTH_QUANTILE = 0.30
EXTERNAL_METHODS = (
    "Min-Span Boustrophedon",
    "Contour-Parallel Fixed-Width",
    "Geometry-Shortest Fixed-Width",
)
REFERENCE_METHODS = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Hybrid GA Seed-0",
)
METHODS = (
    "Fixed-Spacing",
    *EXTERNAL_METHODS,
    "Adaptive Spacing w/o GA",
    "Hybrid GA Seed-0",
)
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Min-Span Boustrophedon": "Min-span",
    "Contour-Parallel Fixed-Width": "Contour",
    "Geometry-Shortest Fixed-Width": "Geom-short",
    "Adaptive Spacing w/o GA": "Adaptive",
    "Hybrid GA Seed-0": "Hybrid s0",
}
SCENE_LABELS = {
    "gebco_cascadia_margin_moderate": "GEBCO Cascadia",
    "gebco_monterey_canyon_complex": "GEBCO Monterey",
    "gebco_mariana_trench_complex": "GEBCO Mariana",
    "gebco_puerto_rico_trench_complex": "GEBCO Puerto Rico",
    "gebco_mid_atlantic_ridge_moderate": "GEBCO Mid-Atlantic",
    "gebco_hawaii_ridge_moderate": "GEBCO Hawaii",
    "usgs_southern_cascadia_30m_low": "USGS Low",
    "usgs_southern_cascadia_30m_medium": "USGS Medium",
    "usgs_southern_cascadia_30m_high": "USGS High",
}


def _safe_json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _load_usgs_scene_from_manifest(manifest: dict[str, Any]) -> geo.TerrainScene:
    raw_file = Path(manifest["raw_file"])
    if not raw_file.exists():
        pilot.ensure_extracted()
        raw_file = pilot.RASTER_PATH
    bounds = manifest["crop_bounds"]
    with rasterio.open(raw_file) as dataset:
        window = from_bounds(
            float(bounds["left"]),
            float(bounds["bottom"]),
            float(bounds["right"]),
            float(bounds["top"]),
            transform=dataset.transform,
        ).round_offsets().round_lengths()
        arr = dataset.read(
            1,
            window=window,
            out_shape=(geo.GRID_NY, geo.GRID_NX),
            masked=True,
            resampling=Resampling.bilinear,
        )
        depth = pilot.depth_from_masked(arr)
        depth, fill_info = geo._fill_depth_gaps(depth)
        crop_bounds = rasterio.windows.bounds(window, dataset.transform)
        width_m = float(crop_bounds[2] - crop_bounds[0])
        height_m = float(crop_bounds[3] - crop_bounds[1])
        x = np.linspace(0.0, width_m, geo.GRID_NX)
        y = np.linspace(0.0, height_m, geo.GRID_NY)
        xx, yy = np.meshgrid(x, y)
    merged = dict(manifest)
    merged["raw_file"] = str(raw_file)
    merged["missing_value_handling_recomputed"] = fill_info
    merged["diagnostic_rebuild_policy"] = (
        "Rebuilt from the crop bounds recorded in the USGS public-grid extension manifest."
    )
    return geo.TerrainScene(
        scene_id=str(manifest["scene_id"]),
        display_name=str(manifest["scene_id"]).replace("usgs_southern_cascadia_30m_", "USGS Cascadia 30 m ").title(),
        scene_group="public",
        terrain_class=str(manifest["terrain_class"]),
        x=xx,
        y=yy,
        z=depth,
        source=str(manifest["source"]),
        download_url=str(manifest["download_url"]),
        raw_file=str(raw_file),
        manifest_entry=merged,
    )


def load_public_audit_scenes() -> list[geo.TerrainScene]:
    scenes = [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]
    scenes.extend(geo.load_public_scene(spec, ROOT) for spec in gebco_expansion.EXTRA_GEBCO_SPECS)
    usgs_items = json.loads(USGS_MANIFEST.read_text(encoding="utf-8"))
    scenes.extend(_load_usgs_scene_from_manifest(item) for item in usgs_items)
    return scenes


def _nearest_heading_5(angle_deg: float) -> float:
    angle = float(angle_deg) % 180.0
    snapped = round(angle / 5.0) * 5.0
    return float(snapped % 180.0)


def _cross_track_span(scene: geo.TerrainScene, orientation_deg: float) -> float:
    context = geo.make_context(scene, orientation_deg)
    return float(context.vmax - context.vmin)


def _fixed_width_positions(
    scene: geo.TerrainScene,
    orientation_deg: float,
    *,
    quantile: float = FIXED_WIDTH_QUANTILE,
) -> tuple[np.ndarray, float, float]:
    context = geo.make_context(scene, orientation_deg)
    swath_ref = float(np.quantile(context.swath_width, quantile))
    spacing = swath_ref * (1.0 - geo.TARGET_OVERLAP)
    positions = geo.uniform_line_positions(context.vmin, context.vmax, spacing, swath_ref)
    return positions, swath_ref, spacing


def _evaluate_fixed_width(
    scene: geo.TerrainScene,
    method: str,
    orientation_deg: float,
    planning_time_s: float,
) -> tuple[geo.PlanResult, dict[str, Any]]:
    positions, swath_ref, spacing = _fixed_width_positions(scene, orientation_deg)
    result = geo.evaluate_plan(scene, method, 0, orientation_deg, positions, planning_time_s)
    details = {
        "spacing_policy": f"scene-wide q{FIXED_WIDTH_QUANTILE:.2f} swath times target non-overlap",
        "swath_quantile": FIXED_WIDTH_QUANTILE,
        "swath_ref_m": float(swath_ref),
        "spacing_m": float(spacing),
    }
    return result, details


def min_span_boustrophedon_plan(scene: geo.TerrainScene) -> tuple[geo.PlanResult, dict[str, Any]]:
    start = time.perf_counter()
    spans = {float(angle): _cross_track_span(scene, float(angle)) for angle in HEADING_CANDIDATES_5}
    orientation = min(spans, key=spans.get)
    result, details = _evaluate_fixed_width(scene, "Min-Span Boustrophedon", orientation, time.perf_counter() - start)
    details.update(
        {
            "heading_policy": "Choose the heading with minimum cross-track span on a 5-degree grid.",
            "selected_span_m": float(spans[orientation]),
            "span_min_m": float(min(spans.values())),
            "span_max_m": float(max(spans.values())),
        }
    )
    return result, details


def _dominant_contour_heading(scene: geo.TerrainScene) -> float:
    dx = float(scene.x[0, 1] - scene.x[0, 0])
    dy = float(scene.y[1, 0] - scene.y[0, 0])
    dz_dy, dz_dx = np.gradient(scene.z, dy, dx)
    slope = np.hypot(dz_dx, dz_dy)
    finite = np.isfinite(slope)
    if not np.any(finite):
        return 0.0
    slope = np.where(finite, slope, 0.0)
    cutoff = float(np.percentile(slope[finite], 95))
    weights = np.clip(slope, 0.0, cutoff)
    if float(np.sum(weights)) <= 1e-12:
        return 0.0
    gradient_angle = np.arctan2(dz_dy, dz_dx)
    contour_angle = gradient_angle + 0.5 * np.pi
    vector = np.sum(weights * np.exp(2j * contour_angle))
    if abs(vector) <= 1e-12:
        return 0.0
    return _nearest_heading_5(math.degrees(0.5 * math.atan2(vector.imag, vector.real)))


def contour_parallel_plan(scene: geo.TerrainScene) -> tuple[geo.PlanResult, dict[str, Any]]:
    start = time.perf_counter()
    orientation = _dominant_contour_heading(scene)
    result, details = _evaluate_fixed_width(
        scene,
        "Contour-Parallel Fixed-Width",
        orientation,
        time.perf_counter() - start,
    )
    details.update(
        {
            "heading_policy": (
                "Estimate the dominant terrain-gradient direction, rotate by 90 degrees, "
                "and snap the contour-parallel line heading to the nearest 5 degrees."
            ),
            "dominant_contour_heading_deg": float(orientation),
        }
    )
    return result, details


def geometry_shortest_plan(scene: geo.TerrainScene) -> tuple[geo.PlanResult, dict[str, Any]]:
    start = time.perf_counter()
    candidates: list[tuple[float, float, np.ndarray, float, float]] = []
    for angle in HEADING_CANDIDATES_5:
        positions, swath_ref, spacing = _fixed_width_positions(scene, float(angle))
        context = geo.make_context(scene, float(angle))
        length = geo.plan_length_km(scene, positions, context.phi_rad)
        candidates.append((length, float(angle), positions, swath_ref, spacing))
    length, orientation, positions, swath_ref, spacing = min(candidates, key=lambda item: item[0])
    result = geo.evaluate_plan(
        scene,
        "Geometry-Shortest Fixed-Width",
        0,
        orientation,
        positions,
        time.perf_counter() - start,
    )
    details = {
        "heading_policy": (
            "Scan 5-degree headings and select the shortest fixed-width lawnmower distance; "
            "coverage and overlap are audited after selection, not used to choose the heading."
        ),
        "spacing_policy": f"scene-wide q{FIXED_WIDTH_QUANTILE:.2f} swath times target non-overlap",
        "swath_quantile": FIXED_WIDTH_QUANTILE,
        "swath_ref_m": float(swath_ref),
        "spacing_m": float(spacing),
        "selected_geometry_length_km": float(length),
    }
    return result, details


def collect_plans(scene: geo.TerrainScene) -> list[tuple[geo.PlanResult, dict[str, Any]]]:
    fixed = geo.fixed_spacing_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    hybrid_seed0 = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed=0)
    hybrid_seed0 = geo.PlanResult(
        scene_id=hybrid_seed0.scene_id,
        scene_name=hybrid_seed0.scene_name,
        scene_group=hybrid_seed0.scene_group,
        terrain_class=hybrid_seed0.terrain_class,
        method="Hybrid GA Seed-0",
        seed=0,
        orientation_deg=hybrid_seed0.orientation_deg,
        line_positions=hybrid_seed0.line_positions,
        coverage_pct=hybrid_seed0.coverage_pct,
        excess_overlap_pct=hybrid_seed0.excess_overlap_pct,
        path_length_km=hybrid_seed0.path_length_km,
        planning_time_s=hybrid_seed0.planning_time_s,
        feasible=hybrid_seed0.feasible,
    )
    return [
        (fixed, {"heading_policy": "Reference 0-degree fixed-spacing plan from the main benchmark."}),
        min_span_boustrophedon_plan(scene),
        contour_parallel_plan(scene),
        geometry_shortest_plan(scene),
        (adaptive, {"heading_policy": "Deterministic terrain-aware adaptive-spacing baseline."}),
        (hybrid_seed0, {"heading_policy": "Representative seed-0 local GA cleanup from the adaptive base."}),
    ]


def result_row(result: geo.PlanResult, details: dict[str, Any], fixed: geo.PlanResult) -> dict[str, Any]:
    return {
        "scene_id": result.scene_id,
        "scene_label": SCENE_LABELS.get(result.scene_id, result.scene_name),
        "scene_name": result.scene_name,
        "terrain_class": result.terrain_class,
        "method": result.method,
        "method_label": METHOD_LABELS.get(result.method, result.method),
        "method_family": "external_heuristic" if result.method in EXTERNAL_METHODS else "paper_reference",
        "seed": int(result.seed),
        "orientation_deg": float(result.orientation_deg),
        "line_count": int(result.line_count),
        "path_length_km": float(result.path_length_km),
        "path_gain_vs_fixed_pct": float((fixed.path_length_km - result.path_length_km) / max(fixed.path_length_km, 1e-9) * 100.0),
        "coverage_pct": float(result.coverage_pct),
        "coverage_delta_vs_fixed_pp": float(result.coverage_pct - fixed.coverage_pct),
        "excess_overlap_pct": float(result.excess_overlap_pct),
        "overlap_cleanup_vs_fixed_pp": float(fixed.excess_overlap_pct - result.excess_overlap_pct),
        "score": float(geo.plan_score(result.path_length_km, result.coverage_pct, result.excess_overlap_pct)),
        "feasible_C97_O3": int(result.feasible),
        "planning_time_s": float(result.planning_time_s),
        "heading_policy": str(details.get("heading_policy", "")),
        "spacing_policy": str(details.get("spacing_policy", "")),
        "swath_quantile": details.get("swath_quantile", ""),
        "swath_ref_m": details.get("swath_ref_m", ""),
        "spacing_m": details.get("spacing_m", ""),
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for method in METHODS:
        group = [row for row in rows if row["method"] == method]
        if not group:
            continue
        record: dict[str, Any] = {
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "method_family": group[0]["method_family"],
            "n_public_windows": len(group),
            "feasible_windows_C97_O3": int(sum(int(row["feasible_C97_O3"]) for row in group)),
        }
        for key in (
            "path_gain_vs_fixed_pct",
            "coverage_pct",
            "coverage_delta_vs_fixed_pp",
            "excess_overlap_pct",
            "overlap_cleanup_vs_fixed_pp",
            "score",
            "line_count",
        ):
            values = np.asarray([float(row[key]) for row in group], dtype=float)
            record[f"{key}_mean"] = float(np.mean(values))
            record[f"{key}_median"] = float(np.median(values))
            record[f"{key}_min"] = float(np.min(values))
            record[f"{key}_max"] = float(np.max(values))
            record[f"{key}_q25"] = float(np.percentile(values, 25))
            record[f"{key}_q75"] = float(np.percentile(values, 75))
        out.append(record)
    return out


def make_figure(rows: list[dict[str, Any]]) -> None:
    jhs.apply_rc(base_font=8.45)
    method_order = [method for method in METHODS if method != "Fixed-Spacing"]
    scene_order = list(dict.fromkeys(row["scene_id"] for row in rows))
    matrices = []
    for key, title, cmap, norm, fmt, mark_bad in [
        (
            "path_gain_vs_fixed_pct",
            "(a) Path gain vs fixed (%)",
            jhs.PATH_GAIN_CMAP,
            mcolors.TwoSlopeNorm(vmin=-8.0, vcenter=0.0, vmax=28.0),
            "{:+.1f}",
            lambda value: value < 0.0,
        ),
        (
            "coverage_pct",
            "(b) Predicted coverage (%)",
            jhs.COVERAGE_CMAP,
            mcolors.TwoSlopeNorm(vmin=94.0, vcenter=97.0, vmax=100.0),
            "{:.1f}",
            lambda value: value < 97.0,
        ),
        (
            "excess_overlap_pct",
            "(c) Mean excess overlap (%)",
            jhs.FAILURE_CMAP,
            mcolors.Normalize(vmin=0.0, vmax=30.0),
            "{:.1f}",
            lambda value: value > 3.0,
        ),
        (
            "feasible_C97_O3",
            "(d) Pass C97/O3",
            jhs.COVERAGE_CMAP,
            mcolors.Normalize(vmin=0.0, vmax=1.0),
            "{:.0f}",
            lambda value: value < 1.0,
        ),
    ]:
        data = np.full((len(scene_order), len(method_order)), np.nan)
        for i, scene_id in enumerate(scene_order):
            for j, method in enumerate(method_order):
                match = [row for row in rows if row["scene_id"] == scene_id and row["method"] == method]
                if match:
                    data[i, j] = float(match[0][key])
        matrices.append((data, title, cmap, norm, fmt, mark_bad))

    fig, axes_grid = plt.subplots(2, 2, figsize=(7.60, 5.35), facecolor="white")
    axes = list(axes_grid.flat)
    ylabels = [SCENE_LABELS.get(scene_id, scene_id).replace("GEBCO ", "G. ").replace("USGS ", "U. ") for scene_id in scene_order]
    xlabels = [METHOD_LABELS[method] for method in method_order]
    for ax_idx, (ax, (data, title, cmap, norm, fmt, mark_bad)) in enumerate(zip(axes, matrices)):
        ax.imshow(data, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        jhs.style_heatmap_axis(
            ax,
            title,
            xlabels,
            ylabels if ax_idx in (0, 2) else None,
            data.shape[0],
            rotate_x=0,
        )
        jhs.annotate_cells(ax, data, cmap, norm, fmt, mark_bad=mark_bad, fontsize=6.35)
        for y in np.arange(0.5, data.shape[0], 1.0):
            ax.axhline(y, color="white", linewidth=0.64)
        for x in np.arange(0.5, data.shape[1], 1.0):
            ax.axvline(x, color="white", linewidth=0.64)
    fig.text(
        0.012,
        0.013,
        "External heuristics are deterministic fixed-width line-layout audits, not full reproductions of field-ready CPP systems.",
        ha="left",
        va="bottom",
        fontsize=6.2,
        color=jhs.MUTED,
    )
    fig.subplots_adjust(left=0.096, right=0.997, top=0.940, bottom=0.070, wspace=0.064, hspace=0.188)
    out_path = OUT / "journal_external_layout_baseline_audit.png"
    jhs.save_white_rgb(fig, out_path, dpi=430, pad_inches=0.025)
    for pic_dir in PIC_DIRS:
        jhs.save_white_rgb(fig, pic_dir / "journal_external_layout_baseline_audit.png", dpi=430, pad_inches=0.025)
    plt.close(fig)


def write_report(summary_rows: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    best_external_by_scene: list[dict[str, Any]] = []
    for scene_id in sorted({row["scene_id"] for row in rows}):
        ext_rows = [row for row in rows if row["scene_id"] == scene_id and row["method"] in EXTERNAL_METHODS]
        best = min(ext_rows, key=lambda row: float(row["score"]))
        best_external_by_scene.append(best)
    lines = [
        "# External Survey-layout Heuristic Baseline Audit\n\n",
        "This diagnostic responds to the reviewer risk that the manuscript only compares variants inside the same proposed family. ",
        "It does not claim to reproduce complete field-ready coverage-path-planning systems. ",
        "Instead, it implements three deterministic survey-layout heuristics under the same raster MBES evaluator and audits them against the paper's fixed/adaptive references.\n\n",
        "## External heuristics\n\n",
        "- **Min-Span Boustrophedon:** choose the 5-degree heading with minimum cross-track span, then use a scene-wide q0.30 fixed-width spacing.\n",
        "- **Contour-Parallel Fixed-Width:** estimate the dominant contour-parallel heading from the bathymetric gradient, snap to 5 degrees, then use the same fixed-width spacing.\n",
        "- **Geometry-Shortest Fixed-Width:** scan 5-degree headings and choose the shortest fixed-width lawnmower distance before auditing coverage and overlap.\n\n",
        "## Summary\n\n",
        "| Method | Feasible windows | Median path gain (%) | Median coverage (%) | Median excess overlap (%) | Median overlap cleanup (pp) |\n",
        "|---|---:|---:|---:|---:|---:|\n",
    ]
    for row in summary_rows:
        if row["method"] == "Fixed-Spacing":
            continue
        lines.append(
            f"| {row['method_label']} | {row['feasible_windows_C97_O3']}/{row['n_public_windows']} | "
            f"{row['path_gain_vs_fixed_pct_median']:.3f} | {row['coverage_pct_median']:.2f} | "
            f"{row['excess_overlap_pct_median']:.3f} | {row['overlap_cleanup_vs_fixed_pp_median']:.3f} |\n"
        )
    lines.extend(
        [
            "\n## Best external heuristic by scene\n\n",
            "| Scene | Best external heuristic | Score | Coverage (%) | Excess overlap (%) | Path gain (%) |\n",
            "|---|---|---:|---:|---:|---:|\n",
        ]
    )
    for row in best_external_by_scene:
        lines.append(
            f"| {row['scene_label']} | {row['method_label']} | {float(row['score']):.2f} | "
            f"{float(row['coverage_pct']):.2f} | {float(row['excess_overlap_pct']):.3f} | "
            f"{float(row['path_gain_vs_fixed_pct']):.3f} |\n"
        )
    lines.extend(
        [
            "\n## Interpretation boundary\n\n",
            "- The audit is a compact external-style baseline layer; it is not an implementation of a full Zhao/Bai-style multi-objective, vehicle-dynamics, or field-validated planner.\n",
            "- If an external heuristic wins a scene, that result should be reported rather than hidden; the manuscript claim is terrain-aware fixed-line spacing, not global broad-baseline dominance.\n",
            "- The main comparator remains the deterministic Adaptive Spacing layout, with Hybrid GA treated as local seed-0 cleanup in this audit and as a 50-seed method in the main benchmark.\n",
        ]
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = load_public_audit_scenes()
    rows: list[dict[str, Any]] = []
    manifests = []
    for scene in scenes:
        print(f"auditing {scene.scene_id}", flush=True)
        manifests.append(scene.manifest_entry)
        plans = collect_plans(scene)
        fixed = next(result for result, _ in plans if result.method == "Fixed-Spacing")
        for result, details in plans:
            rows.append(result_row(result, details, fixed))
    summary_rows = summarize(rows)
    _write_csv(OUT / "external_layout_baseline_raw.csv", rows)
    _write_csv(OUT / "external_layout_baseline_summary.csv", summary_rows)
    _safe_json_dump(
        OUT / "external_layout_baseline_summary.json",
        {
            "scope": (
                "External-style deterministic fixed-width survey-layout heuristic audit on nine public-grid windows; "
                "not a full reproduction of broader CPP systems or a deployment validation."
            ),
            "heading_grid_deg": 5,
            "fixed_width_quantile": FIXED_WIDTH_QUANTILE,
            "methods": list(METHODS),
            "scene_manifest": manifests,
            "summary_rows": summary_rows,
            "raw_rows": rows,
        },
    )
    make_figure(rows)
    write_report(summary_rows, rows)
    print(json.dumps({"out_dir": str(OUT), "raw_rows": len(rows), "summary_rows": len(summary_rows)}, indent=2))


if __name__ == "__main__":
    main()
