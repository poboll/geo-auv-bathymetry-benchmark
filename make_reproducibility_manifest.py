from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "reproducibility_manifest.json"

PATTERNS = {
    "benchmark_outputs": [
        "run_5/*.csv",
        "run_5/*.json",
    ],
    "extension_outputs": [
        "survey_grade_extension_usgs_cascadia/*.csv",
        "survey_grade_extension_usgs_cascadia/*.json",
    ],
    "sensitivity_outputs": [
        "sensitivity/*.csv",
        "sensitivity/*.json",
    ],
    "uncertainty_outputs": [
        "uncertainty_replay/*.csv",
        "uncertainty_replay/*.json",
    ],
    "coarse_prior_replay_outputs": [
        "coarse_prior_replay/*.csv",
        "coarse_prior_replay/*.json",
        "coarse_prior_replay/*.md",
    ],
    "pso_baseline_outputs": [
        "pso_baseline/*.csv",
        "pso_baseline/*.json",
    ],
    "gebco_scene_expansion_outputs": [
        "gebco_scene_expansion/*.csv",
        "gebco_scene_expansion/*.json",
    ],
    "figure_outputs": [
        "latex/pic/journal_*.png",
        "latex/pic/method_pipeline.pdf",
        "latex/pic/method_pipeline.tex",
        "manuscript/latex/pic/journal_*.png",
        "manuscript/latex/pic/method_pipeline.pdf",
        "manuscript/latex/pic/method_pipeline.tex",
        "manuscript/mdpi_jmse/pic/journal_*.png",
        "manuscript/mdpi_jmse/pic/method_pipeline.pdf",
        "manuscript/mdpi_jmse/pic/method_pipeline.tex",
    ],
    "manuscripts": [
        "latex/template.tex",
        "latex/template.pdf",
        "mdpi_jmse/template.tex",
        "mdpi_jmse/template.pdf",
        "manuscript/latex/template.tex",
        "manuscript/latex/template.pdf",
        "manuscript/mdpi_jmse/template.tex",
        "manuscript/mdpi_jmse/template.pdf",
        "paper_refined.pdf",
        "geo_public_bathy_rebuild.pdf",
        "mdpi_jmse_jmse_submission_draft.pdf",
    ],
    "release_metadata": [
        "README.md",
        "RELEASE_NOTES_*.md",
        "CITATION.cff",
        ".zenodo.json",
        "environment.yml",
        ".gitignore",
    ],
    "submission_package": [
        "submission_package/*.md",
    ],
    "audit_trail": [
        "geo_next_round_checklist_log.md",
        "reference_verification_20260428_v3.json",
        "literature_verification_notes.md",
        "verify_run_metrics.md",
        "journal_target_assessment_*.md",
        "reviewer_critique_and_revision_*.md",
        "REVIEWER_OBJECTION_MATRIX_*.md",
        "SCI_REAUDIT_REPORT_*.md",
        "DEEP_LITERATURE_POSITIONING_*.md",
        "GEBCO_DATA_BOUNDARY_AUDIT_*.md",
        "SURVEY_GRADE_*.md",
        "audit/*.md",
        "audit/reference_verification_20260428_v3.json",
    ],
    "reproduction_scripts": [
        "geo_public_bathy_benchmark.py",
        "make_journal_figures.py",
        "make_sensitivity_study.py",
        "make_penalty_weight_sensitivity.py",
        "make_uncertainty_replay.py",
        "make_survey_grade_extension.py",
        "make_turning_aware_posteval.py",
        "make_public_bootstrap_ci.py",
        "make_method_pipeline_figure.py",
        "make_coarse_prior_replay.py",
        "make_pso_baseline.py",
        "make_gebco_scene_expansion.py",
        "make_failure_mode_figure.py",
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    entries: list[dict[str, object]] = []
    seen: set[Path] = set()
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            for path in sorted(ROOT.glob(pattern)):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    entries.append(
                        {
                            "category": category,
                            "path": path.relative_to(ROOT).as_posix(),
                            "size_bytes": path.stat().st_size,
                            "sha256": sha256(path),
                        }
                    )

    payload = {
        "manifest_version": "2026-05-02",
        "workspace": str(ROOT),
        "primary_run": "run_5",
        "scope_note": (
            "Reproducibility manifest for the public-bathymetry numerical benchmark "
            "artifacts archived through the GitHub/Zenodo release series."
        ),
        "archive": {
            "github_repository": "https://github.com/poboll/geo-auv-bathymetry-benchmark",
            "zenodo_concept_doi": "10.5281/zenodo.19919505",
            "zenodo_concept_url": "https://doi.org/10.5281/zenodo.19919505",
            "initial_archived_release_tag": "v0.1.0",
            "initial_archived_release_commit": "625fb6a",
            "initial_archived_version_doi": "10.5281/zenodo.19919506",
            "initial_archived_record_url": "https://zenodo.org/records/19919506",
            "note": (
                "The concept DOI identifies the release series and should resolve to "
                "the latest DOI-bearing archive after a final pre-submission release "
                "is minted."
            ),
        },
        "source_data": [
            {
                "name": "GEBCO 2025 Grid",
                "doi": "10.5285/37c52e96-24ea-67ce-e063-7086abc05f29",
                "role": "Primary public gridded bathymetry benchmark source",
            },
            {
                "name": "USGS Southern Cascadia 30 m composite bathymetry",
                "doi": "10.5066/P9C5DBMR",
                "role": "Independent higher-resolution public-grid extension source",
            },
        ],
        "entries": entries,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(entries)} entries")


if __name__ == "__main__":
    main()
