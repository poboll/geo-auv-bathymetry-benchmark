from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "vehicle_aware_posteval"
PIC_DIRS = [
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
]

MAIN_RESULTS = ROOT / "run_5" / "benchmark_results.csv"
USGS_RESULTS = ROOT / "usgs_cascadia_extension" / "benchmark_results.csv"
SEGMENTED_RESULTS = ROOT / "segmented_heading_extension" / "segmented_heading_raw.csv"

RADIUS_VALUES_M = (25.0, 50.0, 100.0)
SURVEY_SPEED_MPS = 1.5
TURN_SPEED_MPS = 0.75

SINGLE_METHODS = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
)
SEGMENTED_METHODS = (
    "Fixed-Spacing",
    "Full Geometry-Aware Hybrid GA",
    "Coverage-Preserving Segmented Hybrid",
    "Transition-Aware Segmented Hybrid",
)

METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adaptive",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
    "Coverage-Preserving Segmented Hybrid": "Segmented",
    "Transition-Aware Segmented Hybrid": "TA-Seg",
}
METHOD_COLORS = {
    "Fixed-Spacing": "#6f7782",
    "Adaptive Spacing w/o GA": "#1f8f83",
    "Full Geometry-Aware Hybrid GA": "#c66b3d",
    "Coverage-Preserving Segmented Hybrid": "#3a739c",
    "Transition-Aware Segmented Hybrid": "#245f7d",
}
SCENE_SHORT = {
    "gebco_cascadia_margin_moderate": "GEBCO\nCascadia",
    "gebco_monterey_canyon_complex": "GEBCO\nMonterey",
    "usgs_southern_cascadia_30m_high": "USGS\nHigh",
    "synthetic_complex": "Synthetic\nComplex",
}
TEXT = "#202a33"
MUTED = "#687583"
GRID = "#d8e1e9"
SPINE = "#b9c4ce"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _num(row: pd.Series, key: str, default: float = 0.0) -> float:
    if key not in row or pd.isna(row[key]):
        return default
    try:
        return float(row[key])
    except (TypeError, ValueError):
        return default


def _int(row: pd.Series, key: str, default: int = 0) -> int:
    return int(round(_num(row, key, float(default))))


def _records_from_benchmark(path: Path, evidence_block: str) -> list[dict[str, Any]]:
    df = _read_csv(path)
    df = df[df["method"].isin(SINGLE_METHODS)].copy()
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        path_length = _num(row, "path_length_km")
        records.append(
            {
                "evidence_block": evidence_block,
                "scene_id": str(row["scene_id"]),
                "scene_name": str(row["scene_name"]),
                "scene_group": str(row["scene_group"]),
                "terrain_class": str(row["terrain_class"]),
                "method": str(row["method"]),
                "seed": _int(row, "seed"),
                "n_segments": 1,
                "path_length_km": path_length,
                "path_without_transition_km": path_length,
                "boundary_transition_km": 0.0,
                "heading_turn_transition_km_at_base_radius": 0.0,
                "base_min_turn_radius_m": 0.0,
                "coverage_pct": _num(row, "coverage_pct"),
                "excess_overlap_pct": _num(row, "excess_overlap_pct"),
                "line_count": _int(row, "line_count"),
                "feasible": _int(row, "feasible"),
            }
        )
    return records


def _records_from_segmented(path: Path) -> list[dict[str, Any]]:
    df = _read_csv(path)
    df = df[df["method"].isin(SEGMENTED_METHODS)].copy()
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        path_length = _num(row, "path_length_km")
        path_without_transition = _num(row, "path_without_transition_km", path_length)
        records.append(
            {
                "evidence_block": "segmented_diagnostic",
                "scene_id": str(row["scene_id"]),
                "scene_name": str(row["scene_name"]),
                "scene_group": str(row["scene_group"]),
                "terrain_class": str(row["terrain_class"]),
                "method": str(row["method"]),
                "seed": _int(row, "seed"),
                "n_segments": max(_int(row, "n_segments", 1), 1),
                "path_length_km": path_length,
                "path_without_transition_km": path_without_transition,
                "boundary_transition_km": _num(row, "boundary_transition_km"),
                "heading_turn_transition_km_at_base_radius": _num(row, "turn_transition_km"),
                "base_min_turn_radius_m": _num(row, "min_turn_radius_m"),
                "coverage_pct": _num(row, "coverage_pct"),
                "excess_overlap_pct": _num(row, "excess_overlap_pct"),
                "line_count": _int(row, "line_count"),
                "feasible": _int(row, "feasible"),
            }
        )
    return records


