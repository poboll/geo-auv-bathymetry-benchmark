# Coarse-prior to fine-grid replay

This diagnostic plans fixed-pattern line families on coarsened USGS public bathymetry priors and replays the selected layouts on a finer public grid without re-optimization. It remains a public-grid numerical replay, not mission-log validation.

- Hybrid GA seeds: 0--4
- Fine-grid shape: 300 x 240
- Prior target cells: 120, 300, 600 m

| Crop | Prior m | Method | Replay coverage % | Coverage loss pp | Replay Oex % | Replay feasible |
|---|---:|---|---:|---:|---:|---:|
| high | 120 | Adaptive | 97.92 | 0.86 | 1.588 | 1.00 |
| high | 120 | Fixed | 96.06 | 0.92 | 30.909 | 0.00 |
| high | 120 | Hybrid | 97.91 | 0.77 | 1.312 | 1.00 |
| high | 300 | Adaptive | 98.06 | 1.22 | 2.379 | 1.00 |
| high | 300 | Fixed | 96.11 | 0.76 | 24.396 | 0.00 |
| high | 300 | Hybrid | 97.95 | 1.23 | 1.856 | 1.00 |
| high | 600 | Adaptive | 98.29 | 0.27 | 2.525 | 1.00 |
| high | 600 | Fixed | 96.32 | -0.65 | 30.593 | 0.00 |
| high | 600 | Hybrid | 98.31 | 1.02 | 2.157 | 1.00 |
| low | 120 | Adaptive | 100.00 | 0.00 | 0.000 | 1.00 |
| low | 120 | Fixed | 100.00 | 0.00 | 1.633 | 1.00 |
| low | 120 | Hybrid | 100.00 | 0.00 | 0.000 | 1.00 |
| low | 300 | Adaptive | 100.00 | 0.00 | 0.000 | 1.00 |
| low | 300 | Fixed | 100.00 | 0.00 | 1.633 | 1.00 |
| low | 300 | Hybrid | 100.00 | 0.00 | 0.000 | 1.00 |
| low | 600 | Adaptive | 100.00 | 0.00 | 0.000 | 1.00 |
| low | 600 | Fixed | 100.00 | 0.00 | 1.633 | 1.00 |
| low | 600 | Hybrid | 100.00 | 0.00 | 0.000 | 1.00 |
| medium | 120 | Adaptive | 99.93 | 0.07 | 0.000 | 1.00 |
| medium | 120 | Fixed | 99.93 | 0.07 | 1.631 | 1.00 |
| medium | 120 | Hybrid | 99.93 | 0.07 | 0.000 | 1.00 |
| medium | 300 | Adaptive | 99.93 | 0.07 | 0.000 | 1.00 |
| medium | 300 | Fixed | 99.93 | 0.07 | 1.631 | 1.00 |
| medium | 300 | Hybrid | 99.93 | 0.07 | 0.000 | 1.00 |
| medium | 600 | Adaptive | 99.93 | 0.07 | 0.000 | 1.00 |
| medium | 600 | Fixed | 99.93 | 0.07 | 1.631 | 1.00 |
| medium | 600 | Hybrid | 99.93 | 0.07 | 0.000 | 1.00 |
