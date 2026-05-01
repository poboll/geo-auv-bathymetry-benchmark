from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

import geo_public_bathy_benchmark as bench


ROOT = Path(__file__).resolve().parent
RUN = ROOT / "run_5"
OUT_CSV = RUN / "complex_terrain_failure_mode_summary.csv"
OUT_FIGS = [
    ROOT / "latex" / "pic" / "journal_failure_mode_complex.png",
    ROOT / "mdpi_jmse" / "pic" / "journal_failure_mode_complex.png",
]

METHODS = [
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
]

METHOD_LABELS = {
    "Fixed-Spacing": "Fixed spacing",
    "Adaptive Spacing w/o GA": "Adaptive only",
    "Full Geometry-Aware Hybrid GA": "Hybrid GA",
}

METHOD_COLORS = {
    "Fixed-Spacing": "#7b7f8a",
    "Adaptive Spacing w/o GA": "#2a9d8f",
    "Full Geometry-Aware Hybrid GA": "#c26a3d",
}

GAP_CMAP = LinearSegmentedColormap.from_list("gap_red", ["#ffffff", "#b2182b"])
OVERLAP_CMAP = LinearSegmentedColormap.from_list(
    "overlap_gold",
    ["#101820", "#2b4162", "#7b3f98", "#d95f5f", "#f7b267", "#fff3b0"],
)


def representative_complex_plans() -> tuple[bench.TerrainScene, list[bench.PlanResult]]:
    scenes = {scene.scene_id: scene for scene in bench.terrain_generators()}
    scene = scenes["synthetic_complex"]

    fixed = bench.fixed_spacing_plan(scene)
    _greedy, _greedy_base = bench.simple_greedy_plan(scene)
    adaptive, adaptive_base = bench.adaptive_spacing_plan(scene)
    hybrid = bench.full_geometry_aware_hybrid_ga_plan(scene, adaptive_base, seed=0)
    return scene, [fixed, adaptive, hybrid]


def write_summary(rows: list[dict[str, object]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _plot_lines(ax: plt.Axes, scene: bench.TerrainScene, plan: bench.PlanResult) -> None:
    context = bench.make_context(scene, plan.orientation_deg)
    for v in plan.line_positions:
        xs, ys = bench.line_segment_points(v, context.phi_rad, scene.width_m, scene.height_m)
        if len(xs) == 2:
            ax.plot(
                xs / bench.NM_TO_M,
                ys / bench.NM_TO_M,
                color=METHOD_COLORS[plan.method],
                linewidth=0.55,
                alpha=0.88,
                solid_capstyle="round",
                zorder=3,
            )


def make_figure(scene: bench.TerrainScene, plans: list[bench.PlanResult]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Palatino", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "axes.titlesize": 8.0,
            "axes.labelsize": 7.8,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
        }
    )

    extent = [
        float(scene.x.min() / bench.NM_TO_M),
        float(scene.x.max() / bench.NM_TO_M),
        float(scene.y.min() / bench.NM_TO_M),
        float(scene.y.max() / bench.NM_TO_M),
    ]
    terrain = scene.z
    rows: list[dict[str, object]] = []

    fig, axes = plt.subplots(2, 3, figsize=(7.30, 4.55), constrained_layout=False)
    for col, plan in enumerate(plans):
        context = bench.make_context(scene, plan.orientation_deg)
        counts = bench.coverage_counts(context.v_grid, plan.line_positions, context.swath_width)
        gap_map = (counts < 1).astype(float)
        overlap_map = bench.cellwise_excess_overlap(context.v_grid, plan.line_positions, context.swath_width)
        uncovered_pct = float(np.mean(gap_map) * 100.0)
        max_overlap = float(np.nanmax(overlap_map))
        rows.append(
            {
                "scene_id": scene.scene_id,
                "scene_name": scene.display_name,
                "method": plan.method,
                "orientation_deg": plan.orientation_deg,
                "line_count": plan.line_count,
                "path_length_km": plan.path_length_km,
                "predicted_coverage_pct": plan.coverage_pct,
                "uncovered_pct": uncovered_pct,
                "excess_overlap_pct": plan.excess_overlap_pct,
                "max_cell_excess_overlap_pct": max_overlap,
                "feasible": int(plan.feasible),
            }
        )

        ax_top = axes[0, col]
        hill = bench.BATHY_LIGHT.shade(terrain, cmap=bench.BATHY_CMAP, vert_exag=0.25, blend_mode="soft")
        ax_top.imshow(hill, extent=extent, origin="lower", aspect="equal", zorder=0)
        masked_gap = np.ma.masked_where(gap_map < 0.5, gap_map)
        ax_top.imshow(
            masked_gap,
            extent=extent,
            origin="lower",
            aspect="equal",
            cmap=GAP_CMAP,
            vmin=0,
            vmax=1,
            alpha=0.78,
            interpolation="nearest",
            zorder=2,
        )
        _plot_lines(ax_top, scene, plan)
        ax_top.text(
            0.03,
            0.96,
            f"({chr(97 + col)}) {METHOD_LABELS[plan.method]}\n"
            f"C={plan.coverage_pct:.2f}%, gap={uncovered_pct:.2f}%",
            transform=ax_top.transAxes,
            va="top",
            ha="left",
            fontsize=7.4,
            color="#111821",
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#cbd5df", alpha=0.88),
        )
        ax_top.tick_params(labelbottom=False)

        ax_bottom = axes[1, col]
        img = ax_bottom.imshow(
            overlap_map,
            extent=extent,
            origin="lower",
            aspect="equal",
            cmap=OVERLAP_CMAP,
            vmin=0,
            vmax=max(8.0, max_overlap),
            interpolation="nearest",
        )
        ax_bottom.text(
            0.03,
            0.96,
            f"({chr(100 + col)}) Excess overlap\n"
            f"mean={plan.excess_overlap_pct:.2f}%, max={max_overlap:.1f}%",
            transform=ax_bottom.transAxes,
            va="top",
            ha="left",
            fontsize=7.4,
            color="#111821",
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#cbd5df", alpha=0.88),
        )

        for ax in (ax_top, ax_bottom):
            ax.set_xlim(extent[0], extent[1])
            ax.set_ylim(extent[2], extent[3])
            ax.set_xlabel("East-West (NM)" if ax is ax_bottom else "")
            if col == 0:
                ax.set_ylabel("North-South (NM)")
            else:
                ax.set_ylabel("")
            ax.grid(False)
            for spine in ax.spines.values():
                spine.set_linewidth(0.6)
                spine.set_color("#2a3340")

    cax = fig.add_axes([0.92, 0.13, 0.018, 0.32])
    cb = fig.colorbar(img, cax=cax)
    cb.set_label("Cell excess overlap (%)", fontsize=7.6)
    cb.ax.tick_params(labelsize=6.8)

    fig.text(0.065, 0.975, "Complex Terrain failure mode under a single-heading fixed-pattern layout", fontsize=8.6)
    fig.text(
        0.065,
        0.025,
        "Red overlay marks cells with zero predicted MBES coverage; rows use the same synthetic complex-relief scene and the same evaluator.",
        fontsize=6.7,
        color="#3c4753",
    )
    fig.subplots_adjust(left=0.065, right=0.90, top=0.93, bottom=0.135, wspace=0.18, hspace=0.16)

    for out_path in OUT_FIGS:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=320)
    plt.close(fig)
    write_summary(rows)


def main() -> None:
    scene, plans = representative_complex_plans()
    make_figure(scene, plans)
    print(f"Wrote {OUT_CSV}")
    for out in OUT_FIGS:
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