def _vehicle_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        for radius_m in RADIUS_VALUES_M:
            n_segments = max(int(record["n_segments"]), 1)
            line_count = max(int(record["line_count"]), 0)
            line_change_count = max(line_count - n_segments, 0)
            base_radius = float(record["base_min_turn_radius_m"])
            base_heading_arc = float(record["heading_turn_transition_km_at_base_radius"])
            heading_arc_km = 0.0 if base_radius <= 0.0 else base_heading_arc * radius_m / base_radius
            line_change_arc_km = line_change_count * math.pi * radius_m / 1000.0
            vehicle_length_km = (
                float(record["path_without_transition_km"])
                + float(record["boundary_transition_km"])
                + heading_arc_km
                + line_change_arc_km
            )
            turn_arc_km = heading_arc_km + line_change_arc_km
            base_motion_km = vehicle_length_km - turn_arc_km
            mission_time_h = (
                base_motion_km * 1000.0 / SURVEY_SPEED_MPS
                + turn_arc_km * 1000.0 / TURN_SPEED_MPS
            ) / 3600.0
            row = {
                **record,
                "radius_m": float(radius_m),
                "line_change_count": int(line_change_count),
                "line_change_turn_arc_km": float(line_change_arc_km),
                "heading_turn_arc_km": float(heading_arc_km),
                "total_turn_arc_km": float(turn_arc_km),
                "vehicle_length_km": float(vehicle_length_km),
                "turn_arc_fraction_pct": 100.0 * turn_arc_km / vehicle_length_km if vehicle_length_km > 0 else 0.0,
                "mission_time_h": float(mission_time_h),
            }
            rows.append(row)

    baseline: dict[tuple[str, str, float], dict[str, Any]] = {}
    for row in rows:
        if row["method"] == "Fixed-Spacing":
            baseline[(row["evidence_block"], row["scene_id"], row["radius_m"])] = row

    for row in rows:
        fixed = baseline.get((row["evidence_block"], row["scene_id"], row["radius_m"]))
        if fixed is None:
            row["vehicle_length_gain_vs_fixed_pct"] = np.nan
            row["mission_time_gain_vs_fixed_pct"] = np.nan
            continue
        row["vehicle_length_gain_vs_fixed_pct"] = (
            (fixed["vehicle_length_km"] - row["vehicle_length_km"]) / fixed["vehicle_length_km"] * 100.0
            if fixed["vehicle_length_km"] > 0
            else np.nan
        )
        row["mission_time_gain_vs_fixed_pct"] = (
            (fixed["mission_time_h"] - row["mission_time_h"]) / fixed["mission_time_h"] * 100.0
            if fixed["mission_time_h"] > 0
            else np.nan
        )
    return rows


