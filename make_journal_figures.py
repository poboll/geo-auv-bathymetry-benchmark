from __future__ import annotations

import csv
import importlib.util
import json
import math
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LightSource, Normalize, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

import journal_heatmap_style as jhs


ROOT = Path(__file__).resolve().parent
RUN = ROOT / "run_5"
PIC_DIRS = [
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
]
PIC = PIC_DIRS[0]
EXT = ROOT / "survey_grade_extension_usgs_cascadia"
PUBLIC_MANIFEST = {
    row["scene_id"]: row for row in json.loads((RUN / "public_scene_manifest.json").read_text(encoding="utf-8"))
}

SPEC = importlib.util.spec_from_file_location("geo_public_bathy_benchmark", ROOT / "geo_public_bathy_benchmark.py")
geo = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(geo)


plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "mathtext.fontset": "dejavusans",
        "font.size": 7.15,
        "axes.titlesize": 7.65,
        "axes.labelsize": 6.85,
        "xtick.labelsize": 6.25,
        "ytick.labelsize": 6.25,
        "legend.fontsize": 6.75,
        "axes.linewidth": 0.45,
        "savefig.dpi": 420,
    }
)

TEXT = "#202a33"
MUTED = "#65717f"
GRID = "#d7e0e7"
SPINE = "#b8c4cf"
BG = "#ffffff"
PUBLIC = "#0a6f7a"
SYNTH = "#b55a32"

METHODS = [
    "Fixed-Spacing",
    "Simple Greedy",
    "Adaptive Spacing w/o GA",
    "Fixed-Swath GA",
    "Full Geometry-Aware Hybrid GA",
]
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Simple Greedy": "Greedy",
    "Adaptive Spacing w/o GA": "Adaptive-only",
    "Fixed-Swath GA": "Fixed-swath GA",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
}
METHOD_TEXT_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Simple Greedy": "Greedy",
    "Adaptive Spacing w/o GA": "Adaptive-only",
    "Fixed-Swath GA": "Fixed-swath",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
}
METHOD_COLORS = {
    "Fixed-Spacing": "#6f7682",
    "Simple Greedy": "#756bb1",
    "Adaptive Spacing w/o GA": "#148f82",
    "Fixed-Swath GA": "#a64f7d",
    "Full Geometry-Aware Hybrid GA": "#c56335",
}
METHOD_STYLES = {
    "Fixed-Spacing": (0, (4, 2)),
    "Simple Greedy": (0, (2, 2)),
    "Adaptive Spacing w/o GA": (0, (1, 1.4)),
    "Fixed-Swath GA": (0, (3, 1.5, 1, 1.5)),
    "Full Geometry-Aware Hybrid GA": "-",
}

PUBLIC_DETAIL_WINDOWS = {
    "gebco_cascadia_margin_moderate": (0.50, 0.84, 0.58, 0.90),
    "gebco_monterey_canyon_complex": (0.42, 0.74, 0.34, 0.82),
}

BATHY = LinearSegmentedColormap.from_list(
    "journal_bathy",
    ["#f7fbf7", "#d8f0ee", "#8bd1d4", "#4298b7", "#175f88", "#092640"],
)
DETAIL_BATHY = LinearSegmentedColormap.from_list(
    "journal_bathy_detail",
    ["#fbfdfb", "#e4f6f1", "#a8dfe0", "#63b7cf", "#2d7ea8", "#16445f"],
)
PATH_GAIN_CMAP = LinearSegmentedColormap.from_list(
    "journal_path_gain",
    ["#f8fbfb", "#e7f0ef", "#c2dad8", "#7fb3b2", "#2f7580"],
)
COVERAGE_CMAP = LinearSegmentedColormap.from_list(
    "journal_coverage",
    ["#bb765f", "#dfbea2", "#f8f4ea", "#bfd9d3", "#4c8b8d"],
)
OVERLAP_CMAP = LinearSegmentedColormap.from_list(
    "journal_overlap",
    ["#fffaf0", "#f0dfba", "#d9a66f", "#ae6150", "#74393a"],
)
TIME_CMAP = LinearSegmentedColormap.from_list(
    "journal_time",
    ["#fbfbfa", "#e6e4df", "#c3c7c3", "#879997", "#465b61"],
)
LIGHT = LightSource(azdeg=318, altdeg=42)


def load_summary() -> list[dict[str, str]]:
    with (RUN / "benchmark_method_statistics.csv").open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def load_raw_rows() -> list[dict[str, str]]:
    with (RUN / "benchmark_results.csv").open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def load_extension_summary() -> list[dict[str, str]]:
    with (EXT / "benchmark_method_statistics.csv").open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def summary_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["scene_id"], row["method"]): row for row in rows}


def public_scenes():
    return [geo.load_public_scene(spec, ROOT) for spec in geo.PUBLIC_SCENE_SPECS]


def all_scenes():
    return public_scenes() + geo.terrain_generators()


def scene_order(summary_rows: list[dict[str, str]]) -> list[tuple[str, str, str]]:
    preferred = [
        "gebco_cascadia_margin_moderate",
        "gebco_monterey_canyon_complex",
        "synthetic_flat",
        "synthetic_uniform_slope",
        "synthetic_complex",
    ]
    meta = {row["scene_id"]: (row["scene_name"], row["scene_group"]) for row in summary_rows}
    return [(sid, meta[sid][0], meta[sid][1]) for sid in preferred]


def short_name(name: str) -> str:
    return (
        name.replace("GEBCO ", "")
        .replace(" Margin", "")
        .replace(" Canyon", "")
        .replace(" Seafloor", "")
    )


def extent_nm(scene) -> tuple[float, float, float, float]:
    return (
        float(np.nanmin(scene.x) / geo.NM_TO_M),
        float(np.nanmax(scene.x) / geo.NM_TO_M),
        float(np.nanmin(scene.y) / geo.NM_TO_M),
        float(np.nanmax(scene.y) / geo.NM_TO_M),
    )


def terrain_limits(z: np.ndarray) -> tuple[float, float]:
    lo = float(np.nanpercentile(z, 1))
    hi = float(np.nanpercentile(z, 99))
    if hi - lo < 1e-6:
        mid = float(np.nanmean(z))
        return mid - 1.0, mid + 1.0
    pad = 0.03 * (hi - lo)
    return lo - pad, hi + pad


def style_map_axes(ax, *, show_grid: bool = True) -> None:
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_color(SPINE)
        spine.set_linewidth(0.5)
    ax.tick_params(colors=TEXT, width=0.45, length=2.2, pad=1.5)
    if show_grid:
        ax.grid(True, color=GRID, linewidth=0.35, alpha=0.58)
    ax.set_axisbelow(True)


def style_chart_axes(ax, grid_axis: str = "y") -> None:
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_color(SPINE)
        spine.set_linewidth(0.5)
    ax.tick_params(colors=TEXT, width=0.45, length=2.2, pad=1.8)
    ax.grid(True, axis=grid_axis, color=GRID, linewidth=0.4, alpha=0.75)
    ax.set_axisbelow(True)


