from __future__ import annotations

import csv
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RUN = ROOT / "run_5"
INPUT = RUN / "benchmark_method_statistics.csv"
OUTPUT = RUN / "turning_aware_public_posteval.csv"

PUBLIC_METHODS = [
    "Fixed-Spacing",
    "Adaptive Spacing w/o GA",
    "Full Geometry-Aware Hybrid GA",
]
R_MIN_VALUES_M = [25, 50, 100]


def main() -> None:
    df = pd.read_csv(INPUT)
    public = df[(df["scene_group"] == "public") & (df["method"].isin(PUBLIC_METHODS))].copy()

    rows: list[dict[str, str | float | int]] = []
    for scene_id, group in public.groupby("scene_id", sort=False):
        fixed = group[group["method"] == "Fixed-Spacing"].iloc[0]
        fixed_l = float(fixed["path_length_km_mean"])
        fixed_n = float(fixed["line_count_mean"])
        fixed_turns = max(int(round(fixed_n)) - 1, 0)

        for _, row in group.iterrows():
            line_count = int(round(float(row["line_count_mean"])))
            turns = max(line_count - 1, 0)
            length_km = float(row["path_length_km_mean"])
            out: dict[str, str | float | int] = {
                "scene_id": scene_id,
                "scene_name": row["scene_name"],
                "method": row["method"],
                "line_count": line_count,
                "turn_count": turns,
                "geometric_length_km": length_km,
                "geometric_gain_vs_fixed_pct": (fixed_l - length_km) / fixed_l * 100.0,
            }
            for radius_m in R_MIN_VALUES_M:
                effective = length_km + turns * math.pi * radius_m / 1000.0
                fixed_effective = fixed_l + fixed_turns * math.pi * radius_m / 1000.0
                out[f"turning_length_R{radius_m}_km"] = effective
                out[f"turning_gain_R{radius_m}_pct"] = (
                    (fixed_effective - effective) / fixed_effective * 100.0
                )
            rows.append(out)

    fieldnames = list(rows[0].keys())
    with OUTPUT.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
