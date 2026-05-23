from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import geo_public_bathy_benchmark as geo


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "gebco_scene_expansion"
PIC_DIRS = [
    ROOT / "manuscript" / "latex" / "pic",
    ROOT / "manuscript" / "mdpi_jmse" / "pic",
]
PIC = PIC_DIRS[0]
DEFAULT_SEEDS = tuple(range(20))

EXTRA_GEBCO_SPECS: tuple[geo.PublicSceneSpec, ...] = (
    geo.PublicSceneSpec(
        scene_id="gebco_mariana_trench_complex",
        display_name="GEBCO Mariana Trench",
        provider="gebco",
        terrain_class="complex_relief",
        download_url="https://download.gebco.net",
        bbox=(141.0, 143.0, 11.0, 13.0),
        source="GEBCO 2025 global bathymetry subset",
        license="GEBCO 2025 Grid terms of use",
    ),
    geo.PublicSceneSpec(
        scene_id="gebco_puerto_rico_trench_complex",
        display_name="GEBCO Puerto Rico Trench",
        provider="gebco",
        terrain_class="complex_relief",
        download_url="https://download.gebco.net",
        bbox=(-67.5, -65.5, 18.5, 20.5),
        source="GEBCO 2025 global bathymetry subset",
        license="GEBCO 2025 Grid terms of use",
    ),
    geo.PublicSceneSpec(
        scene_id="gebco_mid_atlantic_ridge_moderate",
        display_name="GEBCO Mid-Atlantic Ridge",
        provider="gebco",
        terrain_class="ridge_relief",
        download_url="https://download.gebco.net",
        bbox=(-31.0, -29.0, 35.0, 37.0),
        source="GEBCO 2025 global bathymetry subset",
        license="GEBCO 2025 Grid terms of use",
    ),
    geo.PublicSceneSpec(
        scene_id="gebco_hawaii_ridge_moderate",
        display_name="GEBCO Hawaii Ridge",
        provider="gebco",
        terrain_class="ridge_relief",
        download_url="https://download.gebco.net",
        bbox=(-162.0, -160.0, 22.0, 24.0),
        source="GEBCO 2025 global bathymetry subset",
        license="GEBCO 2025 Grid terms of use",
    ),
)

METHODS = (
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
)
METHOD_LABELS = {
    "Fixed-Spacing": "Fixed",
    "Adaptive Spacing w/o GA": "Adaptive",
    "Full Geometry-Aware Hybrid GA": "Hybrid GA",
}


def result_row(result: geo.PlanResult, fixed_path: float | None) -> dict[str, float | int | str]:
    path_gain = 0.0 if fixed_path in (None, 0.0) else (fixed_path - result.path_length_km) / fixed_path * 100.0
    return {
        "scene_id": result.scene_id,
        "scene_name": result.scene_name,
        "terrain_class": result.terrain_class,
        "method": result.method,
        "seed": int(result.seed),
        "orientation_deg": float(result.orientation_deg),
        "line_count": int(result.line_count),
        "path_length_km": float(result.path_length_km),
        "path_gain_vs_fixed_pct": float(path_gain),
        "coverage_pct": float(result.coverage_pct),
        "excess_overlap_pct": float(result.excess_overlap_pct),
        "planning_time_s": float(result.planning_time_s),
        "feasible": int(result.feasible),
    }