def render_terrain(
    ax,
    scene,
    *,
    contours: bool = True,
    value_limits: tuple[float, float] | None = None,
    cmap=None,
    vert_exag: float = 0.85,
    interpolation: str = "bilinear",
) -> None:
    z = scene.z
    vmin, vmax = value_limits or terrain_limits(z)
    dx = float(np.abs(scene.x[0, 1] - scene.x[0, 0])) if scene.x.shape[1] > 1 else 1.0
    dy = float(np.abs(scene.y[1, 0] - scene.y[0, 0])) if scene.y.shape[0] > 1 else 1.0
    z_fill = np.where(np.isfinite(z), z, float(np.nanmedian(z)))
    shaded = LIGHT.shade(
        z_fill,
        cmap=cmap or BATHY,
        vmin=vmin,
        vmax=vmax,
        vert_exag=vert_exag,
        dx=max(dx, 1.0),
        dy=max(dy, 1.0),
        blend_mode="soft",
    )
    ax.imshow(
        shaded,
        extent=extent_nm(scene),
        origin="lower",
        interpolation=interpolation,
        aspect="equal",
        zorder=0,
    )
    if contours and float(np.nanmax(z) - np.nanmin(z)) > 1e-6:
        levels = np.linspace(float(np.nanmin(z)), float(np.nanmax(z)), 12)
        ax.contour(
            scene.x / geo.NM_TO_M,
            scene.y / geo.NM_TO_M,
            z,
            levels=levels[1:-1:2],
            colors="#ffffff",
            linewidths=0.24,
            alpha=0.24,
            zorder=1,
        )
    ax.set_xlim(extent_nm(scene)[0], extent_nm(scene)[1])
    ax.set_ylim(extent_nm(scene)[2], extent_nm(scene)[3])


def add_panel_text(ax, label: str, *, accent: str | None = None) -> None:
    color = accent or TEXT
    ax.text(
        0.018,
        0.975,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=5.85,
        fontweight="bold",
        color=color,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 0.9},
        zorder=10,
    )


def add_scale_bar(
    ax,
    length_nm: float,
    *,
    x_anchor: float = 0.68,
    y_anchor: float = 0.075,
    label_dy: float = 0.018,
) -> None:
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    w = xmax - xmin
    h = ymax - ymin
    x0 = xmin + x_anchor * w
    y0 = ymin + y_anchor * h
    x1 = min(x0 + length_nm, xmin + 0.94 * w)
    tick = 0.012 * h
    effect = [pe.Stroke(linewidth=1.05, foreground="#263746"), pe.Normal()]
    ax.plot([x0, x1], [y0, y0], color="white", linewidth=0.82, zorder=8, path_effects=effect)
    ax.plot([x0, x0], [y0 - tick, y0 + tick], color="white", linewidth=0.68, zorder=8, path_effects=effect)
    ax.plot([x1, x1], [y0 - tick, y0 + tick], color="white", linewidth=0.68, zorder=8, path_effects=effect)
    ax.text(
        0.5 * (x0 + x1),
        y0 + label_dy * h,
        f"{length_nm:g} NM",
        ha="center",
        va="bottom",
        fontsize=6.10,
        color="white",
        zorder=9,
        path_effects=effect,
    )


def ratio_bounds(scene, ratios: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    xmin, xmax, ymin, ymax = extent_nm(scene)
    rx0, rx1, ry0, ry1 = ratios
    return (
        xmin + rx0 * (xmax - xmin),
        xmin + rx1 * (xmax - xmin),
        ymin + ry0 * (ymax - ymin),
        ymin + ry1 * (ymax - ymin),
    )


def ratio_patch(scene, ratios: tuple[float, float, float, float]) -> np.ndarray:
    ny, nx = scene.z.shape
    rx0, rx1, ry0, ry1 = ratios
    x0 = max(0, min(nx - 1, int(math.floor(rx0 * nx))))
    x1 = max(x0 + 1, min(nx, int(math.ceil(rx1 * nx))))
    y0 = max(0, min(ny - 1, int(math.floor(ry0 * ny))))
    y1 = max(y0 + 1, min(ny, int(math.ceil(ry1 * ny))))
    return scene.z[y0:y1, x0:x1]


def local_terrain_limits(scene, ratios: tuple[float, float, float, float]) -> tuple[float, float]:
    return terrain_limits(ratio_patch(scene, ratios))


def set_center_square_view(ax, scene) -> None:
    xmin, xmax, ymin, ymax = extent_nm(scene)
    set_center_square_bounds(ax, (xmin, xmax, ymin, ymax))


def set_center_square_bounds(ax, bounds: tuple[float, float, float, float]) -> None:
    xmin, xmax, ymin, ymax = bounds
    span = min(xmax - xmin, ymax - ymin)
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    ax.set_xlim(cx - 0.5 * span, cx + 0.5 * span)
    ax.set_ylim(cy - 0.5 * span, cy + 0.5 * span)
    ax.set_aspect("equal", adjustable="box")


def make_square_map_card(ax, scene, *, panel_label: str, scale_nm: float, is_public: bool) -> None:
    render_terrain(ax, scene)
    set_center_square_view(ax, scene)
    style_map_axes(ax, show_grid=False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_box_aspect(1.0)
    add_panel_text(ax, panel_label, accent=TEXT)
    ax.text(
        0.02,
        0.045,
        f"{float(np.nanmin(scene.z)):.0f}-{float(np.nanmax(scene.z)):.0f} m",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.35,
        color="white",
        path_effects=[pe.Stroke(linewidth=1.35, foreground="#263746"), pe.Normal()],
        zorder=10,
    )
    ax.text(
        0.98,
        0.965,
        "public grid" if is_public else "synthetic",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=4.45,
        color=PUBLIC if is_public else SYNTH,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.80, "pad": 0.55},
        zorder=10,
    )
    add_scale_bar(ax, scale_nm)


def make_atlas_note_card(ax) -> None:
    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    card = FancyBboxPatch(
        (0.035, 0.055),
        0.93,
        0.89,
        boxstyle="round,pad=0.018,rounding_size=0.026",
        linewidth=0.55,
        edgecolor="#d4e0e8",
        facecolor="#f8fbfd",
        transform=ax.transAxes,
    )
    ax.add_patch(card)
    ax.text(0.085, 0.865, "(c) Evidence roles", transform=ax.transAxes, ha="left", va="top", fontsize=6.05, fontweight="bold", color=TEXT)
    bullets = [
        ("GEBCO", "primary public-grid\nbenchmark"),
        ("Synthetic", "mechanism and\nfailure tests"),
        ("USGS", "high-resolution transfer\ncheck in Fig. 14"),
    ]
    y = 0.70
    for label, body in bullets:
        color = PUBLIC if label == "GEBCO" else (SYNTH if label == "Synthetic" else "#4a6fa5")
        ax.scatter([0.105], [y + 0.008], s=18, color=color, transform=ax.transAxes, zorder=5)
        ax.text(0.155, y + 0.035, label, transform=ax.transAxes, ha="left", va="top", fontsize=5.15, fontweight="bold", color=TEXT)
        ax.text(0.155, y - 0.010, body, transform=ax.transAxes, ha="left", va="top", fontsize=4.52, color=MUTED, linespacing=1.13)
        y -= 0.19
    ax.text(
        0.085,
        0.118,
        "Square map cards keep native aspect;\ndepth ranges are local to each scene.",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=4.25,
        color=MUTED,
        linespacing=1.15,
    )


def make_atlas(summary_rows: list[dict[str, str]]) -> None:
    del summary_rows
    scenes = all_scenes()
    fig = plt.figure(figsize=(7.15, 4.84), facecolor=BG)
    gs = fig.add_gridspec(2, 3, hspace=0.07, wspace=0.08)
    placement = [
        (0, 0, scenes[0], "(a) Cascadia", 10.0, True),
        (0, 1, scenes[1], "(b) Monterey", 10.0, True),
        (1, 0, scenes[2], "(d) Flat", 1.0, False),
        (1, 1, scenes[3], "(e) Uniform Slope", 1.0, False),
        (1, 2, scenes[4], "(f) Complex Terrain", 1.0, False),
    ]
    for row, col, scene, label, scale_nm, is_public in placement:
        make_square_map_card(fig.add_subplot(gs[row, col]), scene, panel_label=label, scale_nm=scale_nm, is_public=is_public)
    make_atlas_note_card(fig.add_subplot(gs[0, 2]))
    fig.savefig(PIC / "journal_scene_atlas.png", bbox_inches="tight", facecolor="white", pad_inches=0.025)
    plt.close(fig)


def compute_public_layouts():
    layouts = {}
    for scene in public_scenes():
        fixed = geo.fixed_spacing_plan(scene)
        _, greedy_base = geo.simple_greedy_plan(scene)
        adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
        del greedy_base
        hybrids = [geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed) for seed in geo.GA_SEEDS]
        target = np.mean([row.path_length_km for row in hybrids])
        hybrid = min(hybrids, key=lambda row: abs(row.path_length_km - target))
        layouts[scene.scene_id] = {
            "scene": scene,
            "Fixed-Spacing": fixed,
            "Adaptive Spacing w/o GA": adaptive,
            "Full Geometry-Aware Hybrid GA": hybrid,
        }
    return layouts


