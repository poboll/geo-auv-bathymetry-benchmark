from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parent
SENSITIVITY = ROOT / "sensitivity"
MANUSCRIPT_PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

METHODS = (
    ("Fixed-Spacing", "Fixed"),
    ("Adaptive Spacing w/o GA", "Adaptive"),
    ("Full Geometry-Aware Hybrid GA", "Hybrid GA"),
)
SCENES = (
    ("gebco_cascadia_margin_moderate", "Cascadia"),
    ("gebco_monterey_canyon_complex", "Monterey"),
)

COVERAGE_TARGET = 97.0


@dataclass(frozen=True)
class SensitivityFigureSpec:
    csv_name: str
    output_name: str
    parameter_key: str
    x_values: tuple[float, ...]
    x_labels: tuple[str, ...]
    title: str
    footnote: str


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def find_row(
    rows: list[dict[str, str]],
    *,
    scene_id: str,
    method: str,
    parameter_key: str,
    parameter_value: float,
) -> dict[str, str]:
    for row in rows:
        if row["scene_id"] != scene_id or row["method"] != method:
            continue
        if np.isclose(float(row[parameter_key]), parameter_value):
            return row
    raise KeyError((scene_id, method, parameter_key, parameter_value))


def collect_metric_matrix(
    rows: list[dict[str, str]],
    spec: SensitivityFigureSpec,
    metric_key: str,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.full((len(SCENES) * len(METHODS), len(spec.x_values)), np.nan, dtype=float)
    feasible = np.full_like(values, np.nan)
    for scene_i, (scene_id, _scene_label) in enumerate(SCENES):
        for method_i, (method, _method_label) in enumerate(METHODS):
            row_i = scene_i * len(METHODS) + method_i
            for col_i, value in enumerate(spec.x_values):
                row = find_row(
                    rows,
                    scene_id=scene_id,
                    method=method,
                    parameter_key=spec.parameter_key,
                    parameter_value=value,
                )
                values[row_i, col_i] = float(row[metric_key])
                feasible[row_i, col_i] = float(row.get("feasible_mean", "1.0"))
    return values, feasible


def row_labels() -> list[str]:
    labels: list[str] = []
    for scene_label in [scene[1] for scene in SCENES]:
        for _method, method_label in METHODS:
            labels.append(f"{scene_label} - {method_label}")
    return labels


def metric_style(values: np.ndarray, metric: str) -> tuple[mcolors.Normalize, mcolors.Colormap, str]:
    if metric == "coverage_margin":
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "coverage_margin",
            ["#b84631", "#f0c98f", "#f8f4e8", "#8fc6b8", "#235f72"],
        )
        return mcolors.TwoSlopeNorm(vmin=-0.8, vcenter=0.0, vmax=3.2), cmap, "Coverage margin vs 97% (pp)"
    if metric == "excess_overlap_pct_mean":
        vmax = max(1.0, float(np.nanpercentile(values, 95)))
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "overlap_low_is_good",
            ["#0f5f67", "#8ac5b7", "#f8f4e8", "#e4a056", "#9d4a34"],
        )
        return mcolors.Normalize(vmin=0.0, vmax=vmax), cmap, "Excess-overlap violation (%)"
    vmax = max(1.0, float(np.nanmax(values)))
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "path_gain",
        ["#f4efe5", "#c5d8d7", "#79a9b0", "#386b83", "#17364d"],
    )
    return mcolors.Normalize(vmin=0.0, vmax=vmax), cmap, "Path gain vs fixed (%)"


def text_color_for_cell(norm: mcolors.Normalize, cmap: mcolors.Colormap, value: float) -> str:
    rgba = cmap(norm(value))
    luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
    return "#17212b" if luminance > 0.58 else "white"


