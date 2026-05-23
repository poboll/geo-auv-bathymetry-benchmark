#!/usr/bin/env python3
"""Download GEBCO 2025 TID subsets for the primary scenes and summarize them.

The planner does not use the Type Identifier (TID) layer. This audit records
the source-type mix for the two GEBCO public-prior scenes so the manuscript can
state that boundary with evidence rather than treating GEBCO as a black box.
"""

from __future__ import annotations

import csv
import json
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import requests


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "gebco_tid_audit"
GRID_ID_GEBCO_2025_GLOBAL = 2
DATA_SOURCE_ID_GEBCO_2025_TID = 6
FORMAT_ID_GEOTIFF = 2


SCENES: tuple[dict[str, Any], ...] = (
    {
        "scene_id": "gebco_cascadia_margin_moderate",
        "scene_label": "GEBCO Cascadia Margin",
        "bbox": (-126.8, -125.2, 43.2, 44.8),
    },
    {
        "scene_id": "gebco_monterey_canyon_complex",
        "scene_label": "GEBCO Monterey Canyon",
        "bbox": (-123.3, -122.3, 35.3, 36.3),
    },
)


def _request_subset(scene: dict[str, Any], scene_dir: Path) -> Path:
    left, right, bottom, top = scene["bbox"]
    payload = {
        "id": "0",
        "email": None,
        "submission_date": "2026-05-14T00:00:00",
        "processing_status": "new",
        "items": [
            {
                "id": 0,
                "grid_id": GRID_ID_GEBCO_2025_GLOBAL,
                "data_source_ids": [DATA_SOURCE_ID_GEBCO_2025_TID],
                "formats": [FORMAT_ID_GEOTIFF],
                "left": left,
                "right": right,
                "top": top,
                "bottom": bottom,
            }
        ],
    }
    session = requests.Session()
    session.trust_env = False
    response = session.post("https://download.gebco.net/api/queue", json=payload, timeout=120)
    response.raise_for_status()
    basket_id = response.json()["basketId"]
    (scene_dir / "basket_id.txt").write_text(basket_id + "\n", encoding="utf-8")

    deadline = time.time() + 300
    status_url = f"https://download.gebco.net/api/queue/status/{basket_id}"
    while time.time() < deadline:
        status_response = session.get(status_url, timeout=60)
        status_response.raise_for_status()
        status = status_response.json().get("status")
        if status == "finished":
            break
        if status == "error":
            raise RuntimeError(f"GEBCO TID request failed for {scene['scene_id']}: {status_response.text}")
        time.sleep(2)
    else:
        raise TimeoutError(f"Timed out waiting for GEBCO TID subset for {scene['scene_id']}")

    zip_path = scene_dir / f"{scene['scene_id']}_tid.zip"
    with session.get(f"https://download.gebco.net/api/queue/download/{basket_id}", stream=True, timeout=(30, 240)) as dl:
        dl.raise_for_status()
        with zip_path.open("wb") as fp:
            for chunk in dl.iter_content(chunk_size=1 << 16):
                if chunk:
                    fp.write(chunk)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(scene_dir)
    tifs = sorted(scene_dir.rglob("*.tif")) + sorted(scene_dir.rglob("*.tiff"))
    if not tifs:
        raise FileNotFoundError(f"No TID GeoTIFF found for {scene['scene_id']}")
    return max(tifs, key=lambda path: path.stat().st_size)


def _get_or_download_tid(scene: dict[str, Any]) -> Path:
    scene_dir = OUT_DIR / scene["scene_id"]
    scene_dir.mkdir(parents=True, exist_ok=True)
    cached = sorted(scene_dir.rglob("*.tif")) + sorted(scene_dir.rglob("*.tiff"))
    if cached:
        return max(cached, key=lambda path: path.stat().st_size)
    return _request_subset(scene, scene_dir)


def _summarize_tid(scene: dict[str, Any], tif_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1, masked=True)
        values = np.asarray(arr.compressed(), dtype=int)
        total = int(values.size)
        unique, counts = np.unique(values, return_counts=True)
        rows: list[dict[str, Any]] = []
        for value, count in zip(unique.tolist(), counts.tolist()):
            rows.append(
                {
                    "scene_id": scene["scene_id"],
                    "scene_label": scene["scene_label"],
                    "tid_value": int(value),
                    "cell_count": int(count),
                    "cell_fraction": float(count / total) if total else 0.0,
                    "cell_percent": float(100.0 * count / total) if total else 0.0,
                }
            )
        meta = {
            "scene_id": scene["scene_id"],
            "scene_label": scene["scene_label"],
            "tid_tif": str(tif_path),
            "grid_id": GRID_ID_GEBCO_2025_GLOBAL,
            "data_source_id": DATA_SOURCE_ID_GEBCO_2025_TID,
            "format_id": FORMAT_ID_GEOTIFF,
            "valid_tid_cells": total,
            "tid_values": {str(int(value)): int(count) for value, count in zip(unique.tolist(), counts.tolist())},
        }
        return rows, meta


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    for scene in SCENES:
        tif_path = _get_or_download_tid(scene)
        scene_rows, scene_meta = _summarize_tid(scene, tif_path)
        rows.extend(scene_rows)
        metadata.append(scene_meta)

    csv_path = OUT_DIR / "gebco_tid_audit_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["scene_id", "scene_label", "tid_value", "cell_count", "cell_fraction", "cell_percent"],
        )
        writer.writeheader()
        writer.writerows(rows)

    json_path = OUT_DIR / "gebco_tid_audit_summary.json"
    json_path.write_text(json.dumps({"rows": rows, "metadata": metadata}, indent=2), encoding="utf-8")

    readme = OUT_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# GEBCO TID Audit",
                "",
                "This directory contains a source-type audit for the two primary GEBCO 2025 public-prior scenes.",
                "The Type Identifier (TID) layer is downloaded from the GEBCO subset API with `grid_id=2`,",
                "`data_source_ids=[6]`, and GeoTIFF output. The planner does not condition on TID; these",
                "files document that limitation and support the manuscript's public-grid fidelity caveat.",
                "",
                "Outputs:",
                "- `gebco_tid_audit_summary.csv`",
                "- `gebco_tid_audit_summary.json`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
