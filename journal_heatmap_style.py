from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import Colormap, LinearSegmentedColormap, Normalize
from PIL import Image


TEXT = "#1f2a35"
MUTED = "#65727f"
GRID = "#ffffff"
SPINE = "#ffffff"
GROUP = "#ffffff"
BAD = "#8a4637"
BG = "#ffffff"

PATH_GAIN_CMAP = LinearSegmentedColormap.from_list(
    "journal_path_gain",
    ["#f7fbff", "#deebf7", "#9ecae1", "#3182bd", "#08519c"],
)
COVERAGE_CMAP = LinearSegmentedColormap.from_list(
    "journal_coverage",
    ["#b35c3a", "#e6b27e", "#f7f7f2", "#92c5de", "#2b6c9f"],
)
OVERLAP_CMAP = LinearSegmentedColormap.from_list(
    "journal_overlap",
    ["#fffff5", "#fee6b8", "#fdbb84", "#e34a33", "#7f0000"],
)
TIME_CMAP = LinearSegmentedColormap.from_list(
    "journal_time",
    ["#f8fafc", "#dbe2ea", "#a8b4c0", "#64748b", "#334155"],
)
FAILURE_CMAP = LinearSegmentedColormap.from_list(
    "journal_failure",
    ["#fffff5", "#fee6b8", "#fdbb84", "#d7301f", "#7f0000"],
)


def apply_rc(base_font: float = 8.80) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
            "font.serif": ["Helvetica", "Arial", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "font.size": base_font,
            "axes.titlesize": 8.00,
            "axes.labelsize": 7.40,
            "xtick.labelsize": 6.90,
            "ytick.labelsize": 6.90,
            "axes.linewidth": 0.0,
            "savefig.dpi": 420,
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
    ax.set_title(title, loc="left", color=TEXT, fontweight="semibold", fontsize=7.75, pad=4.8)
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, color=TEXT, rotation=rotate_x, ha="left" if rotate_x else "center")
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, pad=1.7, length=0.0)
    for tick in ax.get_xticklabels():
        tick.set_fontweight("normal")
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(row_labels if row_labels is not None else [])
    ax.tick_params(axis="y", length=0.0, pad=2.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_facecolor(BG)


def annotate_cells(
    ax: Axes,
    data: np.ndarray,
    cmap: Colormap,
    norm: Normalize,
    fmt: str,
    *,
    mark_bad: Callable[[float], bool] | None = None,
    fontsize: float = 6.65,
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
