import argparse
import csv
import json
import math
import os
import os.path as osp
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", osp.join(tempfile.gettempdir(), "mplconfig_geo_public_bathy"))
os.environ.setdefault("XDG_CACHE_HOME", tempfile.gettempdir())

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import requests
import rasterio
from matplotlib.colors import LinearSegmentedColormap, LightSource
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle
from rasterio.enums import Resampling
from rasterio.windows import Window

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "dejavuserif",
    }
)

NM_TO_M = 1852.0
SYNTH_WIDTH_M = 4.0 * NM_TO_M
SYNTH_HEIGHT_M = 5.0 * NM_TO_M
PUBLIC_CROP_WIDTH_M = SYNTH_WIDTH_M
PUBLIC_CROP_HEIGHT_M = SYNTH_HEIGHT_M
GRID_NX = 120
GRID_NY = 150
GA_EVAL_STRIDE = 3
TARGET_OVERLAP = 0.15
TARGET_COVERAGE_PCT = 97.0
EXCESS_OVERLAP_FEASIBLE_PCT = 3.0
BEAM_ANGLE_DEG = 120.0
CONSTANT_QUANTILES = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)
ADAPTIVE_QUANTILES = (0.20, 0.25, 0.30, 0.35)
ANGLE_CANDIDATES = tuple(range(0, 180, 15))
GA_SEEDS = tuple(range(20))
GA_GENERATIONS = 10
GA_POP_SIZE = 10
MIN_PUBLIC_VALID_FRAC = 0.985
OVERVIEW_MAX_SIDE = 420

PAPER_BG = "#ffffff"
PAPER_AX_BG = "#ffffff"
PAPER_GRID = "#d9e2ea"
PAPER_LINE = "#cfd9e3"
PAPER_TEXT = "#18232f"
PAPER_MUTED = "#667789"
PANEL_EDGE = "#d2dce6"
SYNTH_ACCENT = "#bc6131"
PUBLIC_ACCENT = "#175d73"
GROUP_COLORS = {"synthetic": SYNTH_ACCENT, "public": PUBLIC_ACCENT}
METHOD_COLORS = {
    "Fixed-Spacing": "#7b7f8a",
    "Simple Greedy": "#9c6ade",
    "Adaptive Spacing w/o GA": "#2a9d8f",
    "Fixed-Swath GA": "#d94896",
    "Full Geometry-Aware Hybrid GA": "#c26a3d",
}
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed spacing",
    "Simple Greedy": "Greedy",
    "Adaptive Spacing w/o GA": "Adaptive only",
    "Fixed-Swath GA": "Fixed-swath GA",
    "Full Geometry-Aware Hybrid GA": "Hybrid GA",
}
BATHY_CMAP = LinearSegmentedColormap.from_list(
    "paper_bathy",
    ["#eef8fc", "#c9ebf3", "#83d0e2", "#3e97c0", "#1a567f", "#081c30"],
)
BATHY_LIGHT = LightSource(azdeg=315, altdeg=38)


@dataclass(frozen=True)
class PublicSceneSpec:
    scene_id: str
    display_name: str
    provider: str
    terrain_class: str
    download_url: str
    bbox: tuple[float, float, float, float] | None = None
    tile_id: str | None = None
    selection_quantile: float | None = None
    source: str = ""
    license: str = ""


@dataclass
class TerrainScene:
    scene_id: str
    display_name: str
    scene_group: str
    terrain_class: str
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    source: str
    download_url: str | None
    raw_file: str | None
    manifest_entry: dict[str, Any]

    @property
    def width_m(self) -> float:
        return float(self.x[0, -1] - self.x[0, 0]) if self.x.shape[1] > 1 else 0.0

    @property
    def height_m(self) -> float:
        return float(self.y[-1, 0] - self.y[0, 0]) if self.y.shape[0] > 1 else 0.0


@dataclass
class CrossTrackContext:
    phi_rad: float
    v_grid: np.ndarray
    swath_width: np.ndarray
    vmin: float
    vmax: float


@dataclass
class LayoutCandidate:
    orientation_deg: float
    line_positions: np.ndarray
    coverage_pct: float
    excess_overlap_pct: float
    score: float


@dataclass
class PlanResult:
    scene_id: str
    scene_name: str
    scene_group: str
    terrain_class: str
    method: str
    seed: int
    orientation_deg: float
    line_positions: np.ndarray
    coverage_pct: float
    excess_overlap_pct: float
    path_length_km: float
    planning_time_s: float
    feasible: bool

    @property
    def line_count(self) -> int:
        return int(len(self.line_positions))


PUBLIC_SCENE_SPECS: tuple[PublicSceneSpec, ...] = (
    PublicSceneSpec(
        scene_id="gebco_cascadia_margin_moderate",
        display_name="GEBCO Cascadia Margin",
        provider="gebco",
        terrain_class="moderate_slope",
        download_url="https://download.gebco.net",
        bbox=(-126.8, -125.2, 43.2, 44.8),
        source="GEBCO 2025 global bathymetry subset",
        license="GEBCO 2025 Grid terms of use",
    ),
    PublicSceneSpec(
        scene_id="gebco_monterey_canyon_complex",
        display_name="GEBCO Monterey Canyon",
        provider="gebco",
        terrain_class="complex_relief",
        download_url="https://download.gebco.net",
        bbox=(-123.3, -122.3, 35.3, 36.3),
        source="GEBCO 2025 global bathymetry subset",
        license="GEBCO 2025 Grid terms of use",
    ),
)


def terrain_generators(nx: int = GRID_NX, ny: int = GRID_NY) -> list[TerrainScene]:
    x = np.linspace(0.0, SYNTH_WIDTH_M, nx)
    y = np.linspace(0.0, SYNTH_HEIGHT_M, ny)
    xx, yy = np.meshgrid(x, y)

    flat = np.full_like(xx, 120.0)

    slope = 60.0 + 170.0 * (0.55 * xx / SYNTH_WIDTH_M + 0.45 * yy / SYNTH_HEIGHT_M)

    main_slope = 10.0 + (250.0 - 10.0) * (0.60 * xx / SYNTH_WIDTH_M + 0.40 * yy / SYNTH_HEIGHT_M)
    variation_1 = 30.0 * np.sin(2.0 * np.pi * xx / (0.75 * SYNTH_WIDTH_M)) * np.cos(
        2.0 * np.pi * yy / (0.80 * SYNTH_HEIGHT_M)
    )
    variation_2 = 20.0 * np.sin(2.0 * np.pi * yy / (0.40 * SYNTH_HEIGHT_M))
    depression = -40.0 * np.exp(
        -(((xx - 0.38 * SYNTH_WIDTH_M) ** 2) + ((yy - 0.72 * SYNTH_HEIGHT_M) ** 2))
        / (0.07 * SYNTH_WIDTH_M * SYNTH_HEIGHT_M)
    )
    seamount = 25.0 * np.exp(
        -(((xx - 0.76 * SYNTH_WIDTH_M) ** 2) + ((yy - 0.28 * SYNTH_HEIGHT_M) ** 2))
        / (0.04 * SYNTH_WIDTH_M * SYNTH_HEIGHT_M)
    )
    complex_z = np.clip(main_slope + variation_1 + variation_2 + depression + seamount, 10.0, 280.0)

    scenes = [
        ("synthetic_flat", "Flat Seafloor", "flat"),
        ("synthetic_uniform_slope", "Uniform Slope", "moderate_slope"),
        ("synthetic_complex", "Complex Terrain", "complex_relief"),
    ]
    arrays = [flat, slope, complex_z]
    return [
        TerrainScene(
            scene_id=scene_id,
            display_name=name,
            scene_group="synthetic",
            terrain_class=terrain_class,
            x=xx.copy(),
            y=yy.copy(),
            z=z.copy(),
            source="Synthetic benchmark",
            download_url=None,
            raw_file=None,
            manifest_entry={
                "scene_id": scene_id,
                "source": "Synthetic benchmark",
                "download_url": None,
                "license": None,
                "raw_file": None,
                "crop_bounds": {
                    "left": 0.0,
                    "right": SYNTH_WIDTH_M,
                    "bottom": 0.0,
                    "top": SYNTH_HEIGHT_M,
                    "crs": "local_planar_m",
                },
                "resolution_m": round(max(SYNTH_WIDTH_M / max(nx - 1, 1), SYNTH_HEIGHT_M / max(ny - 1, 1)), 3),
                "depth_range_m": [float(np.min(z)), float(np.max(z))],
                "terrain_class": terrain_class,
                "missing_value_handling": "not_applicable",
            },
        )
        for (scene_id, name, terrain_class), z in zip(scenes, arrays)
    ]


def _stderr(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    arr = np.asarray(values, dtype=float)
    return float(arr.std(ddof=1) / math.sqrt(len(arr)))


def output_dir(out_dir: Path | str) -> Path:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _shared_public_root(workspace_root: Path | str) -> Path:
    root = Path(workspace_root) / "public_bathy"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _public_raw_dir(workspace_root: Path | str) -> Path:
    path = _shared_public_root(workspace_root) / "raw" / "noaa"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _public_cache_dir(workspace_root: Path | str) -> Path:
    path = _shared_public_root(workspace_root) / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, ensure_ascii=False)


def _download_with_resume(url: str, dest: Path, timeout_s: int = 120) -> int:
    session = requests.Session()
    session.trust_env = False
    expected_size = 0
    head = session.head(url, allow_redirects=True, timeout=timeout_s)
    head.raise_for_status()
    if head.headers.get("Content-Length"):
        expected_size = int(head.headers["Content-Length"])

    current_size = dest.stat().st_size if dest.exists() else 0
    if expected_size and current_size == expected_size:
        return expected_size

    for attempt in range(3):
        headers = {}
        mode = "wb"
        if current_size > 0:
            headers["Range"] = f"bytes={current_size}-"
            mode = "ab"
        with session.get(url, headers=headers, stream=True, timeout=(30, timeout_s)) as response:
            response.raise_for_status()
            if current_size > 0 and response.status_code == 200:
                current_size = 0
                mode = "wb"
            with dest.open(mode) as fp:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fp.write(chunk)
        current_size = dest.stat().st_size if dest.exists() else 0
        if not expected_size or current_size == expected_size:
            return expected_size or current_size
    raise RuntimeError(
        f"Download incomplete after retries for {url}. expected_size={expected_size}, actual={current_size}"
    )


def _gebco_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _gebco_status_url(basket_id: str) -> str:
    return f"https://download.gebco.net/api/queue/status/{basket_id}"


def _gebco_download_url(basket_id: str) -> str:
    return f"https://download.gebco.net/api/queue/download/{basket_id}"


