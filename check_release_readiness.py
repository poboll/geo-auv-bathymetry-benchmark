from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "reproducibility_manifest.json"

REQUIRED_PATHS = [
    "README.md",
    "README_submission.md",
    "CITATION.cff",
    ".zenodo.json",
    "environment.yml",
    "reproducibility_manifest.json",
    "manuscript/mdpi_jmse/template.tex",
    "manuscript/mdpi_jmse/template.pdf",
    "manuscript/latex/template.tex",
    "manuscript/latex/template.pdf",
    "mdpi_jmse_jmse_submission_draft.pdf",
    "paper_refined.pdf",
    "geo_public_bathy_rebuild.pdf",
]

REQUIRED_DIRS = [
    "run_5",
    "sensitivity",
    "pso_baseline",
    "gebco_tid_audit",
    "gebco_scene_expansion",
    "survey_grade_extension_usgs_cascadia",
    "coarse_prior_replay",
    "structured_prior_error_replay",
    "uncertainty_replay",
    "uncertainty_margin_replay",
    "current_drift_replay",
    "current_aware_margin_optimizer",
    "execution_risk_refinement",
    "segmented_heading_extension",
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
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_paths = {entry["path"] for entry in manifest["entries"]}

    missing_required_paths = [
        path for path in REQUIRED_PATHS if path not in tracked or not (ROOT / path).is_file()
    ]
    empty_required_dirs = [
        path for path in REQUIRED_DIRS if not any(p.startswith(f"{path}/") for p in tracked)
    ]
    untracked_manifest_entries = sorted(path for path in manifest_paths if path not in tracked)
    tracked_not_in_manifest_core = sorted(
        path
        for path in tracked
        if (
            path.startswith(tuple(f"{d}/" for d in REQUIRED_DIRS))
            or path.startswith("manuscript/mdpi_jmse/")
            or path.startswith("manuscript/latex/")
        )
        and Path(path).suffix.lower() in {".csv", ".json", ".md", ".png", ".pdf", ".tex", ".yml"}
        and path not in manifest_paths
        and not any(token in path for token in [".aux", ".log", ".xdv"])
    )

    print(f"manifest_entries={len(manifest_paths)}")
    print(f"tracked_files={len(tracked)}")
    print(f"missing_required_paths={len(missing_required_paths)}")
    for path in missing_required_paths:
        print(f"  MISSING_PATH {path}")
    print(f"empty_required_dirs={len(empty_required_dirs)}")
    for path in empty_required_dirs:
        print(f"  EMPTY_DIR {path}")
    print(f"untracked_manifest_entries={len(untracked_manifest_entries)}")
    for path in untracked_manifest_entries:
        print(f"  UNTRACKED_MANIFEST {path}")
    print(f"tracked_core_files_not_in_manifest={len(tracked_not_in_manifest_core)}")
    for path in tracked_not_in_manifest_core[:80]:
        print(f"  NOT_IN_MANIFEST {path}")

    return 1 if missing_required_paths or empty_required_dirs or untracked_manifest_entries else 0


if __name__ == "__main__":
    raise SystemExit(main())