def line_positions_to_show(
    line_positions: np.ndarray,
    max_lines: int = 15,
    *,
    trim_edges: int = 0,
) -> np.ndarray:
    lines = np.asarray(line_positions, dtype=float)
    if trim_edges > 0 and len(lines) > 2 * trim_edges:
        lines = lines[trim_edges:-trim_edges]
    if len(lines) <= max_lines:
        return lines
    idx = np.linspace(0, len(lines) - 1, max_lines).round().astype(int)
    return lines[np.unique(idx)]


def draw_layout(ax, scene, result, method: str, *, show_ylabel: bool, show_xlabel: bool) -> None:
    render_terrain(ax, scene)
    style_map_axes(ax, show_grid=True)
    phi = math.radians(result.orientation_deg)
    for pos in line_positions_to_show(result.line_positions):
        xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
        if xs.size:
            ax.plot(
                xs / geo.NM_TO_M,
                ys / geo.NM_TO_M,
                color=METHOD_COLORS[method],
                linestyle=METHOD_STYLES[method],
                linewidth=0.68 if method != "Full Geometry-Aware Hybrid GA" else 0.88,
                alpha=0.94,
                zorder=5,
                solid_capstyle="round",
            )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("E-W (NM)" if show_xlabel else "", color=TEXT, labelpad=2.0)
    ax.set_ylabel("N-S (NM)" if show_ylabel else "", color=TEXT, labelpad=2.0)
    if not show_ylabel:
        ax.set_yticklabels([])
    if not show_xlabel:
        ax.set_xticklabels([])


def make_public_layout_matrix(summary_rows: list[dict[str, str]]) -> None:
    lookup = summary_lookup(summary_rows)
    layouts = compute_public_layouts()
    public_ids = ["gebco_cascadia_margin_moderate", "gebco_monterey_canyon_complex"]
    plot_methods = ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]
    scene_labels = ["Cascadia Margin", "Monterey Canyon"]

    fig, axes = plt.subplots(2, 3, figsize=(7.25, 5.05), facecolor=BG)
    for r, sid in enumerate(public_ids):
        for c, method in enumerate(plot_methods):
            scene = layouts[sid]["scene"]
            result = layouts[sid][method]
            ax = axes[r, c]
            draw_layout(ax, scene, result, method, show_ylabel=(c == 0), show_xlabel=(r == 1))
            stats = lookup[(sid, method)]
            if r == 0:
                ax.set_title(METHOD_LABELS[method], color=METHOD_COLORS[method], fontweight="bold", pad=4)
            row_name = " Cascadia" if r == 0 and c == 0 else (" Monterey" if r == 1 and c == 0 else "")
            add_panel_text(ax, f"({chr(97 + r * 3 + c)}){row_name}")
            ax.text(
                0.5,
                -0.145 if r == 0 else -0.205,
                f"{int(round(result.orientation_deg))} deg; {int(float(stats['line_count_mean']))} lines; "
                f"L={float(stats['path_length_km_mean']):.1f} km; "
                f"C={float(stats['coverage_pct_mean']):.1f}%; "
                f"O={float(stats['excess_overlap_pct_mean']):.2f}%",
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=4.65,
                color=MUTED,
                clip_on=False,
            )
    handles = [
        Line2D([0], [0], color=METHOD_COLORS[m], linestyle=METHOD_STYLES[m], linewidth=1.0, label=METHOD_LABELS[m])
        for m in plot_methods
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.018))
    fig.tight_layout(rect=[0.03, 0.035, 1.0, 0.995], h_pad=1.55, w_pad=0.75)
    fig.savefig(PIC / "journal_public_layout_matrix.png", bbox_inches="tight", facecolor="white", pad_inches=0.03)
    plt.close(fig)


def draw_layout_overlay(ax, scene, results: dict[str, object], *, max_lines: int) -> None:
    render_terrain(ax, scene)
    style_map_axes(ax, show_grid=True)
    for method, result in results.items():
        phi = math.radians(result.orientation_deg)
        for pos in line_positions_to_show(result.line_positions, max_lines=max_lines):
            xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
            if xs.size:
                ax.plot(
                    xs / geo.NM_TO_M,
                    ys / geo.NM_TO_M,
                    color=METHOD_COLORS[method],
                    linestyle=METHOD_STYLES[method],
                    linewidth=0.58 if method != "Full Geometry-Aware Hybrid GA" else 0.72,
                    alpha=0.68 if method != "Full Geometry-Aware Hybrid GA" else 0.78,
                    zorder=5,
                    solid_capstyle="round",
                )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("E-W (NM)", color=TEXT, labelpad=2.0)
    ax.set_ylabel("N-S (NM)", color=TEXT, labelpad=2.0)


def method_strip_label(ax, method: str) -> None:
    ax.text(
        0.018,
        0.975,
        METHOD_TEXT_LABELS[method],
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=5.65,
        fontweight="bold",
        color=METHOD_COLORS[method],
        bbox={"facecolor": "white", "edgecolor": "#dbe4ec", "linewidth": 0.28, "alpha": 0.88, "pad": 0.55},
        zorder=14,
    )