def summarize(rows: list[dict[str, float | int | str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, float | int | str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["scene_id"]), str(row["method"]))].append(row)

    out: list[dict[str, Any]] = []
    for (scene_id, method), group_rows in sorted(grouped.items()):
        record: dict[str, Any] = {
            "scene_id": scene_id,
            "scene_name": str(group_rows[0]["scene_name"]),
            "terrain_class": str(group_rows[0]["terrain_class"]),
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "n_runs": len(group_rows),
        }
        for key in (
            "orientation_deg",
            "line_count",
            "path_length_km",
            "path_gain_vs_fixed_pct",
            "coverage_pct",
            "excess_overlap_pct",
            "planning_time_s",
            "feasible",
        ):
            values = np.asarray([float(row[key]) for row in group_rows], dtype=float)
            record[f"{key}_mean"] = float(values.mean())
            record[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            record[f"{key}_min"] = float(values.min())
            record[f"{key}_max"] = float(values.max())
        out.append(record)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_figure(summary_rows: list[dict[str, Any]], seeds: tuple[int, ...]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 7.0,
            "axes.titlesize": 7.2,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 6.0,
            "ytick.labelsize": 6.0,
            "axes.linewidth": 0.5,
            "savefig.dpi": 420,
        }
    )
    scene_order = [spec.scene_id for spec in EXTRA_GEBCO_SPECS]
    scene_labels = {
        spec.scene_id: spec.display_name.replace("GEBCO ", "").replace(" Trench", "\nTrench").replace(" Ridge", "\nRidge")
        for spec in EXTRA_GEBCO_SPECS
    }
    metrics = [
        ("path_gain_vs_fixed_pct_mean", "Path gain vs fixed (%)", "#dfeee8", "#0f766e", 0.0, None),
        ("coverage_pct_mean", "Predicted coverage (%)", "#edf5fb", "#1d5f8a", 97.0, 100.0),
        ("excess_overlap_pct_mean", "Excess overlap (%)", "#f7ece5", "#b5522b", 0.0, None),
        ("feasible_mean", "Feasible seed rate", "#f1eef7", "#5a4a91", 0.0, 1.0),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.35, 5.1), facecolor="white")
    axes_flat = axes.ravel()
    for ax, (key, title, low_color, high_color, vmin, vmax) in zip(axes_flat, metrics):
        matrix = np.full((len(scene_order), len(METHODS)), np.nan)
        for i, scene_id in enumerate(scene_order):
            for j, method in enumerate(METHODS):
                matches = [row for row in summary_rows if row["scene_id"] == scene_id and row["method"] == method]
                if matches:
                    matrix[i, j] = float(matches[0][key])
        if vmax is None:
            vmax = float(np.nanmax(matrix)) if np.isfinite(matrix).any() else 1.0
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list(title, [low_color, high_color])
        im = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect="equal")
        ax.set_title(title, fontweight="bold", color="#202a33")
        ax.set_xticks(range(len(METHODS)))
        ax.set_xticklabels([METHOD_LABELS[m] for m in METHODS], rotation=25, ha="right")
        ax.set_yticks(range(len(scene_order)))
        ax.set_yticklabels([scene_labels[s] for s in scene_order])
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_color("#b8c4cf")
            spine.set_linewidth(0.5)
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = matrix[i, j]
                if np.isfinite(value):
                    text = f"{value:.2f}" if key != "feasible_mean" else f"{value:.1f}"
                    ax.text(j, i, text, ha="center", va="center", fontsize=6.0, color="#16212b")
        cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
        cbar.ax.tick_params(labelsize=5.6, width=0.4, length=2)
    fig.text(
        0.5,
        0.035,
        f"Supplemental GEBCO four-window expansion; Hybrid GA reports seeds {seeds[0]}-{seeds[-1]} and is not merged into the main benchmark.",
        ha="center",
        va="bottom",
        fontsize=6.2,
        color="#4c5965",
    )
    fig.subplots_adjust(top=0.92, bottom=0.16, left=0.16, right=0.985, hspace=0.34, wspace=0.24)
    fig.savefig(PIC / "journal_gebco_scene_expansion.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / "gebco_scene_expansion.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the supplemental GEBCO four-window scene expansion.")
    parser.add_argument(
        "--seed-count",
        type=int,
        default=len(DEFAULT_SEEDS),
        help="Number of Hybrid GA seeds to run, starting at zero.",
    )
    args = parser.parse_args()
    if args.seed_count < 1:
        raise ValueError("--seed-count must be at least 1")
    seeds = tuple(range(args.seed_count))

    OUT.mkdir(exist_ok=True)
    for pic_dir in PIC_DIRS:
        pic_dir.mkdir(parents=True, exist_ok=True)
    raw_rows: list[dict[str, float | int | str]] = []
    scenes = [geo.load_public_scene(spec, ROOT) for spec in EXTRA_GEBCO_SPECS]
    for scene in scenes:
        fixed = geo.fixed_spacing_plan(scene)
        adaptive, adaptive_base = geo.adaptive_spacing_plan(scene)
        fixed_path = fixed.path_length_km
        raw_rows.append(result_row(fixed, fixed_path))
        raw_rows.append(result_row(adaptive, fixed_path))
        for seed in seeds:
            hybrid = geo.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed)
            raw_rows.append(result_row(hybrid, fixed_path))

    summary_rows = summarize(raw_rows)
    manifest = [scene.manifest_entry for scene in scenes]
    write_csv(OUT / "gebco_scene_expansion_raw.csv", raw_rows)
    write_csv(OUT / "gebco_scene_expansion_summary.csv", summary_rows)
    with (OUT / "gebco_scene_expansion_summary.json").open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "scope": "Supplemental four-window GEBCO public-scene expansion; not merged into run_5 main benchmark.",
                "hybrid_ga_seeds": list(seeds),
                "scene_manifest": manifest,
                "raw_rows": raw_rows,
                "summary_rows": summary_rows,
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    with (OUT / "public_scene_manifest.json").open("w", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2, ensure_ascii=False)
    make_figure(summary_rows, seeds)
    for pic_dir in PIC_DIRS[1:]:
        shutil.copy2(PIC / "journal_gebco_scene_expansion.png", pic_dir / "journal_gebco_scene_expansion.png")
    print(f"Wrote {OUT / 'gebco_scene_expansion_summary.csv'}")
    print(f"Wrote {PIC / 'journal_gebco_scene_expansion.png'}")


if __name__ == "__main__":
    main()