def _download_gebco_subset(spec: PublicSceneSpec, dest_dir: Path) -> tuple[Path, str]:
    if spec.bbox is None:
        raise ValueError(f"GEBCO scene {spec.scene_id} missing bbox.")
    left, right, bottom, top = spec.bbox
    session = _gebco_session()
    payload = {
        "id": "0",
        "email": None,
        "submission_date": "2026-04-22T00:00:00",
        "processing_status": "new",
        "items": [
            {
                "id": 0,
                "grid_id": 1,
                "data_source_ids": [1],
                "formats": [2],
                "left": left,
                "right": right,
                "top": top,
                "bottom": bottom,
            }
        ],
    }
    response = session.post("https://download.gebco.net/api/queue", json=payload, timeout=120)
    response.raise_for_status()
    basket_id = response.json()["basketId"]

    deadline = time.time() + 240
    while time.time() < deadline:
        status_response = session.get(_gebco_status_url(basket_id), timeout=60)
        status_response.raise_for_status()
        status = status_response.json().get("status")
        if status == "finished":
            break
        if status == "error":
            raise RuntimeError(f"GEBCO subset request failed for {spec.scene_id} with basket_id={basket_id}")
        time.sleep(2.0)
    else:
        raise TimeoutError(f"Timed out waiting for GEBCO subset generation for {spec.scene_id}")

    zip_path = dest_dir / f"{spec.scene_id}.zip"
    with session.get(_gebco_download_url(basket_id), stream=True, timeout=(30, 240)) as download:
        download.raise_for_status()
        with zip_path.open("wb") as fp:
            for chunk in download.iter_content(chunk_size=1 << 16):
                if chunk:
                    fp.write(chunk)

    extract_dir = dest_dir / spec.scene_id
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    tif_candidates = list(extract_dir.rglob("*.tif")) + list(extract_dir.rglob("*.tiff"))
    if not tif_candidates:
        raise FileNotFoundError(f"No GeoTIFF found in GEBCO download for {spec.scene_id}")
    tif_candidates.sort(key=lambda path: path.stat().st_size, reverse=True)
    return tif_candidates[0], basket_id


def _masked_bathymetry_to_depth(arr: np.ma.MaskedArray) -> np.ndarray:
    raw = np.asarray(arr.astype(float).filled(np.nan), dtype=float)
    finite = np.isfinite(raw)
    if not np.any(finite):
        raise ValueError("Raster crop contains no finite values.")

    median_value = float(np.nanmedian(raw[finite]))
    if median_value < 0:
        valid_mask = raw < 0
        depth = -raw
    else:
        valid_mask = raw > 0
        depth = raw.copy()
    depth[~valid_mask] = np.nan
    return depth


def _infer_meter_resolution(dataset: rasterio.io.DatasetReader) -> tuple[float, float]:
    if dataset.crs is None or not dataset.crs.is_projected:
        raise ValueError(f"Expected a projected CRS in meters, got {dataset.crs!r}")
    xres = abs(float(dataset.transform.a))
    yres = abs(float(dataset.transform.e))
    if xres <= 0 or yres <= 0:
        raise ValueError("Invalid raster transform; resolution must be positive.")
    return xres, yres


def _window_complexity(depth_patch: np.ndarray, xres: float, yres: float) -> dict[str, float] | None:
    valid = np.isfinite(depth_patch)
    valid_fraction = float(np.mean(valid))
    if valid_fraction < MIN_PUBLIC_VALID_FRAC:
        return None

    filled = np.where(valid, depth_patch, np.nanmedian(depth_patch[valid]))
    gy, gx = np.gradient(filled, yres, xres)
    slope_mag = np.hypot(gx, gy)
    depth_std = float(np.std(filled))
    relief = float(np.max(filled) - np.min(filled))
    slope_mean = float(np.mean(slope_mag))
    complexity = slope_mean + 0.015 * depth_std + 0.010 * relief
    return {
        "valid_fraction": valid_fraction,
        "slope_mean": slope_mean,
        "depth_std": depth_std,
        "relief": relief,
        "complexity": float(complexity),
    }