def draw_single_method_strip(
    ax,
    scene,
    result,
    method: str,
    stats: dict[str, str],
    *,
    show_xlabel: bool,
    show_ylabel: bool,
    show_scale: bool,
    scene_label: str | None = None,
) -> None:
    render_terrain(ax, scene)
    if scene.scene_id in PUBLIC_FOCUS_WINDOWS:
        xmin, xmax, ymin, ymax = extent_nm(scene)
        fx0, fx1, fy0, fy1 = PUBLIC_FOCUS_WINDOWS[scene.scene_id]
        ax.set_xlim(xmin + fx0 * (xmax - xmin), xmin + fx1 * (xmax - xmin))
        ax.set_ylim(ymin + fy0 * (ymax - ymin), ymin + fy1 * (ymax - ymin))
    style_map_axes(ax, show_grid=False)
    phi = math.radians(result.orientation_deg)
    line_effect = [pe.Stroke(linewidth=1.05, foreground="white", alpha=0.18), pe.Normal()]
    for pos in line_positions_to_show(result.line_positions, max_lines=17 if "cascadia" in scene.scene_id else 14):
        xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
        if xs.size:
            ax.plot(
                xs / geo.NM_TO_M,
                ys / geo.NM_TO_M,
                color=METHOD_COLORS[method],
                linestyle=METHOD_STYLES[method],
                linewidth=0.58 if method != "Full Geometry-Aware Hybrid GA" else 0.70,
                alpha=0.92,
                zorder=8,
                solid_capstyle="round",
                path_effects=line_effect,
            )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("E-W (NM)" if show_xlabel else "", color=TEXT, labelpad=1.9)
    ax.set_ylabel("N-S (NM)" if show_ylabel else "", color=TEXT, labelpad=1.9)
    if not show_xlabel:
        ax.set_xticklabels([])
    if not show_ylabel:
        ax.set_yticklabels([])
    method_strip_label(ax, method)
    if scene_label:
        ax.text(
            0.985,
            0.975,
            scene_label,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=5.65,
            fontweight="bold",
            color=TEXT,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 0.72},
            zorder=14,
        )
    add_metric_chip(ax, stats, result, method)
    if show_scale:
        add_scale_bar(ax, 10.0)


def add_panel_tag(ax, text: str, *, accent: str = TEXT) -> None:
    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.20,
        fontweight="bold",
        color=accent,
        bbox={"facecolor": "white", "edgecolor": "#d7e0e7", "linewidth": 0.25, "alpha": 0.88, "pad": 0.58},
        zorder=16,
    )


def draw_public_method_panel(
    ax,
    scene,
    result,
    method: str,
    stats: dict[str, str],
    *,
    panel_tag: str,
    detail_window: tuple[float, float, float, float],
    scale_nm: float,
    show_metrics: bool = True,
) -> None:
    render_terrain(
        ax,
        scene,
        value_limits=local_terrain_limits(scene, detail_window),
        cmap=DETAIL_BATHY,
        vert_exag=1.12,
        interpolation="bicubic",
    )
    x0, x1, y0, y1 = ratio_bounds(scene, detail_window)
    set_center_square_bounds(ax, (x0, x1, y0, y1))
    style_map_axes(ax, show_grid=False)
    phi = math.radians(result.orientation_deg)
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_margin = 0.045 * (xlim[1] - xlim[0])
    y_margin = 0.045 * (ylim[1] - ylim[0])
    line_effect = [pe.Stroke(linewidth=1.0, foreground="white", alpha=0.16), pe.Normal()]
    visible_positions: list[float] = []
    for pos in np.asarray(result.line_positions, dtype=float):
        xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
        if not xs.size:
            continue
        xs_nm = xs / geo.NM_TO_M
        ys_nm = ys / geo.NM_TO_M
        inside = (
            np.nanmax(xs_nm) >= xlim[0] + x_margin
            and np.nanmin(xs_nm) <= xlim[1] - x_margin
            and np.nanmax(ys_nm) >= ylim[0] + y_margin
            and np.nanmin(ys_nm) <= ylim[1] - y_margin
        )
        if inside:
            visible_positions.append(float(pos))
    for pos in line_positions_to_show(np.asarray(visible_positions), max_lines=5, trim_edges=2):
        xs, ys = geo.line_segment_points(float(pos), phi, scene.width_m, scene.height_m)
        if xs.size:
            ax.plot(
                xs / geo.NM_TO_M,
                ys / geo.NM_TO_M,
                color=METHOD_COLORS[method],
                linestyle=METHOD_STYLES[method],
                linewidth=0.96 if method != "Full Geometry-Aware Hybrid GA" else 1.12,
                alpha=0.94,
                zorder=9,
                solid_capstyle="round",
                path_effects=line_effect,
            )
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_box_aspect(1.0)
    ax.set_aspect("equal", adjustable="box")
    add_panel_tag(ax, panel_tag, accent=METHOD_COLORS[method])
    if show_metrics:
        add_metric_chip(ax, stats, result, method)
    add_scale_bar(ax, scale_nm)


def make_scene_summary_strip(
    ax,
    lookup: dict[tuple[str, str], dict[str, str]],
    scene_id: str,
    methods: list[str],
    results: dict[str, object],
) -> None:
    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.text(0.0, 0.985, "(d) Layout summary", transform=ax.transAxes, ha="left", va="top", color=TEXT, fontweight="bold", fontsize=7.05)
    ax.text(
        0.0,
        0.905,
        "full-scene metrics; the three map cards above show the same layouts in a compact zoom window",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=5.80,
        color=MUTED,
    )
    ledger = FancyBboxPatch(
        (0.0, 0.13),
        1.0,
        0.56,
        boxstyle="round,pad=0.010,rounding_size=0.016",
        linewidth=0.42,
        edgecolor="#d7e2eb",
        facecolor="#fbfdfe",
        transform=ax.transAxes,
    )
    ax.add_patch(ledger)
    short_labels = {
        "Fixed-Spacing": "Fixed",
        "Adaptive Spacing w/o GA": "Adaptive",
        "Full Geometry-Aware Hybrid GA": "Hybrid",
    }
    x_method = 0.045
    x_cols = [0.39, 0.50, 0.68, 0.84, 0.97]
    for xpos, label in zip(x_cols, ["psi", "n", "L km", "C %", "O %"]):
        ax.text(
            xpos,
            0.60,
            label,
            transform=ax.transAxes,
            ha="right",
            va="center",
            fontsize=5.80,
            color=MUTED,
            fontweight="bold",
        )
    ax.plot([0.04, 0.97], [0.55, 0.55], transform=ax.transAxes, color="#d7e2eb", linewidth=0.42)
    row_y = [0.47, 0.33, 0.19]
    for idx, (method, ypos) in enumerate(zip(methods, row_y)):
        ax.add_patch(
            Rectangle(
                (0.025, ypos - 0.055),
                0.945,
                0.11,
                transform=ax.transAxes,
                facecolor="#ffffff" if idx % 2 == 0 else "#f5f9fb",
                edgecolor="none",
                zorder=0,
            )
        )
        row = lookup[(scene_id, method)]
        if idx:
            ax.plot([0.04, 0.97], [ypos + 0.07, ypos + 0.07], transform=ax.transAxes, color="#e6edf3", linewidth=0.34)
        ax.text(
            x_method,
            ypos,
            short_labels[method],
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=6.15,
            color=METHOD_COLORS[method],
            fontweight="bold",
        )
        values = [
            f"{int(round(results[method].orientation_deg))}",
            f"{int(round(float(row.get('line_count_mean', '0'))))}",
            f"{float(row['path_length_km_mean']):.1f}",
            f"{float(row['coverage_pct_mean']):.1f}",
            f"{float(row['excess_overlap_pct_mean']):.2f}",
        ]
        for xpos, value in zip(x_cols, values):
            ax.text(
                xpos,
                ypos,
                value,
                transform=ax.transAxes,
                ha="right",
                va="center",
                fontsize=6.05,
                color=TEXT,
            )


