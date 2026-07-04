from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window

import geo_public_bathy_benchmark as geo


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "usgs_cascadia_pilot"
ZIP_PATH = ROOT / "public_bathy/raw/usgs/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2.zip"
EXTRACT_DIR = ROOT / "public_bathy/raw/usgs/SouthernCascadia_30m_bathy_UTM10N_NAD83_v2"
RASTER_PATH = EXTRACT_DIR / "SouthernCascadia_30m_bathy_UTM10N_NAD83_v2.tif"


def ensure_extracted() -> None:
    if RASTER_PATH.exists():
        return
    if not ZIP_PATH.exists():
        raise FileNotFoundError(
            f"Missing {ZIP_PATH}. Download the USGS Southern Cascadia v2 GeoTIFF zip before running this pilot."
        )
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        archive.extractall(EXTRACT_DIR)


def depth_from_masked(arr: np.ma.MaskedArray) -> np.ndarray:
    raw = np.asarray(arr.astype(float).filled(np.nan), dtype=float)
    raw[raw > 1e20] = np.nan
    finite = np.isfinite(raw)
    if not finite.any():
        raise ValueError("No finite bathymetry values in crop.")
    # USGS bathymetry is negative below the sea surface.
    if float(np.nanmedian(raw[finite])) < 0:
        depth = -raw
        depth[raw >= 0] = np.nan
    else:
        depth = raw.copy()
        depth[raw <= 0] = np.nan
    return depth


def candidate_complexity(depth: np.ndarray, xres: float, yres: float) -> dict[str, float] | None:
    valid = np.isfinite(depth)
    valid_fraction = float(np.mean(valid))
    if valid_fraction < 0.985:
        return None
    filled = np.where(valid, depth, np.nanmedian(depth[valid]))
    gy, gx = np.gradient(filled, yres, xres)
    slope = np.hypot(gx, gy)
    relief = float(np.nanmax(filled) - np.nanmin(filled))
    std = float(np.nanstd(filled))
    complexity = float(np.nanmean(slope) + 0.015 * std + 0.010 * relief)
    return {
        "valid_fraction": valid_fraction,
        "slope_mean": float(np.nanmean(slope)),
        "depth_std": std,
        "relief": relief,
        "complexity": complexity,
    }


