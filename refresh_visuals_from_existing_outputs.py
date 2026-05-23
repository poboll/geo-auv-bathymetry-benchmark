from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import geo_public_bathy_benchmark as geo
import make_coarse_prior_replay as coarse
import make_journal_figures as journal
import make_segmented_heading_extension as segmented
import make_structured_prior_error_replay as prior
import make_uncertainty_margin_replay as margin
import make_uncertainty_replay as uncertainty


ROOT = Path(__file__).resolve().parent


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_main_journal_figures() -> None:
    summary_rows = journal.load_summary()
    raw_rows = journal.load_raw_rows()
    journal.make_public_route_figures(summary_rows)
    journal.make_metric_heatmap(summary_rows)
    journal.make_overlap_regime_diagnostic(summary_rows)
    for name in [
        "journal_cascadia_routes.png",
        "journal_monterey_routes.png",
        "journal_metric_heatmap.png",
        "journal_overlap_regime.png",
    ]:
        journal.flatten_png(journal.PIC / name)
        for pic_dir in journal.PIC_DIRS[1:]:
            pic_dir.mkdir(parents=True, exist_ok=True)
            (pic_dir / name).write_bytes((journal.PIC / name).read_bytes())
    print("refreshed main journal figures")


def refresh_segmented_figure() -> None:
    payload = read_json(ROOT / "segmented_heading_extension" / "segmented_heading_summary.json")
    scenes = []
    for entry in payload["scenes"]:
        scene_id = entry["scene_id"]
        if scene_id.startswith("synthetic_"):
            for scene in geo.terrain_generators():
                if scene.scene_id == scene_id:
                    scenes.append(scene)
                    break
        else:
            scenes.extend(segmented.load_scenes([scene_id]))
    segmented.make_figure(scenes, payload["raw_rows"], payload["summary_rows"])
    print("refreshed segmented-heading figure")


def refresh_heatmap_figures() -> None:
    prior.make_figure(read_csv_rows(ROOT / "structured_prior_error_replay" / "structured_prior_error_summary.csv"))
    uncertainty.make_figure(read_csv_rows(ROOT / "uncertainty_replay" / "uncertainty_replay_summary.csv"))
    margin.make_figure(read_csv_rows(ROOT / "uncertainty_margin_replay" / "uncertainty_margin_summary.csv"))
    coarse.make_figure(read_csv_rows(ROOT / "coarse_prior_replay" / "coarse_prior_replay_summary.csv"))
    print("refreshed compact heatmap figures")


def main() -> None:
    refresh_main_journal_figures()
    refresh_segmented_figure()
    refresh_heatmap_figures()


if __name__ == "__main__":
    main()