def make_scene_delta_panel(
    ax,
    lookup: dict[tuple[str, str], dict[str, str]],
    scene_id: str,
    methods: list[str],
) -> None:
    style_chart_axes(ax)
    fixed_path = float(lookup[(scene_id, "Fixed-Spacing")]["path_length_km_mean"])
    x = np.arange(2)
    width = 0.20
    for k, method in enumerate(methods):
        row = lookup[(scene_id, method)]
        gain = 100.0 * (fixed_path - float(row["path_length_km_mean"])) / fixed_path
        overlap = float(row["excess_overlap_pct_mean"])
        bars = ax.bar(x + (k - 1) * width, [gain, overlap], width * 0.82, color=METHOD_COLORS[method], alpha=0.86)
        for bar, value in zip(bars, [gain, overlap]):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value + 0.035,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=4.65,
                color=TEXT,
            )
    baseline_overlap = float(lookup[(scene_id, "Fixed-Spacing")]["excess_overlap_pct_mean"])
    ax.set_title("(f) Path gain and residual overlap", loc="left", color=TEXT, fontweight="bold", fontsize=5.95, pad=3)
    ax.set_xticks(x)
    ax.set_xticklabels(["path gain", "O violation"])
    ax.set_ylim(0, 1.10)
    ax.set_yticks([0.0, 0.5, 1.0])
    ax.set_yticklabels([])
    ax.tick_params(axis="y", left=False, right=False, labelleft=False, labelright=False)
    ax.text(0.015, 0.975, "0-1.1% scale", transform=ax.transAxes, ha="left", va="top", fontsize=4.30, color=MUTED)
    ax.text(
        0.98,
        0.93,
        f"baseline O={baseline_overlap:.2f}%",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=4.55,
        color=MUTED,
    )


def make_scene_verdict_panel(ax, scene_id: str, verdict: str) -> None:
    manifest = PUBLIC_MANIFEST[scene_id]
    depth_lo, depth_hi = manifest["depth_range_m"]
    res = manifest["resolution_m"]
    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    card = FancyBboxPatch(
        (0.0, 0.08),
        1.0,
        0.82,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=0.42,
        edgecolor="#d7e2eb",
        facecolor="#f8fbfd",
        transform=ax.transAxes,
    )
    ax.add_patch(card)
    ax.text(0.035, 0.80, "Interpretation", transform=ax.transAxes, ha="left", va="top", fontsize=4.75, color=TEXT, fontweight="bold")
    ax.text(0.035, 0.58, verdict, transform=ax.transAxes, ha="left", va="top", fontsize=4.35, color=MUTED, linespacing=1.20)
    ax.text(
        0.035,
        0.17,
        f"GEBCO 2025 subset | {res:.0f} m grid | {int(depth_lo)}-{int(depth_hi)} m depth",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=4.15,
        color=MUTED,
    )


def add_metric_chip(ax, stats: dict[str, str], result, method: str) -> None:
    text = (
        f"psi {int(round(result.orientation_deg))} deg | n={int(float(stats['line_count_mean']))}\n"
        f"L {float(stats['path_length_km_mean']):.1f} km | "
        f"C={float(stats['coverage_pct_mean']):.1f}%  "
        f"O={float(stats['excess_overlap_pct_mean']):.2f}%"
    )
    ax.text(
        0.018,
        0.84,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=5.35,
        linespacing=1.12,
        color=TEXT,
        bbox={"facecolor": "white", "edgecolor": "#d3dee8", "linewidth": 0.24, "alpha": 0.82, "pad": 0.50},
        zorder=12,
    )


def make_single_public_route_figure(
    summary_rows: list[dict[str, str]],
    *,
    scene_id: str,
    output_name: str,
    scale_nm: float,
    scene_label: str,
) -> None:
    lookup = summary_lookup(summary_rows)
    layouts = compute_public_layouts()
    scene = layouts[scene_id]["scene"]
    plot_methods = ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]

    fig = plt.figure(figsize=(7.05, 4.56), facecolor=BG)
    gs = fig.add_gridspec(
        2,
        3,
        height_ratios=[1.0, 0.44],
        wspace=0.055,
        hspace=0.080,
    )
    ax_fixed = fig.add_subplot(gs[0, 0])
    ax_adaptive = fig.add_subplot(gs[0, 1])
    ax_hybrid = fig.add_subplot(gs[0, 2])
    ax_summary = fig.add_subplot(gs[1, :])
    detail_window = PUBLIC_DETAIL_WINDOWS[scene_id]
    fig.text(
        0.046,
        0.985,
        f"{short_name(scene_label)} public-scene comparison",
        ha="left",
        va="top",
        fontsize=9.35,
        fontweight="bold",
        color=TEXT,
    )
    fig.text(
        0.046,
        0.958,
        "Zoom panels emphasize terrain-structured line placement; metrics remain full-scene benchmark values.",
        ha="left",
        va="top",
        fontsize=6.25,
        color=MUTED,
    )

    draw_public_method_panel(
        ax_fixed,
        scene,
        layouts[scene_id]["Fixed-Spacing"],
        "Fixed-Spacing",
        lookup[(scene_id, "Fixed-Spacing")],
        panel_tag="(a) Fixed",
        detail_window=detail_window,
        scale_nm=scale_nm,
        show_metrics=False,
    )
    draw_public_method_panel(
        ax_adaptive,
        scene,
        layouts[scene_id]["Adaptive Spacing w/o GA"],
        "Adaptive Spacing w/o GA",
        lookup[(scene_id, "Adaptive Spacing w/o GA")],
        panel_tag="(b) Adaptive-only",
        detail_window=detail_window,
        scale_nm=scale_nm,
        show_metrics=False,
    )
    draw_public_method_panel(
        ax_hybrid,
        scene,
        layouts[scene_id]["Full Geometry-Aware Hybrid GA"],
        "Full Geometry-Aware Hybrid GA",
        lookup[(scene_id, "Full Geometry-Aware Hybrid GA")],
        panel_tag="(c) Hybrid",
        detail_window=detail_window,
        scale_nm=scale_nm,
        show_metrics=False,
    )
    make_scene_summary_strip(ax_summary, lookup, scene_id, plot_methods, {method: layouts[scene_id][method] for method in plot_methods})
    fig.subplots_adjust(left=0.026, right=0.994, top=0.905, bottom=0.050)
    fig.savefig(PIC / output_name, bbox_inches="tight", facecolor="white", pad_inches=0.014)
    plt.close(fig)