def _choose_crop_window(
    dataset: rasterio.io.DatasetReader,
    spec: PublicSceneSpec,
) -> tuple[Window, dict[str, float]]:
    xres, yres = _infer_meter_resolution(dataset)
    overview_h = min(OVERVIEW_MAX_SIDE, dataset.height)
    overview_w = min(OVERVIEW_MAX_SIDE, dataset.width)
    overview = dataset.read(
        1,
        out_shape=(overview_h, overview_w),
        resampling=Resampling.bilinear,
        masked=True,
    )
    overview_depth = _masked_bathymetry_to_depth(overview)

    overview_xres = xres * dataset.width / overview_w
    overview_yres = yres * dataset.height / overview_h
    crop_w = max(24, int(round(PUBLIC_CROP_WIDTH_M / overview_xres)))
    crop_h = max(24, int(round(PUBLIC_CROP_HEIGHT_M / overview_yres)))
    crop_w = min(crop_w, overview_w)
    crop_h = min(crop_h, overview_h)
    step_x = max(6, crop_w // 5)
    step_y = max(6, crop_h // 5)

    candidates: list[dict[str, float]] = []
    for row in range(0, max(overview_h - crop_h + 1, 1), step_y):
        for col in range(0, max(overview_w - crop_w + 1, 1), step_x):
            patch = overview_depth[row : row + crop_h, col : col + crop_w]
            metrics = _window_complexity(patch, overview_xres, overview_yres)
            if metrics is None:
                continue
            candidates.append(
                {
                    "row": float(row),
                    "col": float(col),
                    **metrics,
                }
            )
    if not candidates:
        raise RuntimeError(f"No valid crop candidate found for {spec.scene_id}")

    candidates.sort(key=lambda item: item["complexity"])
    index = int(round(spec.selection_quantile * (len(candidates) - 1)))
    chosen = candidates[index]

    scale_x = dataset.width / overview_w
    scale_y = dataset.height / overview_h
    full_col = int(round(chosen["col"] * scale_x))
    full_row = int(round(chosen["row"] * scale_y))
    full_w = max(8, int(round(crop_w * scale_x)))
    full_h = max(8, int(round(crop_h * scale_y)))
    full_col = min(full_col, max(dataset.width - full_w, 0))
    full_row = min(full_row, max(dataset.height - full_h, 0))
    window = Window(full_col, full_row, full_w, full_h)
    return window, chosen


def _fill_depth_gaps(depth: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    valid = np.isfinite(depth)
    valid_fraction = float(np.mean(valid))
    if valid_fraction < MIN_PUBLIC_VALID_FRAC:
        raise RuntimeError(
            f"Selected public crop only has valid_fraction={valid_fraction:.3f}; "
            f"required >= {MIN_PUBLIC_VALID_FRAC:.3f}"
        )
    if np.all(valid):
        return depth, {"valid_fraction_before_fill": valid_fraction, "filled_cells": 0, "fill_strategy": "none"}
    fill_value = float(np.nanmedian(depth[valid]))
    filled = np.where(valid, depth, fill_value)
    return filled, {
        "valid_fraction_before_fill": valid_fraction,
        "filled_cells": int(np.size(depth) - np.count_nonzero(valid)),
        "fill_strategy": "local_median_fill",
    }


def _local_xy_from_lonlat(bounds: tuple[float, float, float, float], nx: int, ny: int) -> tuple[np.ndarray, np.ndarray]:
    west, south, east, north = bounds
    lons = np.linspace(west, east, nx)
    lats = np.linspace(south, north, ny)
    lon0 = 0.5 * (west + east)
    lat0 = 0.5 * (south + north)
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = meters_per_deg_lat * math.cos(math.radians(lat0))
    x = (lons - lon0) * meters_per_deg_lon
    y = (lats - lat0) * meters_per_deg_lat
    x = x - x.min()
    y = y - y.min()
    return np.meshgrid(x, y)


def _save_scene_cache(path: Path, scene: TerrainScene) -> None:
    np.savez_compressed(
        path,
        x=scene.x,
        y=scene.y,
        z=scene.z,
    )
    _safe_json_dump(path.with_suffix(".json"), scene.manifest_entry)


def _load_scene_cache(path: Path, spec: PublicSceneSpec) -> TerrainScene:
    with np.load(path, allow_pickle=True) as obj:
        x = obj["x"]
        y = obj["y"]
        z = obj["z"]
    manifest = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    return TerrainScene(
        scene_id=spec.scene_id,
        display_name=spec.display_name,
        scene_group="public",
        terrain_class=spec.terrain_class,
        x=x,
        y=y,
        z=z,
        source=spec.source,
        download_url=spec.download_url,
        raw_file=manifest.get("raw_file"),
        manifest_entry=manifest,
    )


def _load_gebco_scene(spec: PublicSceneSpec, workspace_root: Path | str, cache_path: Path) -> TerrainScene:
    raw_dir = _shared_public_root(workspace_root) / "raw" / "gebco"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / spec.scene_id / "data.tif"
    basket_id_path = raw_dir / spec.scene_id / "basket_id.txt"
    if not raw_path.exists():
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        tif_path, basket_id = _download_gebco_subset(spec, raw_path.parent)
        if tif_path != raw_path:
            raw_path.write_bytes(tif_path.read_bytes())
        basket_id_path.write_text(basket_id, encoding="utf-8")
    else:
        basket_id = basket_id_path.read_text(encoding="utf-8").strip() if basket_id_path.exists() else "cached"

    with rasterio.open(raw_path) as dataset:
        arr = dataset.read(1, out_shape=(GRID_NY, GRID_NX), resampling=Resampling.bilinear, masked=True)
        depth = _masked_bathymetry_to_depth(arr)
        depth, fill_info = _fill_depth_gaps(depth)
        bounds = tuple(float(value) for value in dataset.bounds)
        xx, yy = _local_xy_from_lonlat(bounds, GRID_NX, GRID_NY)
        resolution_m = round(max(xx[0, 1] - xx[0, 0], yy[1, 0] - yy[0, 0]), 3)
        manifest = {
            "scene_id": spec.scene_id,
            "source": spec.source,
            "download_url": spec.download_url,
            "license": spec.license,
            "raw_file": str(raw_path),
            "crop_bounds": {
                "left": bounds[0],
                "bottom": bounds[1],
                "right": bounds[2],
                "top": bounds[3],
                "crs": dataset.crs.to_string() if dataset.crs else "EPSG:4326",
            },
            "resolution_m": resolution_m,
            "depth_range_m": [float(np.min(depth)), float(np.max(depth))],
            "terrain_class": spec.terrain_class,
            "missing_value_handling": fill_info,
            "queue_download_url": _gebco_download_url(basket_id) if basket_id != "cached" else None,
            "basket_id": basket_id,
            "provider": spec.provider,
        }

    scene = TerrainScene(
        scene_id=spec.scene_id,
        display_name=spec.display_name,
        scene_group="public",
        terrain_class=spec.terrain_class,
        x=xx,
        y=yy,
        z=depth,
        source=spec.source,
        download_url=spec.download_url,
        raw_file=str(raw_path),
        manifest_entry=manifest,
    )
    _save_scene_cache(cache_path, scene)
    return scene


def load_public_scene(spec: PublicSceneSpec, workspace_root: Path | str) -> TerrainScene:
    cache_dir = _public_cache_dir(workspace_root)
    cache_path = cache_dir / f"{spec.scene_id}.npz"
    if cache_path.exists() and cache_path.with_suffix(".json").exists():
        return _load_scene_cache(cache_path, spec)

    if spec.provider == "gebco":
        return _load_gebco_scene(spec, workspace_root, cache_path)

    raw_dir = _public_raw_dir(workspace_root)
    raw_path = raw_dir / Path(spec.download_url).name
    expected_size = _download_with_resume(spec.download_url, raw_path)

    with rasterio.open(raw_path) as dataset:
        xres, yres = _infer_meter_resolution(dataset)
        crop_window, crop_meta = _choose_crop_window(dataset, spec)
        arr = dataset.read(
            1,
            window=crop_window,
            out_shape=(GRID_NY, GRID_NX),
            resampling=Resampling.bilinear,
            masked=True,
        )
        depth = _masked_bathymetry_to_depth(arr)
        depth, fill_info = _fill_depth_gaps(depth)

        crop_bounds = rasterio.windows.bounds(crop_window, dataset.transform)
        width_m = float(crop_bounds[2] - crop_bounds[0])
        height_m = float(crop_bounds[3] - crop_bounds[1])
        x = np.linspace(0.0, width_m, GRID_NX)
        y = np.linspace(0.0, height_m, GRID_NY)
        xx, yy = np.meshgrid(x, y)

        manifest = {
            "scene_id": spec.scene_id,
            "source": spec.source,
            "download_url": spec.download_url,
            "license": spec.license,
            "raw_file": str(raw_path),
            "crop_bounds": {
                "left": float(crop_bounds[0]),
                "bottom": float(crop_bounds[1]),
                "right": float(crop_bounds[2]),
                "top": float(crop_bounds[3]),
                "crs": dataset.crs.to_string() if dataset.crs else None,
            },
            "resolution_m": round(max(width_m / max(GRID_NX - 1, 1), height_m / max(GRID_NY - 1, 1)), 3),
            "depth_range_m": [float(np.min(depth)), float(np.max(depth))],
            "terrain_class": spec.terrain_class,
            "selection_metrics": crop_meta,
            "missing_value_handling": fill_info,
            "raw_resolution_m": {"x": round(xres, 3), "y": round(yres, 3)},
            "raw_file_size_bytes": expected_size,
        }

    scene = TerrainScene(
        scene_id=spec.scene_id,
        display_name=spec.display_name,
        scene_group="public",
        terrain_class=spec.terrain_class,
        x=xx,
        y=yy,
        z=depth,
        source=spec.source,
        download_url=spec.download_url,
        raw_file=str(raw_path),
        manifest_entry=manifest,
    )
    _save_scene_cache(cache_path, scene)
    return scene


def rotate_coordinates(x: np.ndarray, y: np.ndarray, phi_rad: float) -> tuple[np.ndarray, np.ndarray]:
    u = x * math.cos(phi_rad) + y * math.sin(phi_rad)
    v = -x * math.sin(phi_rad) + y * math.cos(phi_rad)
    return u, v


def directional_swath_width(scene: TerrainScene, phi_rad: float, beam_angle_deg: float = BEAM_ANGLE_DEG) -> np.ndarray:
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
    return np.clip(width, 30.0, 1800.0)


def make_context(scene: TerrainScene, orientation_deg: float) -> CrossTrackContext:
    phi_rad = math.radians(orientation_deg)
    _, v_grid = rotate_coordinates(scene.x, scene.y, phi_rad)
    swath_width = directional_swath_width(scene, phi_rad)
    return CrossTrackContext(
        phi_rad=phi_rad,
        v_grid=v_grid,
        swath_width=swath_width,
        vmin=float(v_grid.min()),
        vmax=float(v_grid.max()),
    )


def line_segment_length_in_rect(v: float, phi_rad: float, width_m: float, height_m: float) -> float:
    pts: list[tuple[float, float]] = []
    eps = 1e-9
    cos_phi = math.cos(phi_rad)
    sin_phi = math.sin(phi_rad)

    if abs(cos_phi) > eps:
        for x in (0.0, width_m):
            y = (v + x * sin_phi) / cos_phi
            if -eps <= y <= height_m + eps:
                pts.append((x, min(max(y, 0.0), height_m)))

    if abs(sin_phi) > eps:
        for y in (0.0, height_m):
            x = (y * cos_phi - v) / sin_phi
            if -eps <= x <= width_m + eps:
                pts.append((min(max(x, 0.0), width_m), y))

    unique: list[tuple[float, float]] = []
    for pt in pts:
        if not any(abs(pt[0] - q[0]) < 1e-6 and abs(pt[1] - q[1]) < 1e-6 for q in unique):
            unique.append(pt)

    if len(unique) < 2:
        return 0.0
    if len(unique) > 2:
        best = 0.0
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                best = max(best, math.dist(unique[i], unique[j]))
        return best
    return math.dist(unique[0], unique[1])


def uniform_line_positions(vmin: float, vmax: float, spacing: float, swath_mean: float) -> np.ndarray:
    positions = []
    first = vmin + 0.5 * swath_mean
    pos = first
    while pos <= vmax - 0.5 * swath_mean:
        positions.append(pos)
        pos += spacing
    if not positions:
        positions = [0.5 * (vmin + vmax)]
    if positions[-1] + 0.5 * swath_mean < vmax:
        positions.append(min(vmax - 0.5 * swath_mean, positions[-1] + spacing))
    return np.asarray(sorted(set(round(p, 6) for p in positions)), dtype=float)


def cross_track_profile(
    context: CrossTrackContext,
    quantile: float,
    bins: int = 160,
) -> tuple[np.ndarray, np.ndarray]:
    edges = np.linspace(context.vmin, context.vmax, bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    profile = []
    for idx in range(bins):
        mask = (context.v_grid >= edges[idx]) & (context.v_grid < edges[idx + 1])
        if np.any(mask):
            profile.append(float(np.quantile(context.swath_width[mask], quantile)))
        else:
            profile.append(np.nan)
    profile_arr = np.asarray(profile, dtype=float)
    valid = np.isfinite(profile_arr)
    if not np.any(valid):
        profile_arr[:] = float(np.quantile(context.swath_width, quantile))
    else:
        profile_arr = np.interp(centers, centers[valid], profile_arr[valid])
    return centers, profile_arr


def interpolated_width(position: float, profile_v: np.ndarray, profile_w: np.ndarray) -> float:
    return float(np.interp(position, profile_v, profile_w))


def adaptive_line_positions(
    vmin: float,
    vmax: float,
    profile_v: np.ndarray,
    profile_w: np.ndarray,
    overlap_target: float = TARGET_OVERLAP,
) -> np.ndarray:
    positions: list[float] = []
    pos = vmin + 0.5 * interpolated_width(vmin, profile_v, profile_w)
    while pos <= vmax and len(positions) < 500:
        positions.append(pos)
        pos += interpolated_width(pos, profile_v, profile_w) * (1.0 - overlap_target)
    return np.asarray(positions, dtype=float)


def coverage_counts(v_grid: np.ndarray, line_positions: np.ndarray, swath_width: np.ndarray) -> np.ndarray:
    if len(line_positions) == 0:
        return np.zeros_like(v_grid, dtype=int)
    distances = np.abs(v_grid[..., None] - line_positions[None, None, :])
    return np.sum(distances <= (0.5 * swath_width[..., None]), axis=-1)


def cellwise_excess_overlap(
    v_grid: np.ndarray,
    line_positions: np.ndarray,
    swath_width: np.ndarray,
) -> np.ndarray:
    if len(line_positions) < 2:
        return np.zeros_like(v_grid, dtype=float)
    mids = 0.5 * (line_positions[:-1] + line_positions[1:])
    pair_index = np.searchsorted(mids, v_grid)
    pair_index = np.clip(pair_index, 0, len(line_positions) - 2)
    local_spacing = np.diff(line_positions)[pair_index]
    eta = 1.0 - local_spacing / np.maximum(swath_width, 1e-6)
    return np.maximum(eta - 0.20, 0.0) * 100.0


def coverage_and_overlap(v_grid: np.ndarray, line_positions: np.ndarray, swath_width: np.ndarray) -> tuple[float, float]:
    counts = coverage_counts(v_grid, line_positions, swath_width)
    coverage_pct = float(np.mean(counts >= 1) * 100.0)
    excess_overlap_pct = float(np.mean(cellwise_excess_overlap(v_grid, line_positions, swath_width)))
    return coverage_pct, excess_overlap_pct


def plan_length_km(scene: TerrainScene, line_positions: np.ndarray, phi_rad: float) -> float:
    line_lengths = sum(line_segment_length_in_rect(v, phi_rad, scene.width_m, scene.height_m) for v in line_positions)
    transition = float(np.sum(np.diff(np.sort(line_positions)))) if len(line_positions) > 1 else 0.0
    return (line_lengths + transition) / 1000.0


def plan_score(path_length_km: float, coverage_pct: float, excess_overlap_pct: float) -> float:
    coverage_penalty = max(0.0, TARGET_COVERAGE_PCT - coverage_pct) * 80.0
    overlap_penalty = excess_overlap_pct * 3.0
    return path_length_km + coverage_penalty + overlap_penalty


def _is_feasible(coverage_pct: float, excess_overlap_pct: float) -> bool:
    return coverage_pct >= TARGET_COVERAGE_PCT and excess_overlap_pct <= EXCESS_OVERLAP_FEASIBLE_PCT


def evaluate_plan(
    scene: TerrainScene,
    method: str,
    seed: int,
    orientation_deg: float,
    line_positions: np.ndarray,
    planning_time_s: float,
) -> PlanResult:
    context = make_context(scene, orientation_deg)
    coverage_pct, overlap_pct = coverage_and_overlap(context.v_grid, np.sort(line_positions), context.swath_width)
    return PlanResult(
        scene_id=scene.scene_id,
        scene_name=scene.display_name,
        scene_group=scene.scene_group,
        terrain_class=scene.terrain_class,
        method=method,
        seed=seed,
        orientation_deg=orientation_deg,
        line_positions=np.sort(line_positions),
        coverage_pct=coverage_pct,
        excess_overlap_pct=overlap_pct,
        path_length_km=plan_length_km(scene, np.sort(line_positions), context.phi_rad),
        planning_time_s=planning_time_s,
        feasible=_is_feasible(coverage_pct, overlap_pct),
    )


def best_constant_spacing_layout(scene: TerrainScene, orientation_deg: float) -> LayoutCandidate:
    context = make_context(scene, orientation_deg)
    best_positions = np.asarray([], dtype=float)
    best_score = float("inf")
    best_coverage = 0.0
    best_overlap = 0.0

    for quantile in CONSTANT_QUANTILES:
        swath_ref = float(np.quantile(context.swath_width, quantile))
        spacing = swath_ref * (1.0 - TARGET_OVERLAP)
        positions = uniform_line_positions(context.vmin, context.vmax, spacing, swath_ref)
        coverage_pct, overlap_pct = coverage_and_overlap(context.v_grid, positions, context.swath_width)
        score = plan_score(plan_length_km(scene, positions, context.phi_rad), coverage_pct, overlap_pct)
        if score < best_score:
            best_score = score
            best_positions = positions
            best_coverage = coverage_pct
            best_overlap = overlap_pct

    return LayoutCandidate(
        orientation_deg=orientation_deg,
        line_positions=best_positions,
        coverage_pct=best_coverage,
        excess_overlap_pct=best_overlap,
        score=best_score,
    )


def best_adaptive_layout(scene: TerrainScene, orientation_candidates: tuple[int, ...] = ANGLE_CANDIDATES) -> LayoutCandidate:
    best = LayoutCandidate(
        orientation_deg=float(orientation_candidates[0]),
        line_positions=np.asarray([], dtype=float),
        coverage_pct=0.0,
        excess_overlap_pct=float("inf"),
        score=float("inf"),
    )
    for angle in orientation_candidates:
        context = make_context(scene, float(angle))
        for quantile in ADAPTIVE_QUANTILES:
            profile_v, profile_w = cross_track_profile(context, quantile)
            positions = adaptive_line_positions(context.vmin, context.vmax, profile_v, profile_w)
            coverage_pct, overlap_pct = coverage_and_overlap(context.v_grid, positions, context.swath_width)
            score = plan_score(plan_length_km(scene, positions, context.phi_rad), coverage_pct, overlap_pct)
            if score < best.score:
                best = LayoutCandidate(
                    orientation_deg=float(angle),
                    line_positions=positions,
                    coverage_pct=coverage_pct,
                    excess_overlap_pct=overlap_pct,
                    score=score,
                )
    return best


def fixed_spacing_plan(scene: TerrainScene) -> PlanResult:
    start = time.perf_counter()
    candidate = best_constant_spacing_layout(scene, 0.0)
    planning_time = time.perf_counter() - start
    return evaluate_plan(scene, "Fixed-Spacing", 0, candidate.orientation_deg, candidate.line_positions, planning_time)


def simple_greedy_plan(scene: TerrainScene) -> tuple[PlanResult, LayoutCandidate]:
    start = time.perf_counter()
    best = LayoutCandidate(0.0, np.asarray([], dtype=float), 0.0, 0.0, float("inf"))
    for angle in ANGLE_CANDIDATES:
        candidate = best_constant_spacing_layout(scene, float(angle))
        if candidate.score < best.score:
            best = candidate
    planning_time = time.perf_counter() - start
    result = evaluate_plan(scene, "Simple Greedy", 0, best.orientation_deg, best.line_positions, planning_time)
    return result, best


def adaptive_spacing_plan(scene: TerrainScene) -> tuple[PlanResult, LayoutCandidate]:
    start = time.perf_counter()
    best = best_adaptive_layout(scene)
    planning_time = time.perf_counter() - start
    result = evaluate_plan(scene, "Adaptive Spacing w/o GA", 0, best.orientation_deg, best.line_positions, planning_time)
    return result, best


def ga_refine_layout(
    scene: TerrainScene,
    orientation_deg: float,
    base_positions: np.ndarray,
    rng: np.random.Generator,
    generations: int = GA_GENERATIONS,
    pop_size: int = GA_POP_SIZE,
) -> np.ndarray:
    context = make_context(scene, orientation_deg)
    if len(base_positions) < 2:
        return np.sort(base_positions.copy())
    nominal_spacing = float(np.median(np.diff(base_positions)))
    fitness_v_grid = context.v_grid[::GA_EVAL_STRIDE, ::GA_EVAL_STRIDE]
    fitness_swath_width = context.swath_width[::GA_EVAL_STRIDE, ::GA_EVAL_STRIDE]
    population = [np.sort(base_positions.copy())]
    for _ in range(pop_size - 1):
        jitter = rng.normal(0.0, 0.10 * nominal_spacing, size=len(base_positions))
        candidate = np.clip(base_positions + jitter, context.vmin, context.vmax)
        population.append(np.sort(candidate))

    def fitness(positions: np.ndarray) -> float:
        coverage_pct, overlap_pct = coverage_and_overlap(fitness_v_grid, positions, fitness_swath_width)
        score = plan_score(plan_length_km(scene, positions, context.phi_rad), coverage_pct, overlap_pct)
        if len(positions) > 1:
            spacing_penalty = float(
                np.sum(np.maximum(0.0, 0.25 * nominal_spacing - np.diff(positions)))
            ) * 0.04
        else:
            spacing_penalty = 0.0
        return score + spacing_penalty

    def tournament_select() -> np.ndarray:
        picks = rng.choice(len(population), size=3, replace=False)
        best_idx = min(picks, key=lambda idx: fitness(population[idx]))
        return population[best_idx]

    best = min(population, key=fitness).copy()
    best_fit = fitness(best)
    for _ in range(generations):
        new_population = [best.copy()]
        while len(new_population) < pop_size:
            parent_a = tournament_select()
            parent_b = tournament_select()
            alpha = rng.uniform(0.30, 0.70)
            child = alpha * parent_a + (1.0 - alpha) * parent_b
            mutation_mask = rng.random(len(child)) < 0.30
            child = child + mutation_mask * rng.normal(0.0, 0.05 * nominal_spacing, size=len(child))
            child = np.sort(np.clip(child, context.vmin, context.vmax))
            new_population.append(child)
        population = new_population
        candidate_best = min(population, key=fitness)
        candidate_fit = fitness(candidate_best)
        if candidate_fit < best_fit:
            best = candidate_best.copy()
            best_fit = candidate_fit
    return best


def fixed_swath_ga_plan(scene: TerrainScene, base_candidate: LayoutCandidate, seed: int) -> PlanResult:
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    refined = ga_refine_layout(scene, base_candidate.orientation_deg, base_candidate.line_positions, rng)
    planning_time = time.perf_counter() - start
    return evaluate_plan(scene, "Fixed-Swath GA", seed, base_candidate.orientation_deg, refined, planning_time)


def full_geometry_aware_hybrid_ga_plan(scene: TerrainScene, base_candidate: LayoutCandidate, seed: int) -> PlanResult:
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    refined = ga_refine_layout(scene, base_candidate.orientation_deg, base_candidate.line_positions, rng)
    planning_time = time.perf_counter() - start
    return evaluate_plan(
        scene,
        "Full Geometry-Aware Hybrid GA",
        seed,
        base_candidate.orientation_deg,
        refined,
        planning_time,
    )


def line_segment_points(v: float, phi_rad: float, width_m: float, height_m: float) -> tuple[np.ndarray, np.ndarray]:
    pts: list[tuple[float, float]] = []
    eps = 1e-9
    cos_phi = math.cos(phi_rad)
    sin_phi = math.sin(phi_rad)

    if abs(cos_phi) > eps:
        for x in (0.0, width_m):
            y = (v + x * sin_phi) / cos_phi
            if -eps <= y <= height_m + eps:
                pts.append((x, min(max(y, 0.0), height_m)))

    if abs(sin_phi) > eps:
        for y in (0.0, height_m):
            x = (y * cos_phi - v) / sin_phi
            if -eps <= x <= width_m + eps:
                pts.append((min(max(x, 0.0), width_m), y))

    unique: list[tuple[float, float]] = []
    for pt in pts:
        if not any(abs(pt[0] - q[0]) < 1e-6 and abs(pt[1] - q[1]) < 1e-6 for q in unique):
            unique.append(pt)

    if len(unique) < 2:
        return np.asarray([]), np.asarray([])
    if len(unique) > 2:
        best_pair = None
        best_dist = -1.0
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                dist = math.dist(unique[i], unique[j])
                if dist > best_dist:
                    best_dist = dist
                    best_pair = (unique[i], unique[j])
        assert best_pair is not None
        p0, p1 = best_pair
    else:
        p0, p1 = unique[0], unique[1]
    return np.asarray([p0[0], p1[0]]), np.asarray([p0[1], p1[1]])


def _result_to_row(result: PlanResult) -> dict[str, Any]:
    return {
        "scene_id": result.scene_id,
        "scene_name": result.scene_name,
        "scene_group": result.scene_group,
        "terrain_class": result.terrain_class,
        "method": result.method,
        "seed": int(result.seed),
        "orientation_deg": float(result.orientation_deg),
        "path_length_km": float(result.path_length_km),
        "coverage_pct": float(result.coverage_pct),
        "excess_overlap_pct": float(result.excess_overlap_pct),
        "planning_time_s": float(result.planning_time_s),
        "line_count": int(result.line_count),
        "feasible": int(result.feasible),
    }


def summarize_results(results: list[PlanResult]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[PlanResult]] = defaultdict(list)
    name_lookup = {}
    for result in results:
        grouped[(result.scene_id, result.method)].append(result)
        name_lookup[result.scene_id] = {
            "scene_name": result.scene_name,
            "scene_group": result.scene_group,
            "terrain_class": result.terrain_class,
        }

    summary_rows: list[dict[str, Any]] = []
    for (scene_id, method), rows in sorted(grouped.items()):
        metric_arrays = {
            "path_length_km": np.asarray([row.path_length_km for row in rows], dtype=float),
            "coverage_pct": np.asarray([row.coverage_pct for row in rows], dtype=float),
            "excess_overlap_pct": np.asarray([row.excess_overlap_pct for row in rows], dtype=float),
            "planning_time_s": np.asarray([row.planning_time_s for row in rows], dtype=float),
            "line_count": np.asarray([row.line_count for row in rows], dtype=float),
            "feasible": np.asarray([1.0 if row.feasible else 0.0 for row in rows], dtype=float),
        }
        orientation_counter = Counter(round(row.orientation_deg, 6) for row in rows)
        line_counter = Counter(int(row.line_count) for row in rows)
        orientation_consistency = max(orientation_counter.values()) / len(rows)
        line_count_consistency = max(line_counter.values()) / len(rows)

        record = {
            "scene_id": scene_id,
            "scene_name": name_lookup[scene_id]["scene_name"],
            "scene_group": name_lookup[scene_id]["scene_group"],
            "terrain_class": name_lookup[scene_id]["terrain_class"],
            "method": method,
            "n_runs": len(rows),
            "orientation_consistency": float(orientation_consistency),
            "line_count_consistency": float(line_count_consistency),
            "orientation_modes": [
                {"orientation_deg": float(angle), "count": int(count)} for angle, count in orientation_counter.most_common()
            ],
            "line_count_modes": [
                {"line_count": int(count_key), "count": int(count)} for count_key, count in line_counter.most_common()
            ],
        }
        for key, values in metric_arrays.items():
            record[f"{key}_mean"] = float(values.mean())
            record[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            record[f"{key}_min"] = float(values.min())
            record[f"{key}_max"] = float(values.max())
        summary_rows.append(record)
    return summary_rows


def write_results_tables(out_dir: Path, results: list[PlanResult], summary_rows: list[dict[str, Any]]) -> None:
    benchmark_csv = out_dir / "benchmark_results.csv"
    benchmark_json = out_dir / "benchmark_results.json"
    method_stats_csv = out_dir / "benchmark_method_statistics.csv"

    rows = [_result_to_row(result) for result in results]
    with benchmark_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "scene_id",
                "scene_name",
                "scene_group",
                "terrain_class",
                "method",
                "seed",
                "orientation_deg",
                "path_length_km",
                "coverage_pct",
                "excess_overlap_pct",
                "planning_time_s",
                "line_count",
                "feasible",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    _safe_json_dump(benchmark_json, rows)

    ordered_cols = [
        "scene_id",
        "scene_name",
        "scene_group",
        "terrain_class",
        "method",
        "n_runs",
        "path_length_km_mean",
        "path_length_km_std",
        "path_length_km_min",
        "path_length_km_max",
        "coverage_pct_mean",
        "coverage_pct_std",
        "coverage_pct_min",
        "coverage_pct_max",
        "excess_overlap_pct_mean",
        "excess_overlap_pct_std",
        "excess_overlap_pct_min",
        "excess_overlap_pct_max",
        "planning_time_s_mean",
        "planning_time_s_std",
        "planning_time_s_min",
        "planning_time_s_max",
        "line_count_mean",
        "line_count_std",
        "line_count_min",
        "line_count_max",
        "feasible_mean",
        "feasible_std",
        "feasible_min",
        "feasible_max",
        "orientation_consistency",
        "line_count_consistency",
    ]
    with method_stats_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=ordered_cols)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({key: row.get(key) for key in ordered_cols})


def write_public_manifest(out_dir: Path, public_scenes: list[TerrainScene]) -> None:
    manifest = [scene.manifest_entry for scene in public_scenes]
    _safe_json_dump(out_dir / "public_scene_manifest.json", manifest)


def write_parameter_details(out_dir: Path) -> None:
    config = {
        "fixed_geometry": {
            "beam_angle_deg": BEAM_ANGLE_DEG,
            "target_overlap": TARGET_OVERLAP,
            "target_coverage_pct": TARGET_COVERAGE_PCT,
            "excess_overlap_feasible_pct": EXCESS_OVERLAP_FEASIBLE_PCT,
        },
        "grid": {
            "synthetic_width_m": SYNTH_WIDTH_M,
            "synthetic_height_m": SYNTH_HEIGHT_M,
            "public_crop_width_m": PUBLIC_CROP_WIDTH_M,
            "public_crop_height_m": PUBLIC_CROP_HEIGHT_M,
            "grid_nx": GRID_NX,
            "grid_ny": GRID_NY,
        },
        "search": {
            "angle_candidates_deg": list(ANGLE_CANDIDATES),
            "constant_quantiles": list(CONSTANT_QUANTILES),
            "adaptive_quantiles": list(ADAPTIVE_QUANTILES),
            "ga_generations": GA_GENERATIONS,
            "ga_population": GA_POP_SIZE,
            "ga_seeds": list(GA_SEEDS),
        },
        "public_data_policy": {
            "source_priority": ["GEBCO 2025 public grid"],
            "selection_rule": "overview sliding-window selection at target complexity quantile",
            "missing_value_handling": "discard low-valid windows, then median-fill residual missing cells",
        },
    }
    _safe_json_dump(out_dir / "implementation_details.json", config)

    with (out_dir / "implementation_details.csv").open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["section", "parameter", "value"])
        for section, values in config.items():
            for key, value in values.items():
                writer.writerow([section, key, json.dumps(value, ensure_ascii=False)])


def _paper_style_axes(ax, *, grid_axis: str | None = None) -> None:
    ax.set_facecolor(PAPER_AX_BG)
    ax.tick_params(labelsize=8.5, colors=PAPER_TEXT)
    for spine in ax.spines.values():
        spine.set_color("#465664")
        spine.set_linewidth(0.9)
    if grid_axis:
        ax.grid(axis=grid_axis, linestyle="--", linewidth=0.7, color=PAPER_GRID, alpha=0.75)
    else:
        ax.grid(False)


def _panel_letter(ax, index: int) -> None:
    ax.text(
        0.02,
        0.98,
        f"({chr(ord('a') + index)})",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        fontweight="bold",
        color=PAPER_TEXT,
    )


def _scene_badge(scene: TerrainScene) -> tuple[str, str]:
    if scene.scene_group == "public":
        return "Public GEBCO 2025", PUBLIC_ACCENT
    return "Synthetic stress test", SYNTH_ACCENT


def _depth_range_text(scene: TerrainScene) -> str:
    return f"Depth {float(np.nanmin(scene.z)):.0f}-{float(np.nanmax(scene.z)):.0f} m"


def _contour_levels(z: np.ndarray, n_levels: int = 20) -> np.ndarray:
    zmin = float(np.nanmin(z))
    zmax = float(np.nanmax(z))
    if math.isclose(zmin, zmax, rel_tol=0.0, abs_tol=1e-9):
        delta = max(abs(zmin) * 1e-3, 1.0)
        return np.linspace(zmin - delta, zmax + delta, n_levels)
    return np.linspace(zmin, zmax, n_levels)


def _short_scene_name(name: str) -> str:
    return (
        name.replace("GEBCO ", "")
        .replace(" Margin", "")
        .replace(" Canyon", "")
        .replace(" Seafloor", "")
    )


def _metric_box(ax, text: str, accent: str) -> None:
    ax.text(
        0.03,
        0.04,
        text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.8,
        color=PAPER_TEXT,
        bbox={
            "boxstyle": "round,pad=0.30",
            "facecolor": "#ffffff",
            "edgecolor": accent,
            "linewidth": 1.0,
            "alpha": 0.97,
        },
    )


def _display_line_positions(line_positions: np.ndarray, target_visible_lines: int = 28) -> np.ndarray:
    if len(line_positions) <= target_visible_lines:
        return line_positions
    stride = max(1, len(line_positions) // target_visible_lines)
    sampled = np.asarray(line_positions[::stride], dtype=float)
    if sampled[-1] != float(line_positions[-1]):
        sampled = np.append(sampled, float(line_positions[-1]))
    return sampled


def _scene_extent_nm(scene: TerrainScene) -> tuple[float, float, float, float]:
    return (
        float(np.nanmin(scene.x) / NM_TO_M),
        float(np.nanmax(scene.x) / NM_TO_M),
        float(np.nanmin(scene.y) / NM_TO_M),
        float(np.nanmax(scene.y) / NM_TO_M),
    )


def _framed_scene_limits(
    scene: TerrainScene,
    *,
    target_box_aspect: float = 1.12,
    pad_frac: float = 0.018,
) -> tuple[float, float, float, float]:
    xmin, xmax, ymin, ymax = _scene_extent_nm(scene)
    width = xmax - xmin
    height = ymax - ymin
    pad_x = width * pad_frac
    pad_y = height * pad_frac
    xmin -= pad_x
    xmax += pad_x
    ymin -= pad_y
    ymax += pad_y

    width = xmax - xmin
    height = ymax - ymin
    current_aspect = height / max(width, 1e-9)
    if current_aspect > target_box_aspect:
        target_width = height / target_box_aspect
        extra_x = 0.5 * max(0.0, target_width - width)
        xmin -= extra_x
        xmax += extra_x
    else:
        target_height = width * target_box_aspect
        extra_y = 0.5 * max(0.0, target_height - height)
        ymin -= extra_y
        ymax += extra_y
    return xmin, xmax, ymin, ymax


def _render_bathymetry(
    ax,
    scene: TerrainScene,
    *,
    contour_count: int = 18,
    contour_step: int = 3,
    contour_alpha: float = 0.22,
) -> None:
    extent = _scene_extent_nm(scene)
    vert_exag = 0.65 if scene.scene_group == "public" else 1.05
    shaded = BATHY_LIGHT.shade(scene.z, cmap=BATHY_CMAP, vert_exag=vert_exag, blend_mode="soft")
    ax.imshow(
        shaded,
        extent=extent,
        origin="lower",
        interpolation="bilinear",
        aspect="auto",
        zorder=0,
    )
    levels = _contour_levels(scene.z, contour_count)
    ax.contour(
        scene.x / NM_TO_M,
        scene.y / NM_TO_M,
        scene.z,
        levels=levels[:: max(1, contour_step)],
        colors="#fbfaf7",
        linewidths=0.40,
        alpha=contour_alpha,
        zorder=1,
    )
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])


def _add_scale_bar(
    ax,
    length_nm: float,
    *,
    anchor: tuple[float, float] = (0.68, 0.08),
    text_offset: float = 0.024,
) -> None:
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    width = xmax - xmin
    height = ymax - ymin
    bar_len = min(length_nm, 0.34 * width)
    x0 = xmin + anchor[0] * width
    y0 = ymin + anchor[1] * height
    x1 = x0 + bar_len
    tick = 0.012 * height

    for xs, ys in (
        ([x0, x1], [y0, y0]),
        ([x0, x0], [y0 - tick, y0 + tick]),
        ([x1, x1], [y0 - tick, y0 + tick]),
    ):
        ax.plot(
            xs,
            ys,
            color="#ffffff",
            linewidth=2.8,
            zorder=7,
            solid_capstyle="butt",
            path_effects=[pe.Stroke(linewidth=4.6, foreground="#32485a"), pe.Normal()],
        )

    ax.text(
        0.5 * (x0 + x1),
        y0 + text_offset * height,
        f"{int(length_nm) if float(length_nm).is_integer() else length_nm:g} NM",
        ha="center",
        va="bottom",
        fontsize=7.7,
        color=PAPER_TEXT,
        bbox={
            "boxstyle": "round,pad=0.18",
            "facecolor": "#ffffff",
            "edgecolor": PANEL_EDGE,
            "linewidth": 0.7,
            "alpha": 0.96,
        },
        zorder=8,
    )


def _scene_title_chip(ax, scene: TerrainScene) -> None:
    badge_text, accent = _scene_badge(scene)
    title = _short_scene_name(scene.display_name)
    title = title.replace("Uniform Slope", "Uniform slope").replace("Complex Terrain", "Complex terrain")
    ax.text(
        0.03,
        0.965,
        title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.8 if scene.scene_group == "public" else 9.7,
        fontweight="semibold",
        color=PAPER_TEXT,
        zorder=9,
    )
    ax.text(
        0.03,
        0.885,
        badge_text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        color="#fffdf8",
        bbox={
            "boxstyle": "round,pad=0.22",
            "facecolor": accent,
            "edgecolor": accent,
            "linewidth": 0.8,
            "alpha": 0.92,
        },
        zorder=9,
    )


def _depth_box(ax, scene: TerrainScene, accent: str, *, loc: tuple[float, float] = (0.03, 0.045)) -> None:
    ax.text(
        loc[0],
        loc[1],
        _depth_range_text(scene),
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.8,
        color=PAPER_TEXT,
        bbox={
            "boxstyle": "round,pad=0.22",
            "facecolor": "#ffffff",
            "edgecolor": accent,
            "linewidth": 0.9,
            "alpha": 0.94,
        },
        zorder=9,
    )


def _method_style(method: str) -> dict[str, Any]:
    if method == "Fixed-Spacing":
        return {"color": "#6d727c", "linestyle": (0, (5.0, 2.2)), "linewidth": 1.15, "alpha": 0.95}
    if method == "Adaptive Spacing w/o GA":
        return {"color": "#2a9d8f", "linestyle": (0, (1.4, 1.1)), "linewidth": 1.15, "alpha": 0.92}
    if method == "Full Geometry-Aware Hybrid GA":
        return {"color": "#c26a3d", "linestyle": "-", "linewidth": 1.30, "alpha": 0.94}
    return {"color": METHOD_COLORS[method], "linestyle": "-", "linewidth": 1.0, "alpha": 0.90}


def _draw_public_triptych_row(
    fig,
    axes: list[Any],
    scene: TerrainScene,
    scene_results: list[PlanResult],
    *,
    panel_start: int = 0,
    standalone: bool = False,
) -> int:
    methods = ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]
    accent = PUBLIC_ACCENT
    scene_title_y = 1.12 if standalone else 1.10
    subtitle_y = 1.04 if standalone else 1.02

    axes[0].text(
        0.0,
        scene_title_y,
        scene.display_name,
        transform=axes[0].transAxes,
        ha="left",
        va="bottom",
        fontsize=14.0 if standalone else 12.6,
        fontweight="bold",
        color=PAPER_TEXT,
    )
    axes[0].text(
        0.0,
        subtitle_y,
        "Representative layouts from the public GEBCO benchmark",
        transform=axes[0].transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=PAPER_MUTED,
    )

    for col_idx, (ax, method) in enumerate(zip(axes, methods)):
        rep = _representative_result(scene_results, method)
        style = _method_style(method)
        _render_bathymetry(ax, scene, contour_count=20, contour_step=4, contour_alpha=0.18)
        phi = math.radians(rep.orientation_deg)
        visible_positions = _display_line_positions(rep.line_positions, target_visible_lines=15)
        for pos in visible_positions:
            xs, ys = line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
            if xs.size:
                ax.plot(
                    xs / NM_TO_M,
                    ys / NM_TO_M,
                    color=style["color"],
                    linestyle=style["linestyle"],
                    linewidth=style["linewidth"],
                    alpha=style["alpha"],
                    zorder=5,
                    solid_capstyle="round",
                )

        _paper_style_axes(ax)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("East-West (NM)", fontsize=8.8, color=PAPER_TEXT)
        if col_idx == 0:
            ax.set_ylabel("North-South (NM)", fontsize=8.8, color=PAPER_TEXT)
        else:
            ax.set_ylabel("")
        ax.set_title(METHOD_LABELS[method], fontsize=10.5, fontweight="semibold", color=style["color"], pad=7)
        ax.text(
            0.03,
            0.965,
            f"Heading {int(round(rep.orientation_deg))}°, {rep.line_count} lines",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.4,
            color=PAPER_TEXT,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "#fffaf4",
                "edgecolor": style["color"],
                "linewidth": 0.85,
                "alpha": 0.92,
            },
            zorder=9,
        )
        if col_idx == 0:
            _depth_box(ax, scene, accent, loc=(0.03, 0.13))
        _metric_box(
            ax,
            f"L {rep.path_length_km:.1f} km\nC {rep.coverage_pct:.2f}%\nO {rep.excess_overlap_pct:.2f}%",
            style["color"],
        )
        _add_scale_bar(ax, 10.0, anchor=(0.63, 0.08))
        _panel_letter(ax, panel_start + col_idx)
    return panel_start + len(methods)


