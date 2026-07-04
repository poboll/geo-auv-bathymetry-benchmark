from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "reproducibility_manifest.json"

PATTERNS = {
    "benchmark_outputs": [
        "run_5/*.csv",
        "run_5/*.json",
        "run_5/*.png",
    ],
    "extension_outputs": [
        "survey_grade_extension_usgs_cascadia/*.csv",
        "survey_grade_extension_usgs_cascadia/*.json",
        "survey_grade_extension_usgs_cascadia/*.md",
        "survey_grade_extension_usgs_cascadia/*.png",
    ],
    "gebco_tid_audit_outputs": [
        "gebco_tid_audit/*.csv",
        "gebco_tid_audit/*.json",
        "gebco_tid_audit/*.md",
        "gebco_tid_audit/*/basket_id.txt",
    ],
    "sensitivity_outputs": [
        "sensitivity/*.csv",
        "sensitivity/*.json",
        "sensitivity/*.png",
    ],
    "uncertainty_outputs": [
        "uncertainty_replay/*.csv",
        "uncertainty_replay/*.json",
        "uncertainty_replay/*.png",
    ],
    "uncertainty_margin_outputs": [
        "uncertainty_margin_replay/*.csv",
        "uncertainty_margin_replay/*.json",
        "uncertainty_margin_replay/*.md",
        "uncertainty_margin_replay/*.png",
    ],
    "current_drift_outputs": [
        "current_drift_replay/*.csv",
        "current_drift_replay/*.json",
        "current_drift_replay/*.md",
        "current_drift_replay/*.png",
    ],
    "current_aware_margin_outputs": [
        "current_aware_margin_optimizer/*.csv",
        "current_aware_margin_optimizer/*.json",
        "current_aware_margin_optimizer/*.md",
        "current_aware_margin_optimizer/*.png",
    ],
    "execution_risk_refinement_outputs": [
        "execution_risk_refinement/*.csv",
        "execution_risk_refinement/*.json",
        "execution_risk_refinement/*.md",
        "execution_risk_refinement/*.png",
    ],
    "structured_prior_error_outputs": [
        "structured_prior_error_replay/*.csv",
        "structured_prior_error_replay/*.json",
        "structured_prior_error_replay/*.md",
        "structured_prior_error_replay/*.png",
    ],
    "segmented_heading_outputs": [
        "segmented_heading_extension/*.csv",
        "segmented_heading_extension/*.json",
        "segmented_heading_extension/*.md",
        "segmented_heading_extension/*.png",
    ],
    "segmented_decision_audit_outputs": [
        "segmented_decision_audit/*.csv",
        "segmented_decision_audit/*.json",
        "segmented_decision_audit/*.md",
        "segmented_decision_audit/*.png",
    ],
    "coarse_prior_replay_outputs": [
        "coarse_prior_replay/*.csv",
        "coarse_prior_replay/*.json",
        "coarse_prior_replay/*.md",
        "coarse_prior_replay/*.png",
    ],
    "threshold_local_failure_outputs": [
        "threshold_local_failure_extension/*.csv",
        "threshold_local_failure_extension/*.json",
        "threshold_local_failure_extension/*.md",
        "threshold_local_failure_extension/*.png",
    ],
    "submission_boundary_outputs": [
        "submission_boundary_diagnostics/*.csv",
        "submission_boundary_diagnostics/*.json",
        "submission_boundary_diagnostics/*.md",
    ],
    "heading_resolution_outputs": [
        "heading_resolution_diagnostic/*.csv",
        "heading_resolution_diagnostic/*.json",
        "heading_resolution_diagnostic/*.md",
        "heading_resolution_diagnostic/*.png",
    ],
    "public_window_statistics_outputs": [
        "public_window_statistics/*.csv",
        "public_window_statistics/*.json",
        "public_window_statistics/*.md",
        "public_window_statistics/*.png",
    ],
    "ga_surrogate_audit_outputs": [
        "ga_surrogate_audit/*.csv",
        "ga_surrogate_audit/*.json",
        "ga_surrogate_audit/*.md",
        "ga_surrogate_audit/*.png",
    ],
    "footprint_validity_audit_outputs": [
        "footprint_validity_audit/*.csv",
        "footprint_validity_audit/*.json",
        "footprint_validity_audit/*.md",
        "footprint_validity_audit/*.png",
    ],
    "external_layout_baseline_audit_outputs": [
        "external_layout_baseline_audit/*.csv",
        "external_layout_baseline_audit/*.json",
        "external_layout_baseline_audit/*.md",
        "external_layout_baseline_audit/*.png",
    ],
    "external_turning_cost_audit_outputs": [
        "external_turning_cost_audit/*.csv",
        "external_turning_cost_audit/*.json",
        "external_turning_cost_audit/*.md",
        "external_turning_cost_audit/*.png",
    ],
    "usgs_source_provenance_outputs": [
        "usgs_source_provenance/*.csv",
        "usgs_source_provenance/*.json",
        "usgs_source_provenance/*.md",
        "usgs_source_provenance/*.png",
    ],
    "altitude_aware_footprint_audit_outputs": [
        "altitude_aware_footprint_audit/*.csv",
        "altitude_aware_footprint_audit/*.json",
        "altitude_aware_footprint_audit/*.md",
        "altitude_aware_footprint_audit/*.png",
    ],
    "usgs_overlap_stress_expansion_outputs": [
        "usgs_overlap_stress_expansion/*.csv",
        "usgs_overlap_stress_expansion/*.json",
        "usgs_overlap_stress_expansion/*.md",
        "usgs_overlap_stress_expansion/*.png",
    ],
    "usgs_stress_crop_expansion_outputs": [
        "usgs_stress_crop_expansion/*.csv",
        "usgs_stress_crop_expansion/*.json",
        "usgs_stress_crop_expansion/*.md",
        "usgs_stress_crop_expansion/*.png",
    ],
    "pso_baseline_outputs": [
        "pso_baseline/*.csv",
        "pso_baseline/*.json",
        "pso_baseline/*.png",
    ],
    "vehicle_aware_outputs": [
        "vehicle_aware_posteval/*.csv",
        "vehicle_aware_posteval/*.json",
        "vehicle_aware_posteval/*.md",
        "vehicle_aware_posteval/*.png",
    ],
    "gebco_scene_expansion_outputs": [
        "gebco_scene_expansion/*.csv",
        "gebco_scene_expansion/*.json",
        "gebco_scene_expansion/*.png",
    ],
    "figure_outputs": [
        "latex/pic/journal_*.png",
        "latex/pic/method_pipeline.pdf",
        "latex/pic/method_pipeline.tex",
        "manuscript/latex/pic/journal_*.png",
        "manuscript/latex/pic/method_pipeline.pdf",
        "manuscript/latex/pic/method_pipeline.png",
        "manuscript/latex/pic/method_pipeline.tex",
        "manuscript/latex/pic/method_pipeline_preview.png",
        "manuscript/latex/pic/real_*.png",
        "manuscript/mdpi_jmse/pic/journal_*.png",
        "manuscript/mdpi_jmse/pic/method_pipeline.pdf",
        "manuscript/mdpi_jmse/pic/method_pipeline.png",
        "manuscript/mdpi_jmse/pic/method_pipeline.tex",
        "manuscript/mdpi_jmse/pic/real_*.png",
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
        "manuscript/latex/Definitions/*",
        "manuscript/mdpi_jmse/Definitions/*",
        "manuscript/latex/Fig/*",
        "manuscript/mdpi_jmse/Fig/*",
    ],
    "release_metadata": [
        "README.md",
        "README_submission.md",
        "RELEASE_NOTES_*.md",
        "CITATION.cff",
        ".zenodo.json",
        "environment.yml",
        ".gitignore",
        "check_release_readiness.py",
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
        "audit/reference_verification_20260514_v*.json",
        "audit/reference_verification_20260514_v*.md",
        "audit/page_preview_20260523_external_baseline_v28/*.png",
        "audit/page_preview_20260524_external_turning_v29/*.png",
        "audit/page_preview_20260524_blockwise_v30/*.png",
        "audit/page_preview_20260524_overlap_stress_v33/*.png",
    ],
    "reproduction_scripts": [
        "geo_public_bathy_benchmark.py",
        "make_journal_figures.py",
        "make_sensitivity_study.py",
        "make_penalty_weight_sensitivity.py",
        "make_uncertainty_replay.py",
        "make_survey_grade_extension.py",
        "make_turning_aware_posteval.py",
        "make_vehicle_aware_posteval.py",
        "make_segmented_heading_extension.py",
        "make_segmented_decision_audit.py",
        "make_structured_prior_error_replay.py",
        "make_uncertainty_margin_replay.py",
        "make_current_drift_replay.py",
        "make_current_aware_margin_optimizer.py",
        "make_execution_risk_refinement.py",
        "make_public_bootstrap_ci.py",
        "make_method_pipeline_figure.py",
        "make_coarse_prior_replay.py",
        "make_pso_baseline.py",
        "make_gebco_scene_expansion.py",
        "make_failure_mode_figure.py",
        "make_threshold_local_failure_extension.py",
        "make_submission_boundary_diagnostics.py",
        "make_heading_resolution_diagnostic.py",
        "make_public_window_statistics.py",
        "make_ga_surrogate_audit.py",
        "make_footprint_validity_audit.py",
        "make_external_layout_baseline_audit.py",
        "make_external_turning_cost_audit.py",
        "make_usgs_source_provenance_audit.py",
        "make_altitude_aware_footprint_audit.py",
        "make_usgs_overlap_stress_expansion.py",
        "make_usgs_stress_crop_expansion.py",
        "make_claim_consistency_audit.py",
        "make_sensitivity_evidence_figures.py",
        "journal_heatmap_style.py",
        "refresh_visuals_from_existing_outputs.py",
    ],
}


def git_tracked_paths() -> set[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {ROOT / line for line in result.stdout.splitlines() if line}


def git_revision() -> dict[str, str | bool]:
    payload: dict[str, str | bool] = {}
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        payload["head_commit"] = head
        payload["head_short"] = head[:7]
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        payload["dirty_worktree_at_manifest_time"] = bool(dirty)
    except (subprocess.CalledProcessError, FileNotFoundError):
        payload["head_commit"] = "unknown"
        payload["head_short"] = "unknown"
        payload["dirty_worktree_at_manifest_time"] = True
    return payload


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    entries: list[dict[str, object]] = []
    seen: set[Path] = set()
    tracked = git_tracked_paths()
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            for path in sorted(ROOT.glob(pattern)):
                if path.is_file() and path not in seen and (not tracked or path in tracked):
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
                "The concept DOI identifies the release series. The current manuscript "
                "package cites the fixed version DOI listed above."
            ),
            "current_git_revision": git_revision(),
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
