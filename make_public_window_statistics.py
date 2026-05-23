from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import wilcoxon

import journal_heatmap_style as jhs


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public_window_statistics"
PIC_DIRS = (
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
)

SOURCE_FILES = (
    ("main_gebco_pair", ROOT / "run_5" / "benchmark_method_statistics.csv", {"gebco_cascadia_margin_moderate", "gebco_monterey_canyon_complex"}),
    ("supplemental_gebco_four", ROOT / "gebco_scene_expansion" / "gebco_scene_expansion_summary.csv", None),
    ("usgs_three_crops", ROOT / "survey_grade_extension_usgs_cascadia" / "benchmark_method_statistics.csv", None),
)
METHODS = ("Adaptive Spacing w/o GA", "Full Geometry-Aware Hybrid GA")
METHOD_LABELS = {
    "Adaptive Spacing w/o GA": "Adaptive",
    "Full Geometry-Aware Hybrid GA": "Hybrid",
}
FIXED = "Fixed-Spacing"


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


def _load_source(source_label: str, path: Path, scene_filter: set[str] | None) -> list[dict[str, Any]]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        scene_id = row["scene_id"]
        if scene_filter is not None and scene_id not in scene_filter:
            continue
        grouped.setdefault(scene_id, {})[row["method"]] = row

    out: list[dict[str, Any]] = []
    for scene_id, method_rows in sorted(grouped.items()):
        if FIXED not in method_rows:
            continue
        fixed = method_rows[FIXED]
        fixed_path = float(fixed["path_length_km_mean"])
        fixed_coverage = float(fixed["coverage_pct_mean"])
        fixed_overlap = float(fixed["excess_overlap_pct_mean"])
        for method in METHODS:
            if method not in method_rows:
                continue
            current = method_rows[method]
            path = float(current["path_length_km_mean"])
            coverage = float(current["coverage_pct_mean"])
            overlap = float(current["excess_overlap_pct_mean"])
            out.append(
                {
                    "source_group": source_label,
                    "scene_id": scene_id,
                    "scene_name": current.get("scene_name", scene_id),
                    "terrain_class": current.get("terrain_class", ""),
                    "method": method,
                    "method_label": METHOD_LABELS[method],
                    "fixed_path_km": fixed_path,
                    "method_path_km": path,
                    "path_gain_vs_fixed_pct": 100.0 * (fixed_path - path) / max(fixed_path, 1e-9),
                    "fixed_coverage_pct": fixed_coverage,
                    "method_coverage_pct": coverage,
                    "coverage_delta_pp": coverage - fixed_coverage,
                    "fixed_excess_overlap_pct": fixed_overlap,
                    "method_excess_overlap_pct": overlap,
                    "overlap_cleanup_pp": fixed_overlap - overlap,
                    "fixed_feasible": int(round(float(fixed["feasible_mean"]))),
                    "method_feasible": int(round(float(current["feasible_mean"]))),
                }
            )
    return out


def _bootstrap_ci(values: np.ndarray, *, seed: int = 20260522, n_boot: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))


def _rank_biserial(values: np.ndarray) -> float:
    nonzero = values[np.abs(values) > 1e-12]
    if nonzero.size == 0:
        return 0.0
    ranks = np.argsort(np.argsort(np.abs(nonzero))) + 1
    # Average ties explicitly for the few rounded-equal diagnostic values.
    abs_values = np.abs(nonzero)
    ranks = np.zeros_like(abs_values, dtype=float)
    for value in sorted(set(abs_values)):
        idx = np.flatnonzero(abs_values == value)
        ranks[idx] = 0.5 * (idx.size + 1) + np.sum(abs_values < value)
    w_plus = float(np.sum(ranks[nonzero > 0]))
    w_minus = float(np.sum(ranks[nonzero < 0]))
    denom = float(nonzero.size * (nonzero.size + 1) / 2.0)
    return (w_plus - w_minus) / denom if denom else 0.0


def _wilcoxon_p(values: np.ndarray) -> float:
    nonzero = values[np.abs(values) > 1e-12]
    if nonzero.size == 0:
        return 1.0
    try:
        return float(wilcoxon(nonzero, alternative="greater", zero_method="wilcox").pvalue)
    except ValueError:
        return 1.0


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    metrics = (
        ("path_gain_vs_fixed_pct", "greater"),
        ("overlap_cleanup_pp", "greater"),
        ("coverage_delta_pp", "greater"),
    )
    for method in METHODS:
        group = [row for row in rows if row["method"] == method]
        record: dict[str, Any] = {
            "method": method,
            "method_label": METHOD_LABELS[method],
            "n_public_windows": len(group),
            "feasible_windows": int(sum(row["method_feasible"] for row in group)),
            "source_groups": ";".join(sorted({row["source_group"] for row in group})),
        }
        for metric, _ in metrics:
            values = np.asarray([float(row[metric]) for row in group], dtype=float)
            low, high = _bootstrap_ci(values)
            record[f"{metric}_mean"] = float(np.mean(values))
            record[f"{metric}_median"] = float(np.median(values))
            record[f"{metric}_q25"] = float(np.percentile(values, 25))
            record[f"{metric}_q75"] = float(np.percentile(values, 75))
            record[f"{metric}_bootstrap_mean_ci95_low"] = low
            record[f"{metric}_bootstrap_mean_ci95_high"] = high
            record[f"{metric}_positive_windows"] = int(np.sum(values > 1e-12))
            record[f"{metric}_wilcoxon_greater_p"] = _wilcoxon_p(values)
            record[f"{metric}_rank_biserial"] = _rank_biserial(values)
        summary.append(record)
    return summary