def _square_scene_limits(scene: TerrainScene) -> tuple[float, float, float, float]:
    xmin, xmax, ymin, ymax = _scene_extent_nm(scene)
    side = max(xmax - xmin, ymax - ymin)
    xmid = 0.5 * (xmin + xmax)
    ymid = 0.5 * (ymin + ymax)
    return (xmid - 0.5 * side, xmid + 0.5 * side, ymid - 0.5 * side, ymid + 0.5 * side)


def _draw_method_summary_card(ax, *, y0: float, method: str, rep: PlanResult) -> None:
    style = _method_style(method)
    card_h = 0.245
    ax.add_patch(
        Rectangle(
            (0.05, y0),
            0.90,
            card_h,
            transform=ax.transAxes,
            facecolor="#ffffff",
            edgecolor=PANEL_EDGE,
            linewidth=1.0,
            zorder=1,
        )
    )
    ax.add_patch(
        Rectangle(
            (0.05, y0),
            0.035,
            card_h,
            transform=ax.transAxes,
            facecolor=style["color"],
            edgecolor=style["color"],
            linewidth=0.0,
            zorder=2,
        )
    )
    ax.text(
        0.11,
        y0 + 0.185,
        METHOD_LABELS[method],
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=10.0,
        fontweight="semibold",
        color=style["color"],
        zorder=3,
    )
    ax.plot(
        [0.68, 0.91],
        [y0 + 0.185, y0 + 0.185],
        transform=ax.transAxes,
        color=style["color"],
        linestyle=style["linestyle"],
        linewidth=2.0,
        alpha=0.95,
        solid_capstyle="round",
        zorder=3,
    )
    ax.text(
        0.11,
        y0 + 0.125,
        f"Heading {int(round(rep.orientation_deg))}°   |   {rep.line_count} lines",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8.2,
        color=PAPER_MUTED,
        zorder=3,
    )
    ax.text(
        0.11,
        y0 + 0.067,
        f"Path {rep.path_length_km:.1f} km",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8.6,
        color=PAPER_TEXT,
        zorder=3,
    )
    ax.text(
        0.11,
        y0 + 0.036,
        f"Coverage {rep.coverage_pct:.2f}%   |   Overlap {rep.excess_overlap_pct:.2f}%",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8.2,
        color=PAPER_TEXT,
        zorder=3,
    )


