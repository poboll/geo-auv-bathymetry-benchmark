# GEBCO TID Audit

This directory contains a source-type audit for the two primary GEBCO 2025 public-prior scenes.
The Type Identifier (TID) layer is downloaded from the GEBCO subset API with `grid_id=2`,
`data_source_ids=[6]`, and GeoTIFF output. The planner does not condition on TID; these
files document that limitation and support the manuscript's public-grid fidelity caveat.

Outputs:
- `gebco_tid_audit_summary.csv`
- `gebco_tid_audit_summary.json`