def make_public_route_figures(summary_rows: list[dict[str, str]]) -> None:
    make_single_public_route_figure(
        summary_rows,
        scene_id="gebco_cascadia_margin_moderate",
        output_name="journal_cascadia_routes.png",
        scale_nm=10.0,
        scene_label="GEBCO Cascadia Margin",
    )
    make_single_public_route_figure(
        summary_rows,
        scene_id="gebco_monterey_canyon_complex",
        output_name="journal_monterey_routes.png",
        scale_nm=10.0,
        scene_label="GEBCO Monterey Canyon",
    )


def build_metric_matrices(summary_rows: list[dict[str, str]]):
    lookup = summary_lookup(summary_rows)
    scenes = scene_order(summary_rows)
    fixed_path = {sid: float(lookup[(sid, "Fixed-Spacing")]["path_length_km_mean"]) for sid, _, _ in scenes}
    matrices = {}
    for metric in ["path_gain", "coverage", "excess", "time"]:
        arr = np.zeros((len(scenes), len(METHODS)), dtype=float)
        for i, (sid, _, _) in enumerate(scenes):
            for j, method in enumerate(METHODS):
                row = lookup[(sid, method)]
                if metric == "path_gain":
                    arr[i, j] = 100.0 * (fixed_path[sid] - float(row["path_length_km_mean"])) / fixed_path[sid]
                elif metric == "coverage":
                    arr[i, j] = float(row["coverage_pct_mean"])
                elif metric == "excess":
                    arr[i, j] = float(row["excess_overlap_pct_mean"])
                else:
                    arr[i, j] = float(row["planning_time_s_mean"])
        matrices[metric] = arr
    return scenes, matrices


def cell_text_color(im, value: float) -> str:
    rgba = im.cmap(im.norm(value))
    luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
    return "white" if luminance < 0.43 else TEXT


def annotate_heatmap(ax, im, data: np.ndarray, fmt: str, mark_bad=None) -> None:
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            ax.text(
                j,
                i,
                fmt.format(value),
                ha="center",
                va="center",
                fontsize=7.08,
                fontweight="normal",
                color=cell_text_color(im, value),
            )


def make_metric_heatmap(summary_rows: list[dict[str, str]]) -> None:
    scenes, matrices = build_metric_matrices(summary_rows)
    scene_labels = [
        name.replace("GEBCO ", "").replace(" Seafloor", "").replace(" Terrain", " terrain")
        for _, name, _ in scenes
    ]
    method_labels = ["Fixed", "Greedy", "Adapt.", "Fix-swath", "Hybrid"]
    coverage_matrix = matrices["coverage"]
    metric_specs = [
        (
            matrices["path_gain"],
            PATH_GAIN_CMAP,
            Normalize(vmin=0.0, vmax=float(np.max(matrices["path_gain"]))),
            "(a) Path gain vs Fixed (%)",
            "{:.1f}",
        ),
        (
            coverage_matrix,
            COVERAGE_CMAP,
            TwoSlopeNorm(vmin=float(np.min(coverage_matrix)), vcenter=97.0, vmax=float(np.max(coverage_matrix))),
            "(b) Predicted coverage (%)",
            "{:.1f}",
        ),
        (
            matrices["excess"],
            OVERLAP_CMAP,
            Normalize(vmin=0.0, vmax=float(np.max(matrices["excess"]))),
            "(c) Excess-overlap violation (%)",
            "{:.1f}",
        ),
        (
            matrices["time"],
            TIME_CMAP,
            Normalize(vmin=float(np.min(matrices["time"])), vmax=float(np.max(matrices["time"]))),
            "(d) Planning time (s)",
            "{:.2f}",
        ),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(7.35, 4.78), facecolor=BG)
    for panel_idx, (ax, (data, cmap, norm, title, fmt)) in enumerate(zip(axes.ravel(), metric_specs)):
        im = ax.imshow(data, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_title(title, loc="left", color=TEXT, fontweight="semibold", fontsize=8.25, pad=2.9)
        ax.set_xticks(np.arange(len(METHODS)))
        ax.set_xticklabels(method_labels, color=TEXT)
        for tick in ax.get_xticklabels():
            tick.set_fontweight("normal")
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, pad=0.85, length=0.0)
        ax.set_yticks(np.arange(len(scene_labels)))
        if panel_idx in (0, 2):
            ax.set_yticklabels(scene_labels, color=TEXT)
            for tick, (_, _, group) in zip(ax.get_yticklabels(), scenes):
                tick.set_color(PUBLIC if group == "public" else SYNTH)
                tick.set_fontweight("bold" if group == "public" else "normal")
        else:
            ax.set_yticklabels([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(which="minor", bottom=False, left=False)
        annotate_heatmap(ax, im, data, fmt)
    fig.subplots_adjust(left=0.098, right=0.998, top=0.940, bottom=0.046, wspace=0.045, hspace=0.122)
    fig.savefig(PIC / "journal_metric_heatmap.png", bbox_inches="tight", facecolor="white", pad_inches=0.010)
    plt.close(fig)


def make_ablation_seed(summary_rows: list[dict[str, str]], raw_rows: list[dict[str, str]]) -> None:
    lookup = summary_lookup(summary_rows)
    public_ids = ["gebco_cascadia_margin_moderate", "gebco_monterey_canyon_complex"]
    scene_labels = ["Cascadia", "Monterey"]
    ablation_methods = ["Fixed-Spacing", "Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA"]
    x = np.arange(len(public_ids))
    width = 0.23

    fig = plt.figure(figsize=(7.05, 2.92), facecolor=BG)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.18], wspace=0.42)
    ax_gain = fig.add_subplot(gs[0, 0])
    ax_overlap = fig.add_subplot(gs[0, 1])
    ax_table = fig.add_subplot(gs[0, 2])

    for ax in [ax_gain, ax_overlap]:
        style_chart_axes(ax)

    for k, method in enumerate(ablation_methods):
        values = []
        for sid in public_ids:
            fixed = float(lookup[(sid, "Fixed-Spacing")]["path_length_km_mean"])
            value = 100.0 * (fixed - float(lookup[(sid, method)]["path_length_km_mean"])) / fixed
            values.append(value)
        ax_gain.bar(x + (k - 1) * width, values, width, color=METHOD_COLORS[method], label=METHOD_LABELS[method], alpha=0.88)
    ax_gain.axhline(0, color="#8794a2", linewidth=0.55)
    ax_gain.set_title("(a) Public path gain vs Fixed", loc="left", color=TEXT, fontweight="bold")
    ax_gain.set_ylabel("gain vs fixed (%)")
    ax_gain.set_xticks(x)
    ax_gain.set_xticklabels(scene_labels)
    ax_gain.set_ylim(0, 0.98)

    for k, method in enumerate(ablation_methods):
        values = [float(lookup[(sid, method)]["excess_overlap_pct_mean"]) for sid in public_ids]
        ax_overlap.bar(x + (k - 1) * width, values, width, color=METHOD_COLORS[method], alpha=0.88)
    ax_overlap.set_title("(b) Excess-overlap cleanup", loc="left", color=TEXT, fontweight="bold")
    ax_overlap.set_ylabel("excess overlap (%)")
    ax_overlap.set_xticks(x)
    ax_overlap.set_xticklabels(scene_labels)
    ax_overlap.set_ylim(0, 0.95)

    hybrid_rows = [
        row
        for row in raw_rows
        if row["scene_id"] in public_ids and row["method"] == "Full Geometry-Aware Hybrid GA"
    ]
    table_values = []
    for sid in public_ids:
        rows = [row for row in hybrid_rows if row["scene_id"] == sid]
        path_sd_m = np.std([float(row["path_length_km"]) for row in rows], ddof=1) * 1000.0
        cov_sd = np.std([float(row["coverage_pct"]) for row in rows], ddof=1)
        ov_sd = np.std([float(row["excess_overlap_pct"]) for row in rows], ddof=1)
        heading_mode = max(set(row["orientation_deg"] for row in rows), key=[row["orientation_deg"] for row in rows].count)
        line_mode = max(set(row["line_count"] for row in rows), key=[row["line_count"] for row in rows].count)
        mode_count = sum(1 for row in rows if row["orientation_deg"] == heading_mode and row["line_count"] == line_mode)
        table_values.append([f"{path_sd_m:.1f}", f"{cov_sd:.2f}", f"{ov_sd:.2f}", f"{mode_count}/{len(rows)}"])

    ax_table.axis("off")
    ax_table.set_title("(c) Hybrid seed dispersion", loc="left", color=TEXT, fontweight="bold", pad=3)
    tbl = ax_table.table(
        cellText=table_values,
        rowLabels=scene_labels,
        colLabels=["L SD\n(m)", "C SD\n(pp)", "O SD\n(pp)", "mode"],
        cellLoc="center",
        loc="center",
        bbox=[0.0, 0.05, 1.0, 0.86],
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(6.00)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#cbd6e2")
        cell.set_linewidth(0.35)
        if row == 0:
            cell.set_facecolor("#eef4f5")
            cell.set_text_props(color=TEXT, fontweight="bold")
        elif col == -1:
            cell.set_facecolor("#f7f9fb")
            cell.set_text_props(color=TEXT, fontweight="bold")
        else:
            cell.set_facecolor("#ffffff" if row % 2 else "#f8fbfc")
            cell.set_text_props(color=TEXT)

    handles = [Line2D([0], [0], color=METHOD_COLORS[m], linewidth=4, label=METHOD_LABELS[m]) for m in ablation_methods]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.36, 0.985), handlelength=2.8, columnspacing=1.4)
    fig.subplots_adjust(left=0.060, right=0.985, top=0.82, bottom=0.16, wspace=0.42)
    fig.savefig(PIC / "journal_ablation_seed.png", bbox_inches="tight", facecolor="white", pad_inches=0.025)
    plt.close(fig)