def _draw_scene_overlay_with_cards(
    map_ax,
    card_ax,
    scene: TerrainScene,
    scene_results: list[PlanResult],
    *,
    panel_letter: str,
    title_fontsize: float,
    subtitle_fontsize: float,
) -> None:
    methods = ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]
    _render_bathymetry(map_ax, scene, contour_count=20, contour_step=4, contour_alpha=0.18)
    _paper_style_axes(map_ax)
    map_ax.set_facecolor(PAPER_AX_BG)
    map_ax.set_box_aspect(1.12)
    xmin, xmax, ymin, ymax = _framed_scene_limits(scene, target_box_aspect=1.12)
    map_ax.set_xlim(xmin, xmax)
    map_ax.set_ylim(ymin, ymax)
    map_ax.set_xlabel("East-West (NM)", fontsize=9.0, color=PAPER_TEXT)
    map_ax.set_ylabel("North-South (NM)", fontsize=9.0, color=PAPER_TEXT)
    map_ax.text(
        0.02,
        1.055,
        scene.display_name,
        transform=map_ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=title_fontsize,
        fontweight="bold",
        color=PAPER_TEXT,
    )
    map_ax.text(
        0.02,
        1.010,
        "External-data benchmark comparison",
        transform=map_ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=subtitle_fontsize,
        color=PAPER_MUTED,
    )
    map_ax.text(
        0.02,
        0.98,
        panel_letter,
        transform=map_ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        fontweight="bold",
        color=PAPER_TEXT,
    )

    for method in methods:
        rep = _representative_result(scene_results, method)
        style = _method_style(method)
        visible_positions = _display_line_positions(rep.line_positions, target_visible_lines=10)
        phi = math.radians(rep.orientation_deg)
        zorder = 4 if method == "Fixed-Spacing" else 5 if method == "Adaptive Spacing w/o GA" else 6
        for pos in visible_positions:
            xs, ys = line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
            if xs.size:
                map_ax.plot(
                    xs / NM_TO_M,
                    ys / NM_TO_M,
                    color=style["color"],
                    linestyle=style["linestyle"],
                    linewidth=1.25 if method == "Full Geometry-Aware Hybrid GA" else 1.10,
                    alpha=0.92 if method == "Full Geometry-Aware Hybrid GA" else 0.82,
                    zorder=zorder,
                    solid_capstyle="round",
                    path_effects=[pe.Stroke(linewidth=2.0, foreground=(1.0, 1.0, 1.0, 0.08)), pe.Normal()],
                )

    _depth_box(map_ax, scene, PUBLIC_ACCENT, loc=(0.03, 0.05))
    _add_scale_bar(map_ax, 10.0, anchor=(0.56, 0.08))

    card_ax.set_axis_off()
    card_ax.set_facecolor(PAPER_BG)
    card_ax.text(
        0.05,
        0.96,
        "Method comparison",
        transform=card_ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.6,
        fontweight="bold",
        color=PAPER_TEXT,
    )
    card_ax.text(
        0.05,
        0.91,
        "Route families are visually subsampled for readability;\nreported metrics still use the full layouts.",
        transform=card_ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.4,
        color=PAPER_MUTED,
    )
    for y0, method in zip((0.64, 0.355, 0.07), methods):
        rep = _representative_result(scene_results, method)
        _draw_method_summary_card(card_ax, y0=y0, method=method, rep=rep)


