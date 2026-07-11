from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent

REQUIRED_PATHS = [
    "README.md",
    "CITATION.cff",
    ".zenodo.json",
    "environment.yml",
]

REQUIRED_DIRS = [
    "run_5",
    "sensitivity",
    "pso_baseline",
    "gebco_tid_audit",
    "gebco_scene_expansion",
    "usgs_cascadia_extension",
    "coarse_prior_replay",
    "structured_prior_error_replay",
    "uncertainty_replay",
    "uncertainty_margin_replay",
    "current_drift_replay",
    "current_aware_margin_optimizer",
    "execution_risk_refinement",
    "segmented_heading_extension",
    "segmented_decision_audit",
    "threshold_local_failure_extension",
    "submission_boundary_diagnostics",
    "heading_resolution_diagnostic",
    "public_window_statistics",
    "vehicle_aware_posteval",
    "ga_surrogate_audit",
    "footprint_validity_audit",
    "external_layout_baseline_audit",
    "external_turning_cost_audit",
]

FORBIDDEN_PATH_PATTERNS = [
    "automation_" + "chatgpt_codex/",
    "automation/",
    ".autopilot/",
    ".serena/",
    "audit/",
    "manuscript/",
    "submission_package/",
    "server/",
    "server_results/",
    "reproducibility_manifest.json",
    "mdpi_jmse_jmse_submission_draft.pdf",
    "paper_refined.pdf",
    "geo_public_bathy_rebuild.pdf",
    "chktex_warnings.txt",
]

FORBIDDEN_TEXT_PATTERNS = [
    "Chat" + "GPT",
    "Co" + "dex",
    "Open" + "AI",
    "AUTO" + "PILOT",
    "automation_" + "chatgpt",
    "manual_" + "f116",
    "COE_" + "springer",
    "China Ocean " + "Engineering",
    "Chang" + "long",
    "2021" + "0485",
    "survey" + "_grade",
    "survey" + "-grade",
    "survey" + " grade",
    "SO" + "TA",
    "state-of-the-" + "art",
    "sea " + "trial",
    "field " + "validation",
    "raw MBES " + "validation",
    "navigation-" + "safety",
    "closed-" + "loop",
    "full " + "AUV",
    "complete " + "AUV",
]


def run_git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout


def main() -> int:
    tracked = set(run_git(["ls-files"]).splitlines())

    missing_required_paths = [
        path for path in REQUIRED_PATHS if path not in tracked or not (ROOT / path).is_file()
    ]
    empty_required_dirs = [
        path for path in REQUIRED_DIRS if not any(p.startswith(f"{path}/") for p in tracked)
    ]
    forbidden_paths = sorted(
        path
        for path in tracked
        if any(path == pattern.rstrip("/") or path.startswith(pattern) for pattern in FORBIDDEN_PATH_PATTERNS)
        or path.endswith((".log", ".aux", ".fls", ".fdb_latexmk", ".synctex.gz", ".xdv"))
    )
    text_hits = []
    text_files = [
        path
        for path in tracked
        if Path(path).suffix.lower()
        in {".py", ".md", ".txt", ".tex", ".csv", ".json", ".yml", ".yaml", ".cff"}
    ]
    for path in text_files:
        data = (ROOT / path).read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern in data:
                text_hits.append((path, pattern))

    print(f"tracked_files={len(tracked)}")
    print(f"missing_required_paths={len(missing_required_paths)}")
    for path in missing_required_paths:
        print(f"  MISSING_PATH {path}")
    print(f"empty_required_dirs={len(empty_required_dirs)}")
    for path in empty_required_dirs:
        print(f"  EMPTY_DIR {path}")
    print(f"forbidden_tracked_paths={len(forbidden_paths)}")
    for path in forbidden_paths:
        print(f"  FORBIDDEN_PATH {path}")
    print(f"forbidden_text_hits={len(text_hits)}")
    for path, pattern in text_hits[:80]:
        print(f"  FORBIDDEN_TEXT {path}: {pattern}")

    return 1 if missing_required_paths or empty_required_dirs or forbidden_paths or text_hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