def gather_overlap_regime_records(summary_rows: list[dict[str, str]]) -> list[dict[str, float | str]]:
    lookup = summary_lookup(summary_rows)
    ext_lookup = summary_lookup(load_extension_summary())
    ext_manifest = {
        row["scene_id"]: row for row in json.loads((EXT / "public_scene_manifest.json").read_text(encoding="utf-8"))
    }
    scene_meta = {
        "gebco_cascadia_margin_moderate": ("Cascadia", "GEBCO public"),
        "gebco_monterey_canyon_complex": ("Monterey", "GEBCO public"),
        "synthetic_flat": ("Flat", "Synthetic"),
        "synthetic_uniform_slope": ("Slope", "Synthetic"),
        "synthetic_complex": ("Complex", "Synthetic"),
        "usgs_southern_cascadia_30m_low": ("USGS-L", "USGS extension"),
        "usgs_southern_cascadia_30m_medium": ("USGS-M", "USGS extension"),
        "usgs_southern_cascadia_30m_high": ("USGS-H", "USGS extension"),
    }
    records: list[dict[str, float | str]] = []
    main_ids = [
        "gebco_cascadia_margin_moderate",
        "gebco_monterey_canyon_complex",
        "synthetic_flat",
        "synthetic_uniform_slope",
        "synthetic_complex",
    ]
    for sid in main_ids:
        fixed_path = float(lookup[(sid, "Fixed-Spacing")]["path_length_km_mean"])
        hybrid_path = float(lookup[(sid, "Full Geometry-Aware Hybrid GA")]["path_length_km_mean"])
        fixed_overlap = float(lookup[(sid, "Fixed-Spacing")]["excess_overlap_pct_mean"])
        hybrid_overlap = float(lookup[(sid, "Full Geometry-Aware Hybrid GA")]["excess_overlap_pct_mean"])
        hybrid_cov = float(lookup[(sid, "Full Geometry-Aware Hybrid GA")]["coverage_pct_mean"])
        short, group = scene_meta[sid]
        records.append(
            {
                "scene_id": sid,
                "short": short,
                "group": group,
                "fixed_overlap": fixed_overlap,
                "hybrid_gain": 100.0 * (fixed_path - hybrid_path) / fixed_path,
                "hybrid_cleanup": fixed_overlap - hybrid_overlap,
                "hybrid_coverage": hybrid_cov,
            }
        )
    ext_ids = [
        "usgs_southern_cascadia_30m_low",
        "usgs_southern_cascadia_30m_medium",
        "usgs_southern_cascadia_30m_high",
    ]
    for sid in ext_ids:
        fixed_path = float(ext_lookup[(sid, "Fixed-Spacing")]["path_length_km_mean"])
        hybrid_path = float(ext_lookup[(sid, "Full Geometry-Aware Hybrid GA")]["path_length_km_mean"])
        fixed_overlap = float(ext_lookup[(sid, "Fixed-Spacing")]["excess_overlap_pct_mean"])
        hybrid_overlap = float(ext_lookup[(sid, "Full Geometry-Aware Hybrid GA")]["excess_overlap_pct_mean"])
        hybrid_cov = float(ext_lookup[(sid, "Full Geometry-Aware Hybrid GA")]["coverage_pct_mean"])
        short, group = scene_meta[sid]
        records.append(
            {
                "scene_id": sid,
                "short": short,
                "group": group,
                "fixed_overlap": fixed_overlap,
                "hybrid_gain": 100.0 * (fixed_path - hybrid_path) / fixed_path,
                "hybrid_cleanup": fixed_overlap - hybrid_overlap,
                "hybrid_coverage": hybrid_cov,
                "complexity": float(ext_manifest[sid]["selection_metrics"]["complexity"]),
            }
        )
    return records