def _terrain_class_note(scene: TerrainScene) -> str:
    labels = {
        "flat": "Flat reference case",
        "moderate_slope": "Moderate-slope terrain",
        "complex_relief": "Complex-relief terrain",
    }
    return labels.get(scene.terrain_class, scene.terrain_class.replace("_", " ").title())


def _overview_source_badge(scene: TerrainScene) -> tuple[str, str]:
    if scene.scene_group == "public":
        return "Public bathymetry", PUBLIC_ACCENT
    return "Synthetic benchmark", SYNTH_ACCENT


def _overview_scene_panel(
    ax,
    scene: TerrainScene,
    *,
    panel_index: int,
) -> None:
    badge_text, accent = _overview_source_badge(scene)
    _render_bathymetry(
        ax,
        scene,
        contour_count=18 if scene.scene_group == "public" else 14,
        contour_step=3,
        contour_alpha=0.17 if scene.scene_group == "public" else 0.12,
    )
    _paper_style_axes(ax)
    xmin, xmax, ymin, ymax = _scene_extent_nm(scene)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")

    title = _short_scene_name(scene.display_name)
    title = title.replace("Uniform Slope", "Uniform slope").replace("Complex Terrain", "Complex terrain")
    header_width = 0.50 if scene.scene_group == "public" else 0.57
    ax.add_patch(
        FancyBboxPatch(
            (0.03, 0.82),
            header_width,
            0.145,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            transform=ax.transAxes,
            facecolor=(1.0, 1.0, 1.0, 0.92),
            edgecolor=PANEL_EDGE,
            linewidth=0.8,
            zorder=8,
        )
    )
    ax.text(
        0.055,
        0.944,
        f"({chr(ord('a') + panel_index)})  {title}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.4 if scene.scene_group == "public" else 9.6,
        fontweight="bold",
        color=PAPER_TEXT,
        zorder=9,
    )
    ax.text(
        0.055,
        0.885,
        _terrain_class_note(scene),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.4,
        color=PAPER_MUTED,
        zorder=9,
    )
    ax.text(
        0.97,
        0.95,
        badge_text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=7.2,
        color="#ffffff",
        bbox={
            "boxstyle": "round,pad=0.20",
            "facecolor": accent,
            "edgecolor": accent,
            "linewidth": 0.8,
            "alpha": 0.95,
        },
        zorder=9,
    )
    _depth_box(ax, scene, accent, loc=(0.03, 0.045))
    _add_scale_bar(
        ax,
        10.0 if scene.scene_group == "public" else 1.0,
        anchor=(0.73 if scene.scene_group == "public" else 0.70, 0.08),
    )


def _overview_group_frame(
    fig,
    *,
    bounds: tuple[float, float, float, float],
    accent: str,
    title: str,
    subtitle: str,
) -> None:
    x0, y0, width, height = bounds
    fig.add_artist(
        Rectangle(
            (x0, y0),
            width,
            height,
            transform=fig.transFigure,
            facecolor="#ffffff",
            edgecolor=PANEL_EDGE,
            linewidth=0.9,
            zorder=0,
        )
    )
    fig.add_artist(
        Rectangle(
            (x0, y0 + height - 0.008),
            width,
            0.008,
            transform=fig.transFigure,
            facecolor=accent,
            edgecolor=accent,
            linewidth=0.0,
            zorder=0,
        )
    )
    fig.text(
        x0 + 0.020,
        y0 + height - 0.028,
        title,
        ha="left",
        va="top",
        fontsize=12.0,
        fontweight="bold",
        color=accent,
    )
    fig.text(
        x0 + 0.020,
        y0 + height - 0.053,
        subtitle,
        ha="left",
        va="top",
        fontsize=8.3,
        color=PAPER_MUTED,
    )