def _make_figure(rows: list[dict[str, Any]]) -> None:
    jhs.apply_rc(base_font=8.6)
    scenes = list(dict.fromkeys(row["scene_id"] for row in rows))
    short_labels = {
        "gebco_cascadia_margin_moderate": "GEBCO\nCascadia",
        "gebco_monterey_canyon_complex": "GEBCO\nMonterey",
        "gebco_mariana_trench_complex": "GEBCO\nMariana",
        "gebco_puerto_rico_trench_complex": "GEBCO\nPuerto Rico",
        "gebco_mid_atlantic_ridge_moderate": "GEBCO\nMid-Atl.",
        "gebco_hawaii_ridge_moderate": "GEBCO\nHawaii",
        "usgs_southern_cascadia_30m_low": "USGS\nLow",
        "usgs_southern_cascadia_30m_medium": "USGS\nMedium",
        "usgs_southern_cascadia_30m_high": "USGS\nHigh",
    }
    metrics = [
        ("path_gain_vs_fixed_pct", "Path gain vs fixed (%)", jhs.PATH_GAIN_CMAP, mcolors.Normalize(vmin=-1.0, vmax=26.0), "{:.1f}"),
        ("overlap_cleanup_pp", "Overlap cleanup (pp)", jhs.PATH_GAIN_CMAP, mcolors.Normalize(vmin=-0.5, vmax=29.0), "{:.1f}"),
        ("coverage_delta_pp", "Coverage delta (pp)", jhs.COVERAGE_CMAP, mcolors.TwoSlopeNorm(vmin=-1.5, vcenter=0.0, vmax=1.5), "{:+.1f}"),
    ]
    fig = plt.figure(figsize=(7.55, 3.15), facecolor="white")
    grid = fig.add_gridspec(
        1,
        4,
        width_ratios=[1.18, 1.0, 1.0, 1.0],
        left=0.035,
        right=0.985,
        top=0.82,
        bottom=0.18,
        wspace=0.18,
    )
    label_ax = fig.add_subplot(grid[0, 0])
    label_ax.set_xlim(0, 1)
    label_ax.set_ylim(len(scenes) - 0.5, -0.5)
    label_ax.axis("off")
    for i, scene in enumerate(scenes):
        label_ax.text(
            0.98,
            i,
            short_labels.get(scene, scene).replace("\n", " "),
            ha="right",
            va="center",
            fontsize=6.35,
            color=jhs.TEXT,
        )
    axes = [fig.add_subplot(grid[0, i + 1]) for i in range(3)]
    for ax, (metric, title, cmap, norm, fmt) in zip(axes, metrics):
        matrix = np.full((len(scenes), len(METHODS)), np.nan)
        for i, scene_id in enumerate(scenes):
            for j, method in enumerate(METHODS):
                match = [row for row in rows if row["scene_id"] == scene_id and row["method"] == method]
                if match:
                    matrix[i, j] = float(match[0][metric])
        ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")
        jhs.style_heatmap_axis(
            ax,
            title,
            [METHOD_LABELS[method] for method in METHODS],
            None,
            len(scenes),
            rotate_x=0.0,
        )
        jhs.annotate_cells(ax, matrix, cmap, norm, fmt, fontsize=5.85)
        for y in np.arange(0.5, len(scenes), 1.0):
            ax.axhline(y, color="white", linewidth=0.65)
        ax.axvline(0.5, color="white", linewidth=0.65)
    fig.text(
        0.012,
        0.012,
        "Nine public windows combine the two GEBCO main scenes, four supplemental GEBCO windows, and three USGS 30 m crops.",
        ha="left",
        va="bottom",
        fontsize=6.1,
        color=jhs.MUTED,
    )
    out = OUT / "journal_public_window_statistics.png"
    jhs.save_white_rgb(fig, out, dpi=430, pad_inches=0.025)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
        jhs.save_white_rgb(fig, pic_dir / "journal_public_window_statistics.png", dpi=430, pad_inches=0.025)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows: list[dict[str, Any]] = []
    for label, path, scene_filter in SOURCE_FILES:
        rows.extend(_load_source(label, path, scene_filter))
    summary = _summarize(rows)
    _write_csv(OUT / "public_window_paired_deltas.csv", rows)
    _write_csv(OUT / "public_window_statistics_summary.csv", summary)
    _safe_json_dump(
        OUT / "public_window_statistics_summary.json",
        {
            "scope": (
                "Paired public-window statistics computed from existing benchmark CSV files. "
                "The audit combines the two main GEBCO scenes, four supplemental GEBCO windows, "
                "and three USGS 30 m public-grid crops. It does not merge these windows into the main run_5 averages."
            ),
            "source_files": [str(path.relative_to(ROOT)) for _, path, _ in SOURCE_FILES],
            "paired_rows": rows,
            "summary_rows": summary,
        },
    )
    _make_figure(rows)
    print(f"Wrote public-window statistics for {len(rows) // len(METHODS)} windows and {len(summary)} methods.")


if __name__ == "__main__":
    main()
