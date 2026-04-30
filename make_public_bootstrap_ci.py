from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RUN = ROOT / "run_5"
INPUT = RUN / "benchmark_results.csv"
OUTPUT = RUN / "public_hybrid_bootstrap_ci.csv"

N_BOOT = 20000
RNG_SEED = 20260429


def ci(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return float("nan"), float("nan")
    idx = rng.integers(0, len(values), size=(N_BOOT, len(values)))
    means = values[idx].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def fmt(value: float) -> float:
    return float(round(value, 4))


def main() -> None:
    df = pd.read_csv(INPUT)
    public = df[df["scene_group"] == "public"].copy()
    rng = np.random.default_rng(RNG_SEED)
    rows: list[dict[str, object]] = []

    for scene_id, scene_rows in public.groupby("scene_id", sort=False):
        fixed = scene_rows[scene_rows["method"] == "Fixed-Spacing"].iloc[0]
        hybrid = scene_rows[scene_rows["method"] == "Full Geometry-Aware Hybrid GA"].copy()
        if len(hybrid) < 2:
            continue

        fixed_path = float(fixed["path_length_km"])
        fixed_oex = float(fixed["excess_overlap_pct"])
        fixed_cov = float(fixed["coverage_pct"])

        path_gain = (fixed_path - hybrid["path_length_km"].to_numpy(dtype=float)) / fixed_path * 100.0
        overlap_cleanup = fixed_oex - hybrid["excess_overlap_pct"].to_numpy(dtype=float)
        coverage_delta = hybrid["coverage_pct"].to_numpy(dtype=float) - fixed_cov

        metrics = {
            "path_gain_vs_fixed_pct": path_gain,
            "coverage_pct": hybrid["coverage_pct"].to_numpy(dtype=float),
            "coverage_delta_vs_fixed_pp": coverage_delta,
            "excess_overlap_pct": hybrid["excess_overlap_pct"].to_numpy(dtype=float),
            "overlap_cleanup_vs_fixed_pp": overlap_cleanup,
            "path_length_km": hybrid["path_length_km"].to_numpy(dtype=float),
        }
        base: dict[str, object] = {
            "scene_id": scene_id,
            "scene_name": fixed["scene_name"],
            "method": "Full Geometry-Aware Hybrid GA",
            "n_seeds": len(hybrid),
            "fixed_path_length_km": fmt(fixed_path),
            "fixed_coverage_pct": fmt(fixed_cov),
            "fixed_excess_overlap_pct": fmt(fixed_oex),
            "feasible_seeds": int(hybrid["feasible"].sum()),
            "dominant_orientation_deg": float(hybrid["orientation_deg"].mode().iloc[0]),
            "dominant_line_count": int(hybrid["line_count"].mode().iloc[0]),
        }
        for name, values in metrics.items():
            low, high = ci(values, rng)
            base[f"{name}_mean"] = fmt(float(np.mean(values)))
            base[f"{name}_std"] = fmt(float(np.std(values, ddof=1)))
            base[f"{name}_ci95_low"] = fmt(low)
            base[f"{name}_ci95_high"] = fmt(high)
        rows.append(base)

    fieldnames = list(rows[0].keys())
    with OUTPUT.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
