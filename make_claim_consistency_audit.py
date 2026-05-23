from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "audit"
TEX_FILES = (
    ROOT / "manuscript" / "latex" / "template.tex",
    ROOT / "manuscript" / "mdpi_jmse" / "template.tex",
)


@dataclass(frozen=True)
class Check:
    name: str
    expected_snippets: tuple[str, ...]
    forbidden_snippets: tuple[str, ...] = ()


def read_manuscripts() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in TEX_FILES}


def row(df: pd.DataFrame, **selectors: str) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for key, value in selectors.items():
        mask &= df[key].astype(str).eq(value)
    matches = df[mask]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one row for {selectors}, found {len(matches)}")
    return matches.iloc[0]


def contains_scene(df: pd.DataFrame, scene_substring: str, **selectors: str) -> pd.Series:
    mask = df["scene_id"].astype(str).str.contains(scene_substring, regex=False)
    for key, value in selectors.items():
        mask &= df[key].astype(str).eq(value)
    matches = df[mask]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one row for scene containing {scene_substring!r} and {selectors}, found {len(matches)}")
    return matches.iloc[0]


def feasible_count_text(row_data: pd.Series) -> str:
    feasible = int(round(float(row_data["feasible_rate"]) * int(row_data["n_mc"])))
    total = int(row_data["n_mc"])
    return f"{feasible}/{total}"


def build_checks() -> list[Check]:
    uncertainty = pd.read_csv(ROOT / "uncertainty_replay" / "uncertainty_replay_summary.csv")
    margin = pd.read_csv(ROOT / "uncertainty_margin_replay" / "uncertainty_margin_summary.csv")
    current = pd.read_csv(ROOT / "current_drift_replay" / "current_drift_summary.csv")

    cascadia_hybrid_moderate = row(
        uncertainty,
        scene_id="gebco_cascadia_margin_moderate",
        scenario="moderate_noise",
        method="Full Geometry-Aware Hybrid GA",
    )
    monterey_hybrid_moderate = row(
        uncertainty,
        scene_id="gebco_monterey_canyon_complex",
        scenario="moderate_noise",
        method="Full Geometry-Aware Hybrid GA",
    )

    usgs_hybrid_moderate = contains_scene(
        margin,
        "usgs_southern_cascadia_30m_high",
        scenario="moderate_noise",
        method_label="Hybrid",
    )
    usgs_ua_moderate = contains_scene(
        margin,
        "usgs_southern_cascadia_30m_high",
        scenario="moderate_noise",
        method_label="UA-Hybrid",
    )

    monterey_hybrid_adverse = row(
        current,
        scene_id="gebco_monterey_canyon_complex",
        scenario="adverse_current",
        method_label="Hybrid",
    )
    monterey_ua_adverse = row(
        current,
        scene_id="gebco_monterey_canyon_complex",
        scenario="adverse_current",
        method_label="UA-Hybrid",
    )

    return [
        Check(
            name="Execution-uncertainty moderate feasibility counts",
            expected_snippets=(
                f"{feasible_count_text(cascadia_hybrid_moderate)} Cascadia",
                f"{feasible_count_text(monterey_hybrid_moderate)} Monterey",
            ),
            forbidden_snippets=("298/300 Cascadia", "300/300 Monterey trials"),
        ),
        Check(
            name="USGS High moderate-noise UA-Hybrid margin claim",
            expected_snippets=(
                f"from {float(usgs_hybrid_moderate['feasible_rate']):.3f} to {float(usgs_ua_moderate['feasible_rate']):.3f}",
                f"from {float(usgs_hybrid_moderate['excess_overlap_pct_p95']):.2f} percent to {float(usgs_ua_moderate['excess_overlap_pct_p95']):.2f} percent",
            ),
        ),
        Check(
            name="Monterey adverse-current UA-Hybrid claim",
            expected_snippets=(
                f"from {float(monterey_hybrid_adverse['feasible_rate']):.3f} to {float(monterey_ua_adverse['feasible_rate']):.3f}",
                f"from {float(monterey_hybrid_adverse['excess_overlap_pct_p95']):.2f} to {float(monterey_ua_adverse['excess_overlap_pct_p95']):.2f} percent",
            ),
        ),
    ]


def main() -> int:
    texts = read_manuscripts()
    checks = build_checks()
    failures: list[str] = []
    lines = [
        "# Claim Consistency Audit\n\n",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        "This audit compares a small set of manuscript headline claims against the current replay CSV outputs. It is intentionally narrow: it guards the claims most likely to drift after rerunning stochastic diagnostics.\n\n",
        "## Results\n\n",
    ]

    for check in checks:
        lines.append(f"### {check.name}\n\n")
        for snippet in check.expected_snippets:
            missing = [path for path, text in texts.items() if snippet not in text]
            if missing:
                failures.append(f"Missing expected snippet {snippet!r} in {', '.join(str(p.relative_to(ROOT)) for p in missing)}")
                lines.append(f"- FAIL expected `{snippet}`\n")
            else:
                lines.append(f"- PASS expected `{snippet}`\n")
        for snippet in check.forbidden_snippets:
            present = [path for path, text in texts.items() if snippet in text]
            if present:
                failures.append(f"Forbidden stale snippet {snippet!r} found in {', '.join(str(p.relative_to(ROOT)) for p in present)}")
                lines.append(f"- FAIL forbidden `{snippet}`\n")
            else:
                lines.append(f"- PASS forbidden `{snippet}` absent\n")
        lines.append("\n")

    if failures:
        lines.append("## Failures\n\n")
        for failure in failures:
            lines.append(f"- {failure}\n")
    else:
        lines.append("## Verdict\n\nAll checked headline claims are synchronized with the current CSV outputs.\n")

    AUDIT.mkdir(parents=True, exist_ok=True)
    out = AUDIT / "CLAIM_CONSISTENCY_AUDIT_20260512.md"
    out.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