def draw_matrix_panel(
    ax,
    values: np.ndarray,
    feasible: np.ndarray,
    *,
    metric_name: str,
    title: str,
    x_labels: tuple[str, ...],
    show_ylabels: bool,
) -> None:
    norm, cmap, cbar_label = metric_style(values, metric_name)
    ax.imshow(values, cmap=cmap, norm=norm, aspect="equal")
    ax.set_title(title, loc="left", fontweight="bold", pad=8)

    ax.set_xticks(np.arange(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_yticks(np.arange(len(row_labels())))
    ax.set_yticklabels(row_labels() if show_ylabels else [])
    ax.tick_params(axis="x", labelrotation=0, length=0, pad=5)
    ax.tick_params(axis="y", length=0, pad=6)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(x_labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, values.shape[0], 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.25)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.axhline(2.5, color="#23313d", linewidth=1.0)

    for row_i in range(values.shape[0]):
        for col_i in range(values.shape[1]):
            value = float(values[row_i, col_i])
            if metric_name == "coverage_margin":
                label = f"{value:+.2f}"
            else:
                label = f"{value:.2f}"
            ax.text(
                col_i,
                row_i,
                label,
                ha="center",
                va="center",
                color=text_color_for_cell(norm, cmap, value),
                fontsize=7.6,
                fontweight="bold" if metric_name == "coverage_margin" and value < 0.75 else "normal",
            )
            if feasible[row_i, col_i] < 0.999:
                ax.add_patch(
                    Rectangle(
                        (col_i - 0.49, row_i - 0.49),
                        0.98,
                        0.98,
                        fill=False,
                        edgecolor="#1d1f23",
                        linewidth=1.4,
                    )
                )
                ax.text(
                    col_i - 0.38,
                    row_i - 0.36,
                    f"F={feasible[row_i, col_i]:.2f}",
                    ha="left",
                    va="top",
                    fontsize=6.0,
                    color="#1d1f23",
                    bbox={
                        "boxstyle": "round,pad=0.12",
                        "facecolor": "white",
                        "edgecolor": "none",
                        "alpha": 0.82,
                    },
                )

    cbar = ax.figure.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        ax=ax,
        fraction=0.046,
        pad=0.025,
    )
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(length=0, labelsize=6.6, pad=2)
    cbar.set_label(cbar_label, fontsize=6.9, labelpad=3)


def make_figure(spec: SensitivityFigureSpec) -> None:
    rows = read_rows(SENSITIVITY / spec.csv_name)
    coverage, feasible = collect_metric_matrix(rows, spec, "coverage_pct_mean")
    overlap, _ = collect_metric_matrix(rows, spec, "excess_overlap_pct_mean")
    gain, _ = collect_metric_matrix(rows, spec, "path_gain_vs_fixed_pct_mean")
    coverage_margin = coverage - COVERAGE_TARGET

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 7.4,
            "axes.titlesize": 7.9,
            "xtick.labelsize": 7.4,
            "ytick.labelsize": 7.2,
            "savefig.dpi": 450,
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 4.05), constrained_layout=False)
    fig.patch.set_facecolor("white")
    fig.suptitle(spec.title, x=0.013, y=0.975, ha="left", fontsize=8.1, fontweight="bold")

    draw_matrix_panel(
        axes[0],
        coverage_margin,
        feasible,
        metric_name="coverage_margin",
        title="Coverage safety margin",
        x_labels=spec.x_labels,
        show_ylabels=True,
    )
    draw_matrix_panel(
        axes[1],
        overlap,
        feasible,
        metric_name="excess_overlap_pct_mean",
        title="Overlap cleanup",
        x_labels=spec.x_labels,
        show_ylabels=False,
    )
    draw_matrix_panel(
        axes[2],
        gain,
        feasible,
        metric_name="path_gain_vs_fixed_pct_mean",
        title="Route economy",
        x_labels=spec.x_labels,
        show_ylabels=False,
    )
    fig.subplots_adjust(left=0.035, right=0.995, top=0.88, bottom=0.075, wspace=0.34)

    for pic_dir in MANUSCRIPT_PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(pic_dir / spec.output_name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    specs = (
        SensitivityFigureSpec(
            csv_name="target_overlap_sensitivity_summary.csv",
            output_name="journal_sensitivity_overlap_target.png",
            parameter_key="target_overlap",
            x_values=(0.10, 0.15, 0.20),
            x_labels=("10%", "15%", "20%"),
            title="Target-overlap design-margin sensitivity",
            footnote=(
                "Rows are scene-method pairs; columns are declared overlap margins. "
                "Cell borders mark any stochastic setting with feasibility below 1.0."
            ),
        ),
        SensitivityFigureSpec(
            csv_name="resolution_sensitivity_summary.csv",
            output_name="journal_sensitivity_resolution.png",
            parameter_key="resolution_stride",
            x_values=(1.0, 2.0, 3.0),
            x_labels=("native", "2x", "3x"),
            title="Public-grid resolution sensitivity",
            footnote=(
                "Coverage margin is reported relative to the 97% acceptance gate. "
                "The Monterey Hybrid 3x cell exposes a reduced seed-level feasibility margin."
            ),
        ),
        SensitivityFigureSpec(
            csv_name="beam_angle_sensitivity_summary.csv",
            output_name="journal_sensitivity_beam_angle.png",
            parameter_key="beam_angle_deg",
            x_values=(100.0, 110.0, 120.0, 130.0),
            x_labels=("100 deg", "110 deg", "120 deg", "130 deg"),
            title="MBES opening-angle sensitivity",
            footnote="This is a local idealized-footprint check, not a real-sonar calibration study.",
        ),
        SensitivityFigureSpec(
            csv_name="prior_depth_bias_sensitivity_summary.csv",
            output_name="journal_sensitivity_prior_depth_bias.png",
            parameter_key="planning_depth_bias_m",
            x_values=(-150.0, 0.0, 150.0),
            x_labels=("-150 m", "0 m", "+150 m"),
            title="Uniform prior-depth-bias sensitivity",
            footnote="Layouts are planned on biased public priors and evaluated on the native public GEBCO grids.",
        ),
        SensitivityFigureSpec(
            csv_name="prior_relief_scale_sensitivity_summary.csv",
            output_name="journal_sensitivity_prior_relief_scale.png",
            parameter_key="planning_relief_scale",
            x_values=(0.7, 1.0, 1.3),
            x_labels=("0.7x", "1.0x", "1.3x"),
            title="Uniform relief-scale sensitivity",
            footnote="Uniform relief scaling rules out trivial amplitude sensitivity but not spatially structured prior error.",
        ),
    )
    for spec in specs:
        make_figure(spec)
        print(f"Wrote {spec.output_name} to active manuscript figure directories")


if __name__ == "__main__":
    main()