def make_overlap_regime_diagnostic(summary_rows: list[dict[str, str]]) -> None:
    records = gather_overlap_regime_records(summary_rows)
    fig = plt.figure(figsize=(7.42, 4.78), facecolor=BG)
    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=[1.0, 0.74],
        width_ratios=[1.0, 1.0],
        hspace=0.46,
        wspace=0.28,
    )
    ax_gain = fig.add_subplot(grid[0, 0])
    ax_cleanup = fig.add_subplot(grid[0, 1])
    ax_ladder = fig.add_subplot(grid[1, :])
    for ax in [ax_gain, ax_cleanup, ax_ladder]:
        style_chart_axes(ax)
        ax.tick_params(axis="both", labelsize=8.10)

    group_styles = {
        "GEBCO public": {"color": "#148f82", "marker": "o"},
        "Synthetic": {"color": "#c56335", "marker": "s"},
        "USGS extension": {"color": "#536678", "marker": "^"},
    }
    offsets_gain = {
        "Cascadia": (10, 9),
        "Monterey": (10, -12),
        "Flat": (10, 7),
        "Slope": (10, -10),
        "Complex": (-10, -16),
        "USGS-L": (12, 2),
        "USGS-M": (10, -22),
        "USGS-H": (-44, -18),
    }
    offsets_cleanup = {
        "Cascadia": (10, 8),
        "Monterey": (10, -12),
        "Flat": (10, 7),
        "Slope": (10, -12),
        "Complex": (12, -20),
        "USGS-L": (12, 8),
        "USGS-M": (12, -10),
        "USGS-H": (-44, -18),
    }

    for group, style in group_styles.items():
        subset = [row for row in records if row["group"] == group]
        ax_gain.scatter(
            [row["fixed_overlap"] for row in subset],
            [row["hybrid_gain"] for row in subset],
            s=76,
            marker=style["marker"],
            color=style["color"],
            edgecolor="white",
            linewidth=0.6,
            alpha=0.96,
            zorder=3,
            label=group,
        )
        ax_cleanup.scatter(
            [row["fixed_overlap"] for row in subset],
            [row["hybrid_cleanup"] for row in subset],
            s=76,
            marker=style["marker"],
            color=style["color"],
            edgecolor="white",
            linewidth=0.6,
            alpha=0.96,
            zorder=3,
        )

    label_effect = [pe.Stroke(linewidth=1.4, foreground="white"), pe.Normal()]
    labeled_points = {"Complex", "USGS-H", "Slope"}
    for row in records:
        if row["short"] not in labeled_points:
            continue
        ax_gain.annotate(
            row["short"],
            (row["fixed_overlap"], row["hybrid_gain"]),
            xytext=offsets_gain[row["short"]],
            textcoords="offset points",
            fontsize=8.30,
            color=TEXT,
            path_effects=label_effect,
        )
        ax_cleanup.annotate(
            row["short"],
            (row["fixed_overlap"], row["hybrid_cleanup"]),
            xytext=offsets_cleanup[row["short"]],
            textcoords="offset points",
            fontsize=8.30,
            color=TEXT,
            path_effects=label_effect,
        )

    x_max = max(float(row["fixed_overlap"]) for row in records) + 1.9
    ax_cleanup.plot([0.0, x_max], [0.0, x_max], color="#93a3b2", linewidth=0.72, linestyle=(0, (3.5, 2.2)), zorder=1)
    ax_cleanup.text(
        0.955,
        0.10,
        "1:1 cleanup",
        transform=ax_cleanup.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.20,
        color=MUTED,
    )

    ax_gain.set_title("(a) Burden vs path gain", loc="left", color=TEXT, fontweight="bold", fontsize=8.85, pad=5.0)
    ax_gain.set_xlabel("Fixed excess overlap (%)", fontsize=8.55)
    ax_gain.set_ylabel("Hybrid path gain (%)", fontsize=8.55)
    ax_gain.set_xlim(-0.6, x_max)
    ax_gain.set_ylim(-1.2, 28.6)
    ax_gain.annotate(
        "GEBCO\n<1% $O_{ex}$",
        xy=(0.81, 0.75),
        xytext=(5.8, 5.6),
        textcoords="data",
        fontsize=8.15,
        color=MUTED,
        arrowprops={"arrowstyle": "-", "lw": 0.55, "color": "#94a5b4"},
        bbox={"facecolor": "white", "edgecolor": "#d7e2eb", "linewidth": 0.30, "alpha": 0.84, "pad": 0.48},
    )

    ax_cleanup.set_title("(b) Burden vs overlap cleanup", loc="left", color=TEXT, fontweight="bold", fontsize=8.85, pad=5.0)
    ax_cleanup.set_xlabel("Fixed excess overlap (%)", fontsize=8.55)
    ax_cleanup.set_ylabel("Overlap reduction (pp)", fontsize=8.55)
    ax_cleanup.set_xlim(-0.6, x_max)
    ax_cleanup.set_ylim(-0.5, 30.4)

    selected = [
        row
        for row in records
        if row["short"] in {"Cascadia", "Monterey", "Slope", "Complex", "USGS-H"}
    ]
    selected = sorted(selected, key=lambda row: float(row["fixed_overlap"]))
    y = np.arange(len(selected))
    fixed_vals = np.asarray([float(row["fixed_overlap"]) for row in selected])
    cleanup_vals = np.asarray([float(row["hybrid_cleanup"]) for row in selected])
    hybrid_vals = np.maximum(fixed_vals - cleanup_vals, 0.0)
    ax_ladder.barh(y + 0.16, fixed_vals, height=0.27, color="#8d96a3", alpha=0.82, label="Fixed overlap")
    ax_ladder.barh(y - 0.16, hybrid_vals, height=0.27, color="#c56335", alpha=0.88, label="Hybrid residual")
    for ypos, fixed, hybrid in zip(y, fixed_vals, hybrid_vals):
        ax_ladder.plot([hybrid, fixed], [ypos, ypos], color="#bdc7d0", linewidth=0.72, zorder=1)
    ax_ladder.set_yticks(y)
    ax_ladder.set_yticklabels([str(row["short"]) for row in selected], fontsize=8.20)
    ax_ladder.set_xlabel("Excess overlap (%)", fontsize=8.55)
    ax_ladder.set_title("(c) Regime ladder", loc="left", color=TEXT, fontweight="bold", fontsize=8.85, pad=5.0)
    ax_ladder.set_xlim(0.0, max(fixed_vals) + 3.0)
    ax_ladder.legend(loc="lower right", frameon=True, framealpha=0.92, fontsize=7.75, borderpad=0.25, ncol=2)

    leg = ax_gain.legend(loc="upper left", frameon=True, framealpha=0.92, borderpad=0.28, fontsize=7.75, handlelength=1.3)
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("#d7e2eb")
    leg.get_frame().set_linewidth(0.32)

    fig.subplots_adjust(left=0.082, right=0.990, top=0.925, bottom=0.120)
    fig.savefig(PIC / "journal_overlap_regime.png", bbox_inches="tight", facecolor="white", pad_inches=0.025)
    plt.close(fig)


def flatten_png(path: Path) -> None:
    im = Image.open(path)
    rgba = im.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    bg.alpha_composite(rgba)
    bg.convert("RGB").save(path, optimize=True)


def main() -> None:
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = load_summary()
    raw_rows = load_raw_rows()
    make_atlas(summary_rows)
    make_public_layout_matrix(summary_rows)
    make_public_route_figures(summary_rows)
    make_metric_heatmap(summary_rows)
    make_overlap_regime_diagnostic(summary_rows)
    make_ablation_seed(summary_rows, raw_rows)
    for name in [
        "journal_scene_atlas.png",
        "journal_public_layout_matrix.png",
        "journal_cascadia_routes.png",
        "journal_monterey_routes.png",
        "journal_metric_heatmap.png",
        "journal_overlap_regime.png",
        "journal_ablation_seed.png",
    ]:
        flatten_png(PIC / name)
        for pic_dir in PIC_DIRS[1:]:
            shutil.copy2(PIC / name, pic_dir / name)
        print(PIC / name)


if __name__ == "__main__":
    main()