def scene_overview_plot(out_dir: Path, scenes: list[TerrainScene]) -> None:
    public_scenes = [scene for scene in scenes if scene.scene_group == "public"]
    synthetic_scenes = [scene for scene in scenes if scene.scene_group == "synthetic"]
    fig = plt.figure(figsize=(12.8, 8.8))
    fig.patch.set_facecolor(PAPER_BG)
    fig.text(0.06, 0.962, "Benchmark Scene Atlas", fontsize=17.0, fontweight="bold", color=PAPER_TEXT)
    fig.text(
        0.06,
        0.934,
        "Five benchmark scenes arranged as a publication-style atlas for external-data validation and mechanism analysis.",
        fontsize=9.2,
        color=PAPER_MUTED,
    )
    fig.text(
        0.985,
        0.914,
        "Per-panel scale bars preserve local physical size despite normalized card framing.",
        ha="right",
        va="center",
        fontsize=7.3,
        color=PAPER_MUTED,
    )

    public_bounds = (0.055, 0.535, 0.89, 0.31)
    synth_bounds = (0.055, 0.085, 0.89, 0.35)
    _overview_group_frame(
        fig,
        bounds=public_bounds,
        accent=PUBLIC_ACCENT,
        title="Public bathymetry scenes",
        subtitle="Regional GEBCO subsets used as the main external-data stress cases.",
    )
    _overview_group_frame(
        fig,
        bounds=synth_bounds,
        accent=SYNTH_ACCENT,
        title="Synthetic mechanism scenes",
        subtitle="Controlled flat, slope, and complex-relief cases that isolate geometric sensitivity.",
    )

    layout_axes = [
        fig.add_axes([0.085, 0.575, 0.37, 0.19]),
        fig.add_axes([0.545, 0.575, 0.37, 0.19]),
        fig.add_axes([0.085, 0.125, 0.25, 0.22]),
        fig.add_axes([0.375, 0.125, 0.25, 0.22]),
        fig.add_axes([0.665, 0.125, 0.25, 0.22]),
    ]

    for panel_idx, (ax, scene) in enumerate(zip(layout_axes, public_scenes + synthetic_scenes)):
        _overview_scene_panel(ax, scene, panel_index=panel_idx)

    fig.savefig(out_dir / "figure_scene_overview.png", dpi=300)
    plt.close(fig)


def _representative_result(results: list[PlanResult], method: str) -> PlanResult:
    method_rows = [row for row in results if row.method == method]
    if not method_rows:
        raise ValueError(f"No result found for method={method}")
    method_rows = sorted(
        method_rows,
        key=lambda row: (
            plan_score(row.path_length_km, row.coverage_pct, row.excess_overlap_pct),
            row.seed,
        ),
    )
    return method_rows[len(method_rows) // 2]


def path_overlay_plot(out_dir: Path, public_scenes: list[TerrainScene], results: list[PlanResult]) -> None:
    fig = plt.figure(figsize=(11.4, 11.2))
    fig.patch.set_facecolor(PAPER_BG)
    gs = fig.add_gridspec(len(public_scenes), 2, width_ratios=[1.0, 0.58], hspace=0.22, wspace=0.07)
    for row_idx, scene in enumerate(public_scenes):
        scene_results = [row for row in results if row.scene_id == scene.scene_id]
        map_ax = fig.add_subplot(gs[row_idx, 0])
        card_ax = fig.add_subplot(gs[row_idx, 1])
        _draw_scene_overlay_with_cards(
            map_ax,
            card_ax,
            scene,
            scene_results,
            panel_letter=f"({chr(ord('a') + row_idx)})",
            title_fontsize=13.5,
            subtitle_fontsize=8.7,
        )
    fig.subplots_adjust(left=0.06, right=0.985, top=0.97, bottom=0.05)
    fig.savefig(out_dir / "figure_public_path_overlays.png", dpi=300)
    plt.close(fig)

    for scene in public_scenes:
        scene_results = [row for row in results if row.scene_id == scene.scene_id]
        fig = plt.figure(figsize=(11.2, 6.3))
        fig.patch.set_facecolor(PAPER_BG)
        gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.62], wspace=0.06)
        map_ax = fig.add_subplot(gs[0, 0])
        card_ax = fig.add_subplot(gs[0, 1])
        _draw_scene_overlay_with_cards(
            map_ax,
            card_ax,
            scene,
            scene_results,
            panel_letter="(a)",
            title_fontsize=15.0,
            subtitle_fontsize=9.0,
        )
        fig.subplots_adjust(left=0.06, right=0.985, top=0.90, bottom=0.08)
        fig.savefig(out_dir / f"figure_path_triptych_{scene.scene_id}.png", dpi=300)
        plt.close(fig)


def metric_summary_plot(out_dir: Path, summary_rows: list[dict[str, Any]]) -> None:
    methods = [
        "Fixed-Spacing",
        "Simple Greedy",
        "Adaptive Spacing w/o GA",
        "Fixed-Swath GA",
        "Full Geometry-Aware Hybrid GA",
    ]
    groups = ["synthetic", "public"]
    metric_specs = [
        ("path_gain_pct", "Path gain vs fixed (%)"),
        ("coverage_pct_mean", "Coverage (%)"),
        ("excess_overlap_pct_mean", "Excess overlap (%)"),
        ("planning_time_s_mean", "Planning time (s)"),
    ]

    grouped_lookup = defaultdict(list)
    fixed_lookup = {}
    for row in summary_rows:
        grouped_lookup[(row["scene_group"], row["method"])].append(row)
        if row["method"] == "Fixed-Spacing":
            fixed_lookup[row["scene_id"]] = float(row["path_length_km_mean"])

    def metric_series(group: str, method: str, metric_key: str) -> list[float]:
        rows = grouped_lookup.get((group, method), [])
        if metric_key == "path_gain_pct":
            gains = []
            for row in rows:
                baseline = fixed_lookup.get(row["scene_id"])
                if baseline is None:
                    continue
                gains.append(100.0 * (baseline - float(row["path_length_km_mean"])) / max(baseline, 1e-6))
            return gains
        return [float(row[metric_key]) for row in rows]

    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.6))
    fig.patch.set_facecolor(PAPER_BG)
    axes_flat = axes.ravel()
    y_positions = np.arange(len(methods))

    for panel_idx, (ax, (metric_key, title)) in enumerate(zip(axes_flat, metric_specs)):
        _paper_style_axes(ax, grid_axis="x")
        for y_idx, method in enumerate(methods):
            synthetic_values = metric_series("synthetic", method, metric_key)
            public_values = metric_series("public", method, metric_key)
            syn_mean = float(np.mean(synthetic_values)) if synthetic_values else np.nan
            pub_mean = float(np.mean(public_values)) if public_values else np.nan
            syn_err = _stderr(synthetic_values) if synthetic_values else 0.0
            pub_err = _stderr(public_values) if public_values else 0.0
            ax.plot([syn_mean, pub_mean], [y_idx, y_idx], color=PAPER_LINE, linewidth=1.35, zorder=1)
            ax.errorbar(
                syn_mean,
                y_idx,
                xerr=syn_err,
                fmt="o",
                markersize=6.2,
                color=GROUP_COLORS["synthetic"],
                ecolor=GROUP_COLORS["synthetic"],
                elinewidth=1.0,
                capsize=2.6,
                zorder=3,
            )
            ax.errorbar(
                pub_mean,
                y_idx,
                xerr=pub_err,
                fmt="s",
                markersize=5.9,
                color=GROUP_COLORS["public"],
                ecolor=GROUP_COLORS["public"],
                elinewidth=1.0,
                capsize=2.6,
                zorder=4,
            )
        ax.set_title(title, fontsize=11.5, fontweight="semibold", color=PAPER_TEXT, pad=8)
        ax.set_yticks(y_positions)
        ax.set_yticklabels([METHOD_LABELS[method] for method in methods], fontsize=8.8, color=PAPER_TEXT)
        ax.invert_yaxis()
        if metric_key == "path_gain_pct":
            ax.axvline(0.0, color="#92a5b6", linewidth=0.95, linestyle=":")
        _panel_letter(ax, panel_idx)

    legend_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GROUP_COLORS["synthetic"], markeredgecolor=GROUP_COLORS["synthetic"], markersize=7, label="Synthetic scenes"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=GROUP_COLORS["public"], markeredgecolor=GROUP_COLORS["public"], markersize=6.5, label="Public GEBCO scenes"),
    ]
    fig.legend(legend_handles, ["Synthetic scenes", "Public GEBCO scenes"], loc="upper center", ncol=2, frameon=False, fontsize=9.5)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.93])
    fig.savefig(out_dir / "figure_metric_summary.png", dpi=300)
    plt.close(fig)


def gap_overlap_heatmaps(out_dir: Path, public_scenes: list[TerrainScene], results: list[PlanResult]) -> None:
    fig, axes = plt.subplots(len(public_scenes), 2, figsize=(10.5, 4.3 * len(public_scenes)))
    if len(public_scenes) == 1:
        axes = np.asarray([axes])
    for row_idx, scene in enumerate(public_scenes):
        scene_results = [row for row in results if row.scene_id == scene.scene_id]
        rep = _representative_result(scene_results, "Full Geometry-Aware Hybrid GA")
        context = make_context(scene, rep.orientation_deg)
        counts = coverage_counts(context.v_grid, rep.line_positions, context.swath_width)
        gap_map = (counts < 1).astype(float)
        excess_map = cellwise_excess_overlap(context.v_grid, rep.line_positions, context.swath_width)

        gap_ax = axes[row_idx, 0]
        overlap_ax = axes[row_idx, 1]
        gap_img = gap_ax.imshow(
            gap_map,
            origin="lower",
            extent=[0.0, scene.width_m / NM_TO_M, 0.0, scene.height_m / NM_TO_M],
            cmap="Reds",
            vmin=0.0,
            vmax=1.0,
            aspect="equal",
        )
        overlap_img = overlap_ax.imshow(
            excess_map,
            origin="lower",
            extent=[0.0, scene.width_m / NM_TO_M, 0.0, scene.height_m / NM_TO_M],
            cmap="magma",
            aspect="equal",
        )
        gap_ax.set_title(f"{scene.display_name}\nCoverage gap map")
        overlap_ax.set_title(f"{scene.display_name}\nExcess overlap map")
        gap_ax.set_xlabel("East-West (NM)")
        overlap_ax.set_xlabel("East-West (NM)")
        gap_ax.set_ylabel("North-South (NM)")
        overlap_ax.set_ylabel("North-South (NM)")
        fig.colorbar(gap_img, ax=gap_ax, shrink=0.82, pad=0.02, label="Uncovered (0/1)")
        fig.colorbar(overlap_img, ax=overlap_ax, shrink=0.82, pad=0.02, label="Excess overlap (%)")
    fig.tight_layout()
    fig.savefig(out_dir / "figure_gap_overlap_heatmaps.png", dpi=300)
    plt.close(fig)


