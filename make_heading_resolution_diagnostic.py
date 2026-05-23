from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

import geo_public_bathy_benchmark as geo
import journal_heatmap_style as jhs
import make_threshold_local_failure_extension as threshold


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "heading_resolution_diagnostic"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

HEADING_SETS = {
    "15deg": tuple(range(0, 180, 15)),
    "5deg": tuple(range(0, 180, 5)),
}
METHODS = ("Simple Greedy", "Adaptive Spacing w/o GA")
SCENE_LABELS = {
    "gebco_cascadia_margin_moderate": "GEBCO Cascadia",
    "gebco_monterey_canyon_complex": "GEBCO Monterey",
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


def _best_simple_greedy(scene: geo.TerrainScene, headings: tuple[int, ...]) -> geo.PlanResult:
    start = time.perf_counter()
    best = geo.LayoutCandidate(0.0, np.asarray([], dtype=float), 0.0, 0.0, float("inf"))
    for angle in headings:
        candidate = geo.best_constant_spacing_layout(scene, float(angle))
        if candidate.score < best.score:
            best = candidate
    return geo.evaluate_plan(
        scene,
        "Simple Greedy",
        0,
        best.orientation_deg,
        best.line_positions,
        time.perf_counter() - start,
    )


def _best_adaptive(scene: geo.TerrainScene, headings: tuple[int, ...]) -> geo.PlanResult:
    start = time.perf_counter()
    best = geo.best_adaptive_layout(scene, orientation_candidates=headings)
    return geo.evaluate_plan(
        scene,
        "Adaptive Spacing w/o GA",
        0,
        best.orientation_deg,
        best.line_positions,
        time.perf_counter() - start,
    )


def _score(result: geo.PlanResult) -> float:
    return geo.plan_score(result.path_length_km, result.coverage_pct, result.excess_overlap_pct)


def _row(scene: geo.TerrainScene, heading_label: str, heading_step_deg: int, result: geo.PlanResult) -> dict[str, Any]:
    return {
        "scene_id": scene.scene_id,
        "scene_label": SCENE_LABELS.get(scene.scene_id, scene.display_name),
        "terrain_class": scene.terrain_class,
        "heading_set": heading_label,
        "heading_step_deg": int(heading_step_deg),
        "method": result.method,
        "orientation_deg": float(result.orientation_deg),
        "line_count": int(result.line_count),
        "path_length_km": float(result.path_length_km),
        "coverage_pct": float(result.coverage_pct),
        "excess_overlap_pct": float(result.excess_overlap_pct),
        "score": float(_score(result)),
        "feasible_97_3": int(result.feasible),
        "planning_time_s": float(result.planning_time_s),
    }


def _heading_shift_deg(a: float, b: float) -> float:
    delta = abs(float(a) - float(b)) % 180.0
    return float(min(delta, 180.0 - delta))


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {(row["scene_id"], row["method"], row["heading_set"]): row for row in rows}
    summary: list[dict[str, Any]] = []
    for scene_id in sorted({str(row["scene_id"]) for row in rows}):
        for method in METHODS:
            r15 = lookup[(scene_id, method, "15deg")]
            r5 = lookup[(scene_id, method, "5deg")]
            path_delta_pct = 100.0 * (float(r5["path_length_km"]) - float(r15["path_length_km"])) / max(
                float(r15["path_length_km"]), 1e-9
            )
            coverage_delta_pp = float(r5["coverage_pct"]) - float(r15["coverage_pct"])
            overlap_delta_pp = float(r5["excess_overlap_pct"]) - float(r15["excess_overlap_pct"])
            score_delta = float(r5["score"]) - float(r15["score"])
            summary.append(
                {
                    "scene_id": scene_id,
                    "scene_label": r15["scene_label"],
                    "method": method,
                    "orientation_15deg": float(r15["orientation_deg"]),
                    "orientation_5deg": float(r5["orientation_deg"]),
                    "heading_shift_deg": _heading_shift_deg(r15["orientation_deg"], r5["orientation_deg"]),
                    "line_count_15deg": int(r15["line_count"]),
                    "line_count_5deg": int(r5["line_count"]),
                    "line_count_delta": int(r5["line_count"]) - int(r15["line_count"]),
                    "path_15deg_km": float(r15["path_length_km"]),
                    "path_5deg_km": float(r5["path_length_km"]),
                    "path_delta_5minus15_pct": float(path_delta_pct),
                    "coverage_15deg_pct": float(r15["coverage_pct"]),
                    "coverage_5deg_pct": float(r5["coverage_pct"]),
                    "coverage_delta_5minus15_pp": float(coverage_delta_pp),
                    "overlap_15deg_pct": float(r15["excess_overlap_pct"]),
                    "overlap_5deg_pct": float(r5["excess_overlap_pct"]),
                    "overlap_delta_5minus15_pp": float(overlap_delta_pp),
                    "score_delta_5minus15": float(score_delta),
                    "feasible_15deg": int(r15["feasible_97_3"]),
                    "feasible_5deg": int(r5["feasible_97_3"]),
                    "quantization_material": int(
                        abs(path_delta_pct) > 0.25
                        or abs(coverage_delta_pp) > 0.25
                        or abs(overlap_delta_pp) > 0.25
                        or int(r15["feasible_97_3"]) != int(r5["feasible_97_3"])
                    ),
                }
            )
    return summary


def _make_figure(summary_rows: list[dict[str, Any]]) -> None:
    jhs.apply_rc(base_font=8.4)
    row_labels = [f"{row['scene_label']}\n{row['method'].replace(' w/o GA', '')}" for row in summary_rows]
    metrics = [
        ("heading_shift_deg", "Heading shift (deg)", mcolors.Normalize(vmin=0.0, vmax=15.0), jhs.TIME_CMAP, "{:.0f}"),
        (
            "path_delta_5minus15_pct",
            r"$\Delta L_{5-15}$ (%)",
            mcolors.TwoSlopeNorm(vmin=-2.0, vcenter=0.0, vmax=2.0),
            jhs.COVERAGE_CMAP,
            "{:+.2f}",
        ),
        (
            "coverage_delta_5minus15_pp",
            r"$\Delta C_{5-15}$ (pp)",
            mcolors.TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0),
            jhs.COVERAGE_CMAP,
            "{:+.2f}",
        ),
        (
            "overlap_delta_5minus15_pp",
            r"$\Delta O_{5-15}$ (pp)",
            mcolors.TwoSlopeNorm(vmin=-2.0, vcenter=0.0, vmax=2.0),
            jhs.COVERAGE_CMAP.reversed(),
            "{:+.2f}",
        ),
    ]
    fig = plt.figure(figsize=(7.45, 3.25), facecolor="white")
    grid = fig.add_gridspec(
        1,
        len(metrics) + 1,
        width_ratios=[1.34, 0.92, 0.92, 0.92, 0.92],
        left=0.035,
        right=0.985,
        top=0.84,
        bottom=0.17,
        wspace=0.16,
    )
    label_ax = fig.add_subplot(grid[0, 0])
    label_ax.set_xlim(0, 1)
    label_ax.set_ylim(len(row_labels) - 0.5, -0.5)
    label_ax.axis("off")
    for i, label in enumerate(row_labels):
        scene, method = label.split("\n", 1)
        label_ax.text(0.98, i - 0.10, scene, ha="right", va="center", fontsize=6.9, color=jhs.TEXT)
        label_ax.text(0.98, i + 0.18, method, ha="right", va="center", fontsize=6.2, color=jhs.MUTED)

    axes = [fig.add_subplot(grid[0, i + 1]) for i in range(len(metrics))]
    for ax, (key, title, norm, cmap, fmt) in zip(axes, metrics):
        data = np.asarray([[float(row[key])] for row in summary_rows], dtype=float)
        ax.imshow(data, cmap=cmap, norm=norm, aspect="auto")
        jhs.style_heatmap_axis(ax, title, [""], None, len(row_labels))
        ax.set_xticklabels([])
        jhs.annotate_cells(ax, data, cmap, norm, fmt, fontsize=6.4)
        for y in np.arange(0.5, len(row_labels), 1.0):
            ax.axhline(y, color="white", linewidth=0.7)
    fig.text(
        0.012,
        0.012,
        "5-degree diagnostic recomputes Simple Greedy and Adaptive Spacing only; negative path delta means the finer scan is shorter.",
        ha="left",
        va="bottom",
        fontsize=6.1,
        color=jhs.MUTED,
    )
    out_path = OUT / "journal_heading_resolution_diagnostic.png"
    jhs.save_white_rgb(fig, out_path, dpi=430, pad_inches=0.025)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
        jhs.save_white_rgb(fig, pic_dir / "journal_heading_resolution_diagnostic.png", dpi=430, pad_inches=0.025)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit whether the 15-degree heading scan hides material line-layout gains."
    )
    parser.add_argument(
        "--scenes",
        choices=("public", "all"),
        default="all",
        help="Use only the two GEBCO public scenes or include the USGS high-complexity crop.",
    )
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    scenes = threshold.load_scenes()
    if args.scenes == "public":
        scenes = scenes[:2]

    rows: list[dict[str, Any]] = []
    for scene in scenes:
        for heading_label, headings in HEADING_SETS.items():
            heading_step = int(headings[1] - headings[0])
            rows.append(_row(scene, heading_label, heading_step, _best_simple_greedy(scene, headings)))
            rows.append(_row(scene, heading_label, heading_step, _best_adaptive(scene, headings)))

    summary_rows = _summarize(rows)
    _write_csv(OUT / "heading_resolution_raw.csv", rows)
    _write_csv(OUT / "heading_resolution_summary.csv", summary_rows)
    _safe_json_dump(
        OUT / "heading_resolution_summary.json",
        {
            "scope": (
                "Supplemental heading-resolution diagnostic. It compares the deterministic Simple Greedy "
                "and Adaptive Spacing bases under the manuscript 15-degree scan and a finer 5-degree scan. "
                "Hybrid GA is not rerun here because it inherits the deterministic adaptive heading and line-count base."
            ),
            "heading_sets": {key: list(value) for key, value in HEADING_SETS.items()},
            "rows": rows,
            "summary_rows": summary_rows,
        },
    )
    _make_figure(summary_rows)
    print(f"Wrote heading-resolution diagnostic with {len(rows)} raw rows and {len(summary_rows)} comparisons.")


if __name__ == "__main__":
    main()