def _summary(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    group_cols = [
        "evidence_block",
        "scene_id",
        "scene_name",
        "scene_group",
        "terrain_class",
        "method",
        "n_segments",
        "radius_m",
    ]
    value_cols = [
        "path_length_km",
        "vehicle_length_km",
        "mission_time_h",
        "vehicle_length_gain_vs_fixed_pct",
        "mission_time_gain_vs_fixed_pct",
        "turn_arc_fraction_pct",
        "line_count",
        "line_change_count",
        "coverage_pct",
        "excess_overlap_pct",
        "feasible",
    ]
    agg = df.groupby(group_cols, dropna=False)[value_cols].agg(["mean", "std", "min", "max"]).reset_index()
    agg.columns = [
        "_".join(str(part) for part in col if str(part))
        if isinstance(col, tuple)
        else str(col)
        for col in agg.columns
    ]
    runs = df.groupby(group_cols, dropna=False).size().reset_index(name="n_runs")
    return runs.merge(agg, on=group_cols, how="left")


def _metric(summary: pd.DataFrame, block: str, scene: str, method: str, radius: float, metric: str) -> float:
    match = summary[
        (summary["evidence_block"] == block)
        & (summary["scene_id"] == scene)
        & (summary["method"] == method)
        & (summary["radius_m"] == radius)
    ]
    if match.empty:
        return np.nan
    return float(match.iloc[0][metric])


def _style_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_color(SPINE)
        spine.set_linewidth(0.50)
    ax.tick_params(colors=TEXT, width=0.45, length=2.2, pad=1.4)
    ax.grid(True, axis=grid_axis, color=GRID, linewidth=0.42, alpha=0.70)
    ax.set_axisbelow(True)


def _save_white_rgb(fig: plt.Figure, path: Path) -> None:
    """Save a Matplotlib figure as an opaque white-background RGB PNG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    image = Image.open(path).convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    background.convert("RGB").save(path, optimize=True)


def make_figure(summary: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "font.size": 7.35,
            "axes.titlesize": 8.05,
            "axes.labelsize": 7.30,
            "xtick.labelsize": 6.55,
            "ytick.labelsize": 6.55,
            "legend.fontsize": 6.65,
            "savefig.dpi": 420,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(7.45, 4.90), constrained_layout=False)
    fig.set_facecolor("white")

    selected = [
        ("main_benchmark", "gebco_cascadia_margin_moderate"),
        ("main_benchmark", "gebco_monterey_canyon_complex"),
        ("usgs_extension", "usgs_southern_cascadia_30m_high"),
        ("segmented_diagnostic", "synthetic_complex"),
    ]
    methods = [
        "Adaptive Spacing w/o GA",
        "Full Geometry-Aware Hybrid GA",
        "Transition-Aware Segmented Hybrid",
    ]

    ax = axes[0, 0]
    _style_axes(ax)
    x = np.arange(len(selected))
    width = 0.22
    for idx, method in enumerate(methods):
        values = []
        feasible_flags = []
        for block, scene in selected:
            value = _metric(summary, block, scene, method, 100.0, "mission_time_gain_vs_fixed_pct_mean")
            feasible = _metric(summary, block, scene, method, 100.0, "feasible_mean")
            feasible_flags.append(feasible)
            values.append(value if np.isnan(feasible) or feasible >= 0.999 else np.nan)
        xpos = x + (idx - 1) * width
        ax.bar(
            xpos,
            [0.0 if np.isnan(v) else v for v in values],
            width=width,
            color=METHOD_COLORS[method],
            label=METHOD_LABELS[method],
            alpha=0.94,
            edgecolor="white",
            linewidth=0.35,
        )
        for px, value in zip(xpos, values):
            if not np.isnan(value):
                ax.text(px, value + 0.33, f"{value:.1f}", ha="center", va="bottom", color=TEXT, fontsize=5.75)
        for px, value, feasible in zip(xpos, values, feasible_flags):
            if np.isnan(value) and not np.isnan(feasible) and feasible < 0.999:
                ax.text(px, 0.55, "infeas.", ha="center", va="bottom", color="#8b3f2f", fontsize=5.75, rotation=90)
    ax.axhline(0, color=SPINE, linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([SCENE_SHORT[scene] for _, scene in selected])
    ax.set_ylabel("Mission-time gain vs Fixed (%)")
    ax.set_title("(a) Execution-time proxy at $R_{\\min}=100$ m", loc="left", fontweight="bold", color=TEXT)
    ax.margins(y=0.12)
    legend_handles, legend_labels = ax.get_legend_handles_labels()

    ax = axes[0, 1]
    _style_axes(ax)
    shown_methods = ["Fixed-Spacing", "Full Geometry-Aware Hybrid GA", "Transition-Aware Segmented Hybrid"]
    width = 0.24
    for idx, method in enumerate(shown_methods):
        values = [
            _metric(summary, block, scene, method, 100.0, "turn_arc_fraction_pct_mean")
            for block, scene in selected
        ]
        xpos = x + (idx - 1) * width
        ax.bar(
            xpos,
            [0.0 if np.isnan(v) else v for v in values],
            width=width,
            color=METHOD_COLORS[method],
            alpha=0.90,
            edgecolor="white",
            linewidth=0.35,
            label=METHOD_LABELS[method],
        )
    ax.set_xticks(x)
    ax.set_xticklabels([SCENE_SHORT[scene] for _, scene in selected])
    ax.set_ylabel("Turn-arc share of effective length (%)")
    ax.set_title("(b) How much of the proxy path is turning?", loc="left", fontweight="bold", color=TEXT)
    ax.margins(y=0.12)

    ax = axes[1, 0]
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_color(SPINE)
        spine.set_linewidth(0.50)
    matrix_specs = [
        ("main_benchmark", "gebco_monterey_canyon_complex", "Full Geometry-Aware Hybrid GA", "Monterey Hybrid"),
        ("usgs_extension", "usgs_southern_cascadia_30m_high", "Full Geometry-Aware Hybrid GA", "USGS High Hybrid"),
        (
            "segmented_diagnostic",
            "synthetic_complex",
            "Transition-Aware Segmented Hybrid",
            "Complex TA-Seg",
        ),
    ]
    matrix = np.asarray(
        [
            [
                _metric(summary, block, scene, method, radius, "mission_time_gain_vs_fixed_pct_mean")
                for radius in RADIUS_VALUES_M
            ]
            for block, scene, method, _label in matrix_specs
        ],
        dtype=float,
    )
    cmap = plt.get_cmap("PuBuGn").copy()
    cmap.set_bad("#f1f4f6")
    im = ax.imshow(np.ma.masked_invalid(matrix), aspect="equal", cmap=cmap, vmin=0.0, vmax=max(25.0, np.nanmax(matrix)))
    ax.set_xticks(np.arange(len(RADIUS_VALUES_M)))
    ax.set_xticklabels([f"{radius:.0f}" for radius in RADIUS_VALUES_M])
    ax.set_yticks(np.arange(len(matrix_specs)))
    ax.set_yticklabels([label for *_rest, label in matrix_specs])
    ax.set_xlabel("Minimum turn radius (m)")
    ax.set_title("(c) Discrete radius-sensitivity evidence", loc="left", fontweight="bold", color=TEXT)
    ax.tick_params(colors=TEXT, width=0.45, length=0.0, pad=2.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            value = matrix[row_idx, col_idx]
            if np.isnan(value):
                label = "--"
                color = MUTED
            else:
                label = f"{value:.1f}"
                color = "white" if value > 13.0 else TEXT
            ax.text(col_idx, row_idx, label, ha="center", va="center", fontsize=6.65, fontweight="bold", color=color)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.018)
    cbar.ax.tick_params(labelsize=5.65, colors=TEXT, width=0.35, length=1.8)
    cbar.outline.set_edgecolor(SPINE)
    cbar.outline.set_linewidth(0.45)
    cbar.set_label("gain (%)", fontsize=5.75, color=TEXT, labelpad=1.8)

    ax = axes[1, 1]
    _style_axes(ax)
    decomposition = [
        ("usgs_extension", "usgs_southern_cascadia_30m_high", "Fixed-Spacing", "USGS\nFixed"),
        ("usgs_extension", "usgs_southern_cascadia_30m_high", "Full Geometry-Aware Hybrid GA", "USGS\nHybrid"),
        ("segmented_diagnostic", "synthetic_complex", "Full Geometry-Aware Hybrid GA", "Complex\nSingle\n(infeas.)"),
        (
            "segmented_diagnostic",
            "synthetic_complex",
            "Transition-Aware Segmented Hybrid",
            "Complex\nSegmented",
        ),
    ]
    xpos = np.arange(len(decomposition))
    base_hours = []
    turn_hours = []
    for block, scene, method, _label in decomposition:
        vehicle_h = _metric(summary, block, scene, method, 100.0, "mission_time_h_mean")
        turn_frac = _metric(summary, block, scene, method, 100.0, "turn_arc_fraction_pct_mean") / 100.0
        if np.isnan(vehicle_h):
            base_hours.append(0.0)
            turn_hours.append(0.0)
        else:
            # The time share is larger than the length share because turns use the slower declared speed.
            row = summary[
                (summary["evidence_block"] == block)
                & (summary["scene_id"] == scene)
                & (summary["method"] == method)
                & (summary["radius_m"] == 100.0)
            ].iloc[0]
            turn_km = float(row["turn_arc_fraction_pct_mean"]) / 100.0 * float(row["vehicle_length_km_mean"])
            turn_time_h = turn_km * 1000.0 / TURN_SPEED_MPS / 3600.0
            base_hours.append(max(vehicle_h - turn_time_h, 0.0))
            turn_hours.append(turn_time_h)
    ax.bar(
        xpos,
        base_hours,
        color="#cdd8e3",
        width=0.58,
        label="survey + transit",
        edgecolor="white",
        linewidth=0.35,
    )
    ax.bar(
        xpos,
        turn_hours,
        bottom=base_hours,
        color="#cf8457",
        width=0.58,
        label="turn arcs",
        edgecolor="white",
        linewidth=0.35,
    )
    ax.set_xticks(xpos)
    ax.set_xticklabels([label for *_rest, label in decomposition])
    ax.set_ylabel("Mission-time proxy (h)")
    ax.set_title("(d) Execution burden in harder cases", loc="left", fontweight="bold", color=TEXT)
    ax.legend(frameon=False, loc="upper left", handlelength=1.5)

    fig.subplots_adjust(left=0.070, right=0.985, bottom=0.150, top=0.855, wspace=0.28, hspace=0.46)
    fig.text(
        0.070,
        0.982,
        "Vehicle-aware post-evaluation: mission-time proxy and turning burden",
        ha="left",
        va="top",
        color=TEXT,
        fontsize=8.85,
        fontweight="bold",
    )
    fig.legend(
        legend_handles,
        legend_labels,
        ncol=3,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.60, 0.962),
        columnspacing=1.35,
        handlelength=1.55,
    )
    fig.text(
        0.070,
        0.040,
        f"Diagnostic only: base path is evaluated at {SURVEY_SPEED_MPS:.1f} m/s; turn arcs at {TURN_SPEED_MPS:.2f} m/s. "
        "It does not include current, controller, SLAM, or deployment logs.",
        ha="left",
        color=MUTED,
        fontsize=5.90,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "vehicle_aware_posteval.png"
    _save_white_rgb(fig, out_path)
    for pic_dir in PIC_DIRS:
        _save_white_rgb(fig, pic_dir / "journal_vehicle_aware_posteval.png")
    plt.close(fig)


def write_report(summary: pd.DataFrame) -> None:
    selected_rows = summary[
        (summary["radius_m"] == 100.0)
        & (
            (
                (summary["evidence_block"] == "main_benchmark")
                & summary["scene_id"].isin(["gebco_cascadia_margin_moderate", "gebco_monterey_canyon_complex"])
            )
            | (
                (summary["evidence_block"] == "usgs_extension")
                & (summary["scene_id"] == "usgs_southern_cascadia_30m_high")
            )
            | (
                (summary["evidence_block"] == "segmented_diagnostic")
                & (summary["scene_id"] == "synthetic_complex")
                & summary["method"].isin(
                    ["Full Geometry-Aware Hybrid GA", "Transition-Aware Segmented Hybrid"]
                )
            )
        )
    ].copy()
    selected_rows = selected_rows.sort_values(["evidence_block", "scene_id", "method"])
    lines = [
        "# Vehicle-Aware Post-Evaluation\n\n",
        "This diagnostic converts planned line-family outputs into a first-order vehicle-execution proxy. ",
        "It adds semicircular line-change arcs for declared minimum turn radii and converts distance into time ",
        f"using {SURVEY_SPEED_MPS:.1f} m/s for survey/transit distance and {TURN_SPEED_MPS:.2f} m/s for turn arcs. ",
        "The diagnostic is not a Dubins controller, current model, SLAM replay, or deployment validation.\n\n",
        "## Selected R=100 m Results\n\n",
        "| Evidence block | Scene | Method | Runs | Feasible | Lines | Turn changes | Effective length (km) | Mission time (h) | Time gain vs Fixed (%) |\n",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|\n",
    ]
    for _, row in selected_rows.iterrows():
        lines.append(
            f"| {row['evidence_block']} | {row['scene_name']} | {row['method']} | "
            f"{int(row['n_runs'])} | {row['feasible_mean']:.2f} | {row['line_count_mean']:.1f} | "
            f"{row['line_change_count_mean']:.1f} | "
            f"{row['vehicle_length_km_mean']:.2f} | {row['mission_time_h_mean']:.2f} | "
            f"{row['mission_time_gain_vs_fixed_pct_mean']:.2f} |\n"
        )
    lines.extend(
        [
            "\n## Interpretation\n\n",
            "- GEBCO public-scene gains remain modest under the turn-radius proxy, which is consistent with the paper's bounded public-grid claim.\n",
            "- Monterey benefits slightly more after adding turn arcs because the terrain-aware layouts use fewer lines than Fixed-Spacing.\n",
            "- The USGS high-complexity crop retains a large mission-time proxy gain because terrain-aware planning removes the high-overlap fixed-spacing burden.\n",
            "- The transition-aware segmented synthetic-complex repair improves feasibility and is selected with the same first-order mission-time proxy used in this post-evaluation, but it should remain framed as a numerical repair direction until a full vehicle-dynamics route builder is added.\n",
        ]
    )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = [
        *_records_from_benchmark(MAIN_RESULTS, "main_benchmark"),
        *_records_from_benchmark(USGS_RESULTS, "usgs_extension"),
        *_records_from_segmented(SEGMENTED_RESULTS),
    ]
    rows = _vehicle_rows(records)
    raw = pd.DataFrame(rows)
    summary = _summary(rows)

    raw.to_csv(OUT / "vehicle_aware_raw.csv", index=False)
    summary.to_csv(OUT / "vehicle_aware_summary.csv", index=False)
    (OUT / "vehicle_aware_summary.json").write_text(
        json.dumps(
            {
                "radius_values_m": list(RADIUS_VALUES_M),
                "survey_speed_mps": SURVEY_SPEED_MPS,
                "turn_speed_mps": TURN_SPEED_MPS,
                "summary_rows": summary.to_dict(orient="records"),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    make_figure(summary)
    write_report(summary)
    print(f"Wrote {OUT / 'vehicle_aware_summary.csv'}")
    print(f"Wrote {OUT / 'vehicle_aware_posteval.png'}")


if __name__ == "__main__":
    main()