def seed_stability_plot(out_dir: Path, public_scenes: list[TerrainScene], results: list[PlanResult]) -> None:
    metrics = [
        ("path_length_km", "Path Length (km)"),
        ("coverage_pct", "Coverage (%)"),
        ("excess_overlap_pct", "Excess Overlap (%)"),
        ("planning_time_s", "Planning Time (s)"),
    ]
    methods = ["Fixed-Swath GA", "Full Geometry-Aware Hybrid GA"]
    fig, axes = plt.subplots(len(metrics), len(public_scenes), figsize=(5.0 * len(public_scenes), 3.6 * len(metrics)))
    if len(public_scenes) == 1:
        axes = np.asarray([[ax] for ax in axes])
    colors = {"Fixed-Swath GA": "#E7298A", "Full Geometry-Aware Hybrid GA": "#1F78B4"}

    for col_idx, scene in enumerate(public_scenes):
        scene_results = [row for row in results if row.scene_id == scene.scene_id]
        for row_idx, (metric_key, title) in enumerate(metrics):
            ax = axes[row_idx, col_idx]
            for method in methods:
                method_rows = sorted(
                    [row for row in scene_results if row.method == method],
                    key=lambda row: row.seed,
                )
                xs = [row.seed for row in method_rows]
                ys = [float(getattr(row, metric_key)) for row in method_rows]
                ax.plot(xs, ys, marker="o", linewidth=1.1, markersize=3.2, label=method, color=colors[method])
            ax.set_title(f"{scene.display_name}\n{title}")
            ax.set_xlabel("Seed")
            ax.grid(True, linestyle="--", alpha=0.3)
            if col_idx == 0:
                ax.set_ylabel(title)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=True)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.96])
    fig.savefig(out_dir / "figure_seed_stability.png", dpi=300)
    plt.close(fig)


def write_summary_bundle(
    out_dir: Path,
    results: list[PlanResult],
    summary_rows: list[dict[str, Any]],
    public_manifest: list[dict[str, Any]],
    final_means: dict[str, float],
    final_stderrs: dict[str, float],
) -> None:
    bundle = {
        "final_means": final_means,
        "final_stderrs": final_stderrs,
        "summary_rows": summary_rows,
        "public_scene_manifest": public_manifest,
        "run_counts": {
            "total_results": len(results),
            "total_scenes": len({row.scene_id for row in results}),
            "public_scenes": len({row.scene_id for row in results if row.scene_group == "public"}),
            "synthetic_scenes": len({row.scene_id for row in results if row.scene_group == "synthetic"}),
        },
        "figure_files": sorted(path.name for path in out_dir.glob("figure_*.png")),
    }
    _safe_json_dump(out_dir / "benchmark_summary.json", bundle)


def build_final_info(summary_rows: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float], dict[str, Any]]:
    by_group_method = defaultdict(list)
    summary_lookup = {}
    for row in summary_rows:
        by_group_method[(row["scene_group"], row["method"])].append(row)
        summary_lookup[(row["scene_id"], row["method"])] = row

    def series(group: str, method: str, key: str) -> list[float]:
        return [float(row[key]) for row in by_group_method.get((group, method), [])]

    public_hybrid_path_gain = []
    synthetic_hybrid_path_gain = []
    for row in summary_rows:
        key = (row["scene_id"], "Fixed-Spacing")
        if row["method"] != "Full Geometry-Aware Hybrid GA" or key not in summary_lookup:
            continue
        baseline = float(summary_lookup[key]["path_length_km_mean"])
        gain = 100.0 * (baseline - float(row["path_length_km_mean"])) / max(baseline, 1e-6)
        if row["scene_group"] == "public":
            public_hybrid_path_gain.append(gain)
        else:
            synthetic_hybrid_path_gain.append(gain)

    public_hybrid_feasibility = series("public", "Full Geometry-Aware Hybrid GA", "feasible_mean")
    public_hybrid_coverage = series("public", "Full Geometry-Aware Hybrid GA", "coverage_pct_mean")
    public_hybrid_overlap = series("public", "Full Geometry-Aware Hybrid GA", "excess_overlap_pct_mean")
    public_orientation_consistency = series("public", "Full Geometry-Aware Hybrid GA", "orientation_consistency")
    public_line_consistency = series("public", "Full Geometry-Aware Hybrid GA", "line_count_consistency")
    synthetic_hybrid_feasibility = series("synthetic", "Full Geometry-Aware Hybrid GA", "feasible_mean")
    synthetic_hybrid_coverage = series("synthetic", "Full Geometry-Aware Hybrid GA", "coverage_pct_mean")
    synthetic_hybrid_overlap = series("synthetic", "Full Geometry-Aware Hybrid GA", "excess_overlap_pct_mean")
    total_planning = [float(row["planning_time_s_mean"]) for row in summary_rows]

    public_score = (
        0.35 * np.mean(public_hybrid_feasibility or [0.0])
        + 0.20 * (np.mean(public_hybrid_coverage or [0.0]) / 100.0)
        + 0.20 * (np.mean(public_hybrid_path_gain or [0.0]) / 100.0)
        + 0.15 * np.mean(public_orientation_consistency or [0.0])
        + 0.10 * np.mean(public_line_consistency or [0.0])
    )
    synthetic_score = (
        0.40 * np.mean(synthetic_hybrid_feasibility or [0.0])
        + 0.25 * (np.mean(synthetic_hybrid_coverage or [0.0]) / 100.0)
        + 0.25 * (np.mean(synthetic_hybrid_path_gain or [0.0]) / 100.0)
        + 0.10 * (1.0 - min(np.mean(synthetic_hybrid_overlap or [0.0]) / 10.0, 1.0))
    )
    overall_score = float(0.60 * public_score + 0.40 * synthetic_score)

    means = {
        "overall_score_mean": overall_score,
        "public_hybrid_path_gain_pct_mean": float(np.mean(public_hybrid_path_gain or [0.0])),
        "public_hybrid_coverage_pct_mean": float(np.mean(public_hybrid_coverage or [0.0])),
        "public_hybrid_excess_overlap_pct_mean": float(np.mean(public_hybrid_overlap or [0.0])),
        "public_hybrid_feasibility_rate_mean": float(np.mean(public_hybrid_feasibility or [0.0])),
        "public_hybrid_orientation_consistency_mean": float(np.mean(public_orientation_consistency or [0.0])),
        "public_hybrid_line_count_consistency_mean": float(np.mean(public_line_consistency or [0.0])),
        "synthetic_hybrid_path_gain_pct_mean": float(np.mean(synthetic_hybrid_path_gain or [0.0])),
        "synthetic_hybrid_coverage_pct_mean": float(np.mean(synthetic_hybrid_coverage or [0.0])),
        "synthetic_hybrid_excess_overlap_pct_mean": float(np.mean(synthetic_hybrid_overlap or [0.0])),
        "synthetic_hybrid_feasibility_rate_mean": float(np.mean(synthetic_hybrid_feasibility or [0.0])),
        "total_planning_time_s_mean": float(np.mean(total_planning or [0.0])),
    }
    stderrs = {
        "overall_score_stderr": 0.0,
        "public_hybrid_path_gain_pct_stderr": _stderr(public_hybrid_path_gain),
        "public_hybrid_coverage_pct_stderr": _stderr(public_hybrid_coverage),
        "public_hybrid_excess_overlap_pct_stderr": _stderr(public_hybrid_overlap),
        "public_hybrid_feasibility_rate_stderr": _stderr(public_hybrid_feasibility),
        "public_hybrid_orientation_consistency_stderr": _stderr(public_orientation_consistency),
        "public_hybrid_line_count_consistency_stderr": _stderr(public_line_consistency),
        "synthetic_hybrid_path_gain_pct_stderr": _stderr(synthetic_hybrid_path_gain),
        "synthetic_hybrid_coverage_pct_stderr": _stderr(synthetic_hybrid_coverage),
        "synthetic_hybrid_excess_overlap_pct_stderr": _stderr(synthetic_hybrid_overlap),
        "synthetic_hybrid_feasibility_rate_stderr": _stderr(synthetic_hybrid_feasibility),
        "total_planning_time_s_stderr": _stderr(total_planning),
    }
    final_info_dict = {
        "summary_rows": summary_rows,
        "public_hybrid_path_gain_pct": public_hybrid_path_gain,
        "public_hybrid_coverage_pct": public_hybrid_coverage,
        "public_hybrid_excess_overlap_pct": public_hybrid_overlap,
        "public_hybrid_feasibility_rate": public_hybrid_feasibility,
        "public_hybrid_orientation_consistency": public_orientation_consistency,
        "public_hybrid_line_count_consistency": public_line_consistency,
        "synthetic_hybrid_path_gain_pct": synthetic_hybrid_path_gain,
        "synthetic_hybrid_coverage_pct": synthetic_hybrid_coverage,
        "synthetic_hybrid_excess_overlap_pct": synthetic_hybrid_overlap,
        "synthetic_hybrid_feasibility_rate": synthetic_hybrid_feasibility,
        "total_planning_time_s": total_planning,
    }
    return means, stderrs, final_info_dict


def run_benchmark(out_dir: Path | str, workspace_root: Path | str) -> dict[str, Any]:
    out_dir = output_dir(out_dir)
    workspace_root = Path(workspace_root)
    synthetic_scenes = terrain_generators()
    public_scenes = [load_public_scene(spec, workspace_root) for spec in PUBLIC_SCENE_SPECS]
    scenes = synthetic_scenes + public_scenes

    results: list[PlanResult] = []
    for scene in scenes:
        fixed = fixed_spacing_plan(scene)
        greedy_result, greedy_base = simple_greedy_plan(scene)
        adaptive_result, adaptive_base = adaptive_spacing_plan(scene)
        results.extend([fixed, greedy_result, adaptive_result])
        for seed in GA_SEEDS:
            results.append(fixed_swath_ga_plan(scene, greedy_base, seed))
            results.append(full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed))

    summary_rows = summarize_results(results)
    final_means, final_stderrs, final_info_dict = build_final_info(summary_rows)
    public_manifest = [scene.manifest_entry for scene in public_scenes]

    write_results_tables(out_dir, results, summary_rows)
    write_public_manifest(out_dir, public_scenes)
    write_parameter_details(out_dir)
    scene_overview_plot(out_dir, scenes)
    path_overlay_plot(out_dir, public_scenes, results)
    metric_summary_plot(out_dir, summary_rows)
    gap_overlap_heatmaps(out_dir, public_scenes, results)
    seed_stability_plot(out_dir, public_scenes, results)
    write_summary_bundle(out_dir, results, summary_rows, public_manifest, final_means, final_stderrs)

    return {
        "dataset_name": "geo_public_bathy_benchmark",
        "means": final_means,
        "stderrs": final_stderrs,
        "final_info_dict": final_info_dict,
        "summary_rows": summary_rows,
        "public_scene_manifest": public_manifest,
        "all_results_payload": {
            "benchmark_rows": [_result_to_row(result) for result in results],
            "summary_rows": summary_rows,
            "public_scene_manifest": public_manifest,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Geo public bathymetry benchmark.")
    parser.add_argument("--out-dir", type=str, default="real_experiment_outputs", help="Artifact output directory")
    parser.add_argument(
        "--workspace-root",
        type=str,
        default=None,
        help="Workspace root for shared public bathymetry cache (defaults to the script directory).",
    )
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root) if args.workspace_root else Path(__file__).resolve().parent
    summary = run_benchmark(out_dir=Path(args.out_dir), workspace_root=workspace_root)
    print(json.dumps(summary["means"], indent=2))
    print(f"Saved benchmark artifacts to: {Path(args.out_dir).resolve()}")


if __name__ == "__main__":
    main()
