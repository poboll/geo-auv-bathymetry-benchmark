from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import Colormap, LinearSegmentedColormap, Normalize
from PIL import Image


TEXT = "#1d2730"
MUTED = "#5f6d78"
GRID = "#f7f4ed"
SPINE = "#e8e0d3"
GROUP = "#d9d0c2"
BAD = "#7c3f36"
BG = "#ffffff"

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
FAILURE_CMAP = LinearSegmentedColormap.from_list(
    "journal_failure",
    ["#fffaf0", "#efd7aa", "#d39565", "#a9554a", "#6d3339"],
)


def apply_rc(base_font: float = 9.05) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica Neue", "Helvetica", "DejaVu Sans"],
            "font.serif": ["Arial", "Helvetica Neue", "Helvetica", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "font.size": base_font,
            "axes.titlesize": 8.35,
            "axes.labelsize": 7.95,
            "xtick.labelsize": 7.35,
            "ytick.labelsize": 7.35,
            "axes.linewidth": 0.0,
            "savefig.dpi": 450,
        }
    )


def cell_text_color(cmap: Colormap, norm: Normalize, value: float) -> str:
    rgba = cmap(norm(value))
    luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
    return "white" if luminance < 0.43 else TEXT


def style_heatmap_axis(
    ax: Axes,
    title: str,
    col_labels: Sequence[str],
    row_labels: Sequence[str] | None,
    n_rows: int,
    *,
    rotate_x: float = 0.0,
    group_every: int | None = None,
    group_start: int = 0,
) -> None:
    ax.set_title(title, loc="left", color=TEXT, fontweight="semibold", fontsize=8.28, pad=2.8)
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, color=TEXT, rotation=rotate_x, ha="left" if rotate_x else "center")
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, pad=0.82, length=0.0)
    for tick in ax.get_xticklabels():
        tick.set_fontweight("normal")
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(row_labels if row_labels is not None else [])
    ax.tick_params(axis="y", length=0.0, pad=1.05)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if group_every:
        for y in range(group_start + group_every, n_rows, group_every):
            ax.axhline(y - 0.5, color=GROUP, linewidth=0.62, alpha=0.95)
    ax.set_facecolor(BG)


def annotate_cells(
    ax: Axes,
    data: np.ndarray,
    cmap: Colormap,
    norm: Normalize,
    fmt: str,
    *,
    mark_bad: Callable[[float], bool] | None = None,
    fontsize: float = 7.12,
) -> None:
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = float(data[i, j])
            ax.text(
                j,
                i,
                fmt.format(value),
                ha="center",
                va="center",
                fontsize=fontsize,
                color=cell_text_color(cmap, norm, value),
                fontweight="normal",
            )


def add_panel_note(fig, text: str, *, x: float = 0.012, y: float = 0.986) -> None:
    fig.text(x, y, text, ha="left", va="top", fontsize=6.1, color=MUTED)


def save_white_rgb(fig, path: Path, *, dpi: int = 420, pad_inches: float = 0.02) -> None:
    """Save a Matplotlib figure as a white-background RGB PNG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white", pad_inches=pad_inches)
    image = Image.open(path).convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    background.convert("RGB").save(path, optimize=True)