def choose_physical_crop(dataset: rasterio.io.DatasetReader) -> tuple[Window, dict[str, float]]:
    xres = abs(float(dataset.transform.a))
    yres = abs(float(dataset.transform.e))
    crop_w = max(geo.GRID_NX, int(round(geo.PUBLIC_CROP_WIDTH_M / xres)))
    crop_h = max(geo.GRID_NY, int(round(geo.PUBLIC_CROP_HEIGHT_M / yres)))

    overview_w = 1000
    overview_h = max(1, int(round(dataset.height * overview_w / dataset.width)))
    overview = dataset.read(1, out_shape=(overview_h, overview_w), masked=True, resampling=Resampling.nearest)
    overview_depth = depth_from_masked(overview)
    overview_valid = np.isfinite(overview_depth)

    scale_x = dataset.width / overview_w
    scale_y = dataset.height / overview_h
    crop_w_overview = max(2, int(round(crop_w / scale_x)))
    crop_h_overview = max(2, int(round(crop_h / scale_y)))
    step_x = max(3, crop_w_overview * 2)
    step_y = max(3, crop_h_overview * 2)

    candidates: list[tuple[float, Window, dict[str, float]]] = []
    for oy in range(0, max(overview_h - crop_h_overview, 1), step_y):
        for ox in range(0, max(overview_w - crop_w_overview, 1), step_x):
            patch_valid = overview_valid[oy : oy + crop_h_overview, ox : ox + crop_w_overview]
            if patch_valid.size == 0 or float(np.mean(patch_valid)) < 0.90:
                continue
            center_col = int(round((ox + 0.5 * crop_w_overview) * scale_x))
            center_row = int(round((oy + 0.5 * crop_h_overview) * scale_y))
            col = min(max(center_col - crop_w // 2, 0), dataset.width - crop_w)
            row = min(max(center_row - crop_h // 2, 0), dataset.height - crop_h)
            window = Window(col, row, crop_w, crop_h)
            arr = dataset.read(1, window=window, masked=True)
            depth = depth_from_masked(arr)
            metrics = candidate_complexity(depth, xres, yres)
            if metrics is None:
                continue
            candidates.append((metrics["complexity"], window, metrics))

    if not candidates:
        raise RuntimeError("No fully valid public-grid pilot crop found.")
    candidates.sort(key=lambda item: item[0])
    # Pick a high-complexity but not extreme crop so the pilot is informative without being a pathological edge case.
    idx = int(round(0.72 * (len(candidates) - 1)))
    _, window, metrics = candidates[idx]
    metrics = dict(metrics)
    metrics["candidate_count"] = len(candidates)
    metrics["complexity_quantile"] = 0.72
    return window, metrics


def load_usgs_scene() -> geo.TerrainScene:
    ensure_extracted()
    with rasterio.open(RASTER_PATH) as dataset:
        window, metrics = choose_physical_crop(dataset)
        arr = dataset.read(
            1,
            window=window,
            out_shape=(geo.GRID_NY, geo.GRID_NX),
            masked=True,
            resampling=Resampling.bilinear,
        )
        depth = depth_from_masked(arr)
        depth, fill_info = geo._fill_depth_gaps(depth)
        bounds = rasterio.windows.bounds(window, dataset.transform)
        width_m = float(bounds[2] - bounds[0])
        height_m = float(bounds[3] - bounds[1])
        x = np.linspace(0.0, width_m, geo.GRID_NX)
        y = np.linspace(0.0, height_m, geo.GRID_NY)
        xx, yy = np.meshgrid(x, y)
        manifest = {
            "scene_id": "usgs_southern_cascadia_30m_pilot",
            "source": "USGS Southern Cascadia 30 m composite bathymetry, v2",
            "download_url": "https://doi.org/10.5066/P9C5DBMR",
            "license": "USGS public data release",
            "raw_file": str(RASTER_PATH),
            "crop_bounds": {
                "left": float(bounds[0]),
                "bottom": float(bounds[1]),
                "right": float(bounds[2]),
                "top": float(bounds[3]),
                "crs": dataset.crs.to_string() if dataset.crs else None,
            },
            "raw_resolution_m": {
                "x": abs(float(dataset.transform.a)),
                "y": abs(float(dataset.transform.e)),
            },
            "planner_grid_resolution_m": round(max(width_m / max(geo.GRID_NX - 1, 1), height_m / max(geo.GRID_NY - 1, 1)), 3),
            "depth_range_m": [float(np.nanmin(depth)), float(np.nanmax(depth))],
            "terrain_class": "usgs_cascadia_pilot",
            "selection_metrics": metrics,
            "missing_value_handling": fill_info,
            "provider": "USGS",
            "pilot_policy": "Not mixed into run_5; used only to test public-grid ingestion feasibility.",
        }
    return geo.TerrainScene(
        scene_id=manifest["scene_id"],
        display_name="USGS Southern Cascadia 30 m Pilot",
        scene_group="public",
        terrain_class=manifest["terrain_class"],
        x=xx,
        y=yy,
        z=depth,
        source=manifest["source"],
        download_url=manifest["download_url"],
        raw_file=str(RASTER_PATH),
        manifest_entry=manifest,
    )


def run_pilot(scene: geo.TerrainScene, seeds: tuple[int, ...] = (0, 1, 2, 3, 4)) -> list[geo.PlanResult]:
    results: list[geo.PlanResult] = []
    fixed = geo.fixed_spacing_plan(scene)
    greedy, greedy_base = geo.simple_greedy_plan(scene)
    adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
    results.extend([fixed, greedy, adaptive])
    for seed in seeds:
        results.append(geo.fixed_swath_ga_plan(scene, greedy_base, seed))
        results.append(geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed))
    return results


def positions_for_preview(line_positions: np.ndarray, max_lines: int = 12) -> np.ndarray:
    if len(line_positions) <= max_lines:
        return np.asarray(line_positions, dtype=float)
    idx = np.linspace(0, len(line_positions) - 1, max_lines).round().astype(int)
    return np.asarray(line_positions, dtype=float)[np.unique(idx)]


def save_preview(scene: geo.TerrainScene, results: list[geo.PlanResult]) -> None:
    methods = ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]
    chosen = {method: next(row for row in results if row.method == method) for method in methods}
    fig, axes = plt.subplots(1, 3, figsize=(8.0, 2.8), facecolor="white", sharex=True, sharey=True)
    extent = (scene.x.min() / geo.NM_TO_M, scene.x.max() / geo.NM_TO_M, scene.y.min() / geo.NM_TO_M, scene.y.max() / geo.NM_TO_M)
    for ax, method in zip(axes, methods):
        ax.imshow(scene.z, extent=extent, origin="lower", cmap=geo.BATHY_CMAP, aspect="equal")
        result = chosen[method]
        phi = math.radians(result.orientation_deg)
        for pos in positions_for_preview(result.line_positions, max_lines=12):
            xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
            if xs.size:
                ax.plot(xs / geo.NM_TO_M, ys / geo.NM_TO_M, color=geo.METHOD_COLORS[method], lw=0.9, alpha=0.9)
        ax.set_title(f"{method}\n{result.orientation_deg:.0f} deg, n={result.line_count}, C={result.coverage_pct:.1f}%, O={result.excess_overlap_pct:.2f}%")
        ax.set_xlabel("NM")
    axes[0].set_ylabel("NM")
    fig.tight_layout()
    fig.savefig(OUT / "usgs_cascadia_pilot_layouts.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = load_usgs_scene()
    results = run_pilot(scene)
    summary_rows = geo.summarize_results(results)
    geo.write_results_tables(OUT, results, summary_rows)
    geo.write_public_manifest(OUT, [scene])
    means, stderrs, final_info = geo.build_final_info(summary_rows)
    geo.write_summary_bundle(OUT, results, summary_rows, [scene.manifest_entry], means, stderrs)
    np.save(OUT / "all_results.npy", final_info, allow_pickle=True)
    save_preview(scene, results)
    (OUT / "README.md").write_text(
        "# USGS Southern Cascadia 30 m pilot\n\n"
        "This is a public-grid ingestion feasibility probe. It is not mixed into `run_5` and is not yet a manuscript result.\n\n"
        f"- Source raster: `{RASTER_PATH}`\n"
        "- Source DOI: https://doi.org/10.5066/P9C5DBMR\n"
        "- Seeds: 0--4 for stochastic GA methods\n"
        "- Output: `benchmark_method_statistics.csv`, `benchmark_results.csv`, `public_scene_manifest.json`, and `usgs_cascadia_pilot_layouts.png`\n",
        encoding="utf-8",
    )
    print(json.dumps({"out_dir": str(OUT), "means": means, "manifest": scene.manifest_entry}, indent=2))


if __name__ == "__main__":
    main()
