# Deep Literature Positioning Memo

- Date: 2026-04-26 CST
- Workspace: `/Users/Apple/Developer/paper/PaperForge/results/paper_writer/20260423_152326_geo_public_bathy_rebuild_round2`
- Manuscript: `latex/template.tex`
- Purpose: strengthen the SCI story line by making the manuscript's narrow contribution boundary explicit against adjacent AUV coverage, bathymetric SLAM, terrain-aided navigation, sonar-aware CPP, and prior-map survey-design literature.

## Executive Summary

The literature review should not claim that existing AUV planning work is weak. The stronger and more defensible story is that adjacent work usually changes a different part of the system: online replanning, vehicle cooperation, search allocation, SLAM/map consistency, or field-oriented habitat sampling. The current paper keeps the vehicle count, route order, and fixed lawnmower topology constant so that the effect of terrain-dependent MBES swath geometry can be isolated on public GEBCO grids and synthetic stress tests.

## Research Lines And How They Shape The Manuscript

| Line | Representative sources checked | Implication for the Geo manuscript |
|---|---|---|
| Online bathymetric mapping and active SLAM | Shi et al. 2020; Zhang et al. 2022; Ling et al. 2023 | These papers motivate adaptive/autonomous mapping, but they solve online exploration or replanning rather than pre-mission fixed-line placement. The manuscript now uses them to define contrast, not to overclaim parity. |
| Track-spacing and sonar-aware planning | Yordanova and Gips 2020; Jiang et al. 2018; Mu and Gao 2025 | These are the closest methodological neighbors. The manuscript now emphasizes that adaptive spacing is the main public-scene gain and that GA is a refinement stage. |
| Prior-map field-oriented survey design | Shields, Pizarro, and Williams 2023 | This validates the relevance of broad-scale prior bathymetry for initial AUV survey design, while also clarifying that the present work is about MBES coverage/overlap geometry rather than benthic feature-space sampling. |
| Multi-vehicle and heuristic CPP | Xie et al. 2024; Li et al. 2024; Ji et al. 2022; Han et al. 2023 | These studies broaden route topology, vehicle count, task allocation, or search objectives. The manuscript now explains why the current benchmark freezes these variables. |
| Terrain-aided navigation and bathymetric SLAM | Zhou et al. 2017; Kim and Kim 2017; Zhu et al. 2025 | These works support the importance of bathymetry in underwater navigation/mapping but do not replace offline line-layout design. The manuscript uses them to set the deployment boundary. |

## Manuscript Changes Made

- Added a new Related Work positioning table in `latex/template.tex` (`tab:positioning`).
- Rewrote the uncertainty/SLAM paragraph so it no longer depends on unverified review keys.
- Preserved the strict evidence boundary: public GEBCO gridded bathymetry numerical benchmark, not sea-trial validation.
- Kept the main contribution narrow: prior-map fixed-pattern MBES survey-line layout with adaptive-spacing and GA-refinement effects separated.

## Verified Sources Added Or Used In This Pass

- Ling Y, Li Y, Ma T, Cong Z, Xu S, Li Z. *Active Bathymetric SLAM for autonomous underwater exploration*. Applied Ocean Research. 2023;130:103439. DOI: https://doi.org/10.1016/j.apor.2022.103439
- Shields J, Pizarro O, Williams SB. *Feature Space Exploration for Planning Initial Benthic AUV Surveys*. Field Robotics. 2023;3:652-686. DOI: https://doi.org/10.55417/fr.2023021
- Yordanova V, Gips B. *Coverage path planning with track spacing adaptation for autonomous underwater vehicles*. IEEE Robotics and Automation Letters. 2020;5(2):3348-3355. DOI: https://doi.org/10.1109/LRA.2020.3003886
- Mu X, Gao W. *Coverage path planning for multi-AUV considering ocean currents and sonar performance*. Frontiers in Marine Science. 2025;11:1483122. DOI: https://doi.org/10.3389/fmars.2024.1483122
- Zhou L, Cheng X, Zhu Y, Dai C, Fu J. *An Effective Terrain Aided Navigation for Low-Cost Autonomous Underwater Vehicles*. Sensors. 2017;17(4):680. DOI: https://doi.org/10.3390/s17040680
- Kim T, Kim J. *Panel-based bathymetric SLAM with a multibeam echosounder*. 2017 IEEE Underwater Technology (UT). DOI: https://doi.org/10.1109/UT.2017.7890321
- Zhu Y, Ma T, Fan J, Jiang Y, Li Y, Liao Y, Qi C. *Robust underwater SLAM fusing bathymetric and range information*. Measurement. 2025;242:116223. DOI: https://doi.org/10.1016/j.measurement.2024.116223
- GEBCO Compilation Group. *GEBCO 2025 Grid*. DOI: https://doi.org/10.5285/37c52e96-24ea-67ce-e063-7086abc05f29

## Remaining Research Risk

- Several older or secondary bibliography entries still use abbreviated author lists (`et al.`). This is acceptable for the current embedded-bibliography preprint but should be normalized once a target journal style is selected.
- The paper still lacks sea-trial logs, raw MBES returns, or survey-grade mission replay. The manuscript must continue to present the GEBCO layer as public gridded bathymetry evidence for a numerical benchmark, not as field validation.
- The new positioning table improves reviewer readability, but target-journal page limits may require moving it to supplementary material later.
