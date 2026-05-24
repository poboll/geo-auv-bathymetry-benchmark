from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

import journal_heatmap_style as jhs


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "external_layout_baseline_audit" / "external_layout_baseline_raw.csv"
OUT = ROOT / "external_turning_cost_audit"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

RADIUS_VALUES_M = (25.0, 50.0, 100.0, 200.0)
SURVEY_SPEED_MPS = 1.5
TURN_SPEED_MPS = 0.75

METHOD_ORDER = (
    "Fixed-Spacing",
    "Min-Span Boustrophedon",
    "Contour-Parallel Fixed-Width",
    "Geometry-Shortest Fixed-Width",
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


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def as_float(row: dict[str, Any], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else float("nan")


def as_int(row: dict[str, Any], key: str) -> int:
    return int(round(as_float(row, key)))


def expand_turning_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        line_count = as_int(row, "line_count")
        line_change_count = max(line_count - 1, 0)
        path_km = as_float(row, "path_length_km")
        for radius_m in RADIUS_VALUES_M:
            turn_arc_km = line_change_count * math.pi * radius_m / 1000.0
            effective_length_km = path_km + turn_arc_km
            mission_time_h = (
                path_km * 1000.0 / SURVEY_SPEED_MPS
                + turn_arc_km * 1000.0 / TURN_SPEED_MPS
            ) / 3600.0
            rows.append(
                {
                    "scene_id": row["scene_id"],
                    "scene_label": row["scene_label"],
                    "terrain_class": row["terrain_class"],
                    "method": row["method"],
                    "method_label": row["method_label"],
                    "method_family": row["method_family"],
                    "radius_m": radius_m,
                    "line_count": line_count,
                    "line_change_count": line_change_count,
                    "geometric_length_km": path_km,
                    "turn_arc_km": turn_arc_km,
                    "effective_length_km": effective_length_km,
                    "turn_arc_share_pct": 100.0 * turn_arc_km / effective_length_km if effective_length_km > 0 else 0.0,
                    "mission_time_h": mission_time_h,
                    "path_gain_vs_fixed_pct": as_float(row, "path_gain_vs_fixed_pct"),
                    "coverage_pct": as_float(row, "coverage_pct"),
                    "excess_overlap_pct": as_float(row, "excess_overlap_pct"),
                    "feasible_C97_O3": as_int(row, "feasible_C97_O3"),
                }
            )

    fixed_lookup = {
        (row["scene_id"], row["radius_m"]): row
        for row in rows
        if row["method"] == "Fixed-Spacing"
    }
    for row in rows:
        fixed = fixed_lookup[(row["scene_id"], row["radius_m"])]
        row["effective_length_gain_vs_fixed_pct"] = (
            (fixed["effective_length_km"] - row["effective_length_km"])
            / fixed["effective_length_km"]
            * 100.0
        )
        row["mission_time_gain_vs_fixed_pct"] = (
            (fixed["mission_time_h"] - row["mission_time_h"])
            / fixed["mission_time_h"]
            * 100.0
        )
    return rows


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for method in METHOD_ORDER:
        method_rows = [row for row in rows if row["method"] == method]
        if not method_rows:
            continue
        base_rows = [row for row in method_rows if row["radius_m"] == RADIUS_VALUES_M[0]]
        record: dict[str, Any] = {
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "method_family": base_rows[0]["method_family"],
            "n_public_windows": len({row["scene_id"] for row in base_rows}),
            "feasible_windows_C97_O3": int(sum(int(row["feasible_C97_O3"]) for row in base_rows)),
        }
        for radius_m in RADIUS_VALUES_M:
            radius_rows = [row for row in method_rows if row["radius_m"] == radius_m]
            for key in (
                "effective_length_gain_vs_fixed_pct",
                "mission_time_gain_vs_fixed_pct",
                "turn_arc_share_pct",
                "turn_arc_km",
                "mission_time_h",
            ):
                values = np.asarray([float(row[key]) for row in radius_rows], dtype=float)
                prefix = f"R{int(radius_m)}_{key}"
                record[f"{prefix}_mean"] = float(np.mean(values))
                record[f"{prefix}_median"] = float(np.median(values))
                record[f"{prefix}_min"] = float(np.min(values))
                record[f"{prefix}_max"] = float(np.max(values))
            positives = [
                float(row["mission_time_gain_vs_fixed_pct"]) > 0.0
                for row in radius_rows
            ]
            record[f"R{int(radius_m)}_mission_time_positive_windows"] = int(sum(positives))
        summary.append(record)
    return summary


def make_figure(rows: list[dict[str, Any]]) -> None:
    jhs.apply_rc(base_font=8.35)
    scene_order = list(dict.fromkeys(row["scene_id"] for row in rows if row["radius_m"] == 100.0))
    method_order = [method for method in METHOD_ORDER if method != "Fixed-Spacing"]
    ylabels = [
        next(row["scene_label"] for row in rows if row["scene_id"] == scene_id).replace("GEBCO ", "G. ").replace("USGS ", "U. ")
        for scene_id in scene_order
    ]
    xlabels = [METHOD_LABELS[method] for method in method_order]

    specs = [
        (100.0, "mission_time_gain_vs_fixed_pct", "(a) Mission-time gain at R100 (%)", jhs.PATH_GAIN_CMAP, mcolors.TwoSlopeNorm(vmin=-12, vcenter=0, vmax=28), "{:+.1f}"),
        (200.0, "mission_time_gain_vs_fixed_pct", "(b) Mission-time gain at R200 (%)", jhs.PATH_GAIN_CMAP, mcolors.TwoSlopeNorm(vmin=-12, vcenter=0, vmax=28), "{:+.1f}"),
        (100.0, "turn_arc_share_pct", "(c) Turn-arc share at R100 (%)", jhs.TIME_CMAP, mcolors.Normalize(vmin=0, vmax=10), "{:.1f}"),
        (100.0, "feasible_C97_O3", "(d) Pass C97/O3", jhs.COVERAGE_CMAP, mcolors.Normalize(vmin=0, vmax=1), "{:.0f}"),
    ]
    fig, axes_grid = plt.subplots(2, 2, figsize=(7.65, 5.35), facecolor="white")
    axes = list(axes_grid.flat)
    for ax_idx, (ax, (radius_m, key, title, cmap, norm, fmt)) in enumerate(zip(axes, specs)):
        data = np.full((len(scene_order), len(method_order)), np.nan)
        for i, scene_id in enumerate(scene_order):
            for j, method in enumerate(method_order):
                match = [
                    row for row in rows
                    if row["scene_id"] == scene_id and row["method"] == method and row["radius_m"] == radius_m
                ]
                if match:
                    data[i, j] = float(match[0][key])
        ax.imshow(data, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        jhs.style_heatmap_axis(
            ax,
            title,
            xlabels,
            ylabels if ax_idx in (0, 2) else None,
            data.shape[0],
            rotate_x=0,
        )
        jhs.annotate_cells(ax, data, cmap, norm, fmt, fontsize=6.30)
        for y in np.arange(0.5, data.shape[0], 1.0):
            ax.axhline(y, color="white", linewidth=0.64)
        for x in np.arange(0.5, data.shape[1], 1.0):
            ax.axvline(x, color="white", linewidth=0.64)
    fig.text(
        0.012,
        0.013,
        "Mission-time proxy: geometric path at 1.5 m/s plus semicircular line-change arcs at 0.75 m/s; no controller or sea-trial claim.",
        ha="left",
        va="bottom",
        fontsize=6.15,
        color=jhs.MUTED,
    )
    fig.subplots_adjust(left=0.096, right=0.997, top=0.940, bottom=0.070, wspace=0.064, hspace=0.188)
    out_path = OUT / "journal_external_turning_cost_audit.png"
    jhs.save_white_rgb(fig, out_path, dpi=430, pad_inches=0.025)
    for pic_dir in PIC_DIRS:
        jhs.save_white_rgb(fig, pic_dir / "journal_external_turning_cost_audit.png", dpi=430, pad_inches=0.025)
    plt.close(fig)


def write_readme(summary_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# External Heuristic Turning-cost Audit\n\n",
        "This diagnostic extends the v28 external survey-layout audit with a simple execution-cost proxy. ",
        "For each fixed-line layout, it adds a semicircular line-change penalty \\((N-1)\\pi R_{min}\\) and converts the geometric path plus turn arcs into mission time using declared speeds.\n\n",
        "## Assumptions\n\n",
        f"- Minimum-turn-radius values: {', '.join(str(int(r)) for r in RADIUS_VALUES_M)} m.\n",
        f"- Survey/transit speed: {SURVEY_SPEED_MPS:.2f} m/s.\n",
        f"- Turn-arc speed: {TURN_SPEED_MPS:.2f} m/s.\n",
        "- Coverage and overlap feasibility are not recomputed because the line family is unchanged; this is a post-planning execution-cost audit only.\n",
        "- The proxy is not a Dubins controller, hydrodynamic model, mission-log replay, field validation, or hydrographic QA.\n\n",
        "## Summary at R100 and R200\n\n",
        "| Method | Feasible windows | Median mission-time gain R100 (%) | Positive windows R100 | Median mission-time gain R200 (%) | Positive windows R200 | Median turn-arc share R100 (%) |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for row in summary_rows:
        if row["method"] == "Fixed-Spacing":
            continue
        lines.append(
            f"| {row['method_label']} | {row['feasible_windows_C97_O3']}/{row['n_public_windows']} | "
            f"{row['R100_mission_time_gain_vs_fixed_pct_median']:.3f} | {row['R100_mission_time_positive_windows']}/{row['n_public_windows']} | "
            f"{row['R200_mission_time_gain_vs_fixed_pct_median']:.3f} | {row['R200_mission_time_positive_windows']}/{row['n_public_windows']} | "
            f"{row['R100_turn_arc_share_pct_median']:.3f} |\n"
        )
    (OUT / "README.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_rows = read_rows(SOURCE)
    rows = expand_turning_rows(source_rows)
    summary_rows = summarize(rows)
    write_csv(OUT / "external_turning_cost_raw.csv", rows)
    write_csv(OUT / "external_turning_cost_summary.csv", summary_rows)
    dump_json(
        OUT / "external_turning_cost_summary.json",
        {
            "scope": "Post-planning minimum-turn-radius and mission-time proxy audit for the v28 external-layout baseline rows.",
            "source": str(SOURCE.relative_to(ROOT)),
            "radius_values_m": list(RADIUS_VALUES_M),
            "survey_speed_mps": SURVEY_SPEED_MPS,
            "turn_speed_mps": TURN_SPEED_MPS,
            "interpretation_boundary": (
                "Deterministic execution-cost proxy only; not a Dubins controller, hydrodynamic simulation, "
                "mission-log replay, field validation, raw MBES product validation, or hydrographic QA."
            ),
            "summary_rows": summary_rows,
            "raw_rows": rows,
        },
    )
    make_figure(rows)
    write_readme(summary_rows)
    print(f"Wrote {OUT} with raw_rows={len(rows)} summary_rows={len(summary_rows)}")


if __name__ == "__main__":
    main()
