# Literature Verification Notes

- Verification pass time: 2026-04-25 CST
- Scope: targeted title/metadata checks for the references most directly supporting track-spacing adaptation, GEBCO provenance, sonar-aware / terrain-aware CPP, and recent AUV/USV CPP baselines.
- Method: exact-title web search and publisher/official-page checks where available. AMiner API was not used because no AMiner token is configured in this session; this note records the online checks that were completed.

## Checked And Kept

| Key | Status | Notes |
|---|---|---|
| `gebco2025grid` | Verified enough for manuscript use | Official GEBCO page confirms GEBCO Compilation Group (2025), GEBCO 2025 Grid, DOI `10.5285/37c52e96-24ea-67ce-e063-7086abc05f29`. Source: https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2025-grid |
| `yordanova2020coverage` | Corrected | Exact-title search confirms title and authors Veronika Yordanova and Bart Gips; DOI added from the IEEE/arXiv metadata trail: `10.1109/LRA.2020.3003886`. Source: https://arxiv.org/abs/2006.12896 |
| `jiang2018route` | Verified enough for manuscript use | Title, International Journal of Advanced Robotic Systems venue, year, article number, and DOI match the manuscript. |
| `mu2025coverage` | Verified enough for manuscript use | Frontiers page metadata supports title, authors, article number, and DOI `10.3389/fmars.2024.1483122`. |
| `li2024full` | Corrected / enriched | JMSE metadata supports `12(9):1522`; authors and DOI `10.3390/jmse12091522` added. Source: https://www.mdpi.com/2077-1312/12/9/1522 |
| `wu2024complete` | Corrected | Manuscript previously had wrong issue/article number (`12(1):154`). Correct metadata is JMSE 2024, `12(6):1025`, DOI `10.3390/jmse12061025`. Source: https://www.mdpi.com/2077-1312/12/6/1025 |
| `yan2024dual` | Verified enough for manuscript use | Exact-title search supports Ocean Engineering article `119252`; retained. |
| `zhang2023multi` | Verified enough for manuscript use | Exact-title search supports Ocean Engineering article `115456`; retained. |
| `han2023hybrid` | Verified enough for manuscript use | Exact-title search supports IEEE Internet of Things Journal metadata; retained. |
| `zhu2019complete` | Verified enough for manuscript use | Exact-title search supports Journal of Intelligent & Robotic Systems metadata; retained. |
| `ling2023active` | Added and verified | Crossref DOI metadata confirms Ling et al., *Active Bathymetric SLAM for autonomous underwater exploration*, *Applied Ocean Research* 130 (2023) 103439, DOI `10.1016/j.apor.2022.103439`. |
| `shields2023feature` | Added and verified | Crossref DOI metadata confirms Shields, Pizarro, and Williams, *Feature Space Exploration for Planning Initial Benthic AUV Surveys*, *Field Robotics* 3 (2023) 652--686, DOI `10.55417/fr.2023021`. |
| `zhou2017terrain` | Added and verified | Crossref DOI metadata confirms Zhou et al., *An Effective Terrain Aided Navigation for Low-Cost Autonomous Underwater Vehicles*, *Sensors* 17(4) (2017) 680, DOI `10.3390/s17040680`. |
| `kim2017panel` | Added and verified | Crossref DOI metadata confirms Kim and Kim, *Panel-based bathymetric SLAM with a multibeam echosounder*, *2017 IEEE Underwater Technology (UT)*, pp. 1--5, DOI `10.1109/UT.2017.7890321`. |
| `zhu2025robust` | Added and verified | Crossref DOI metadata confirms Zhu et al., *Robust underwater SLAM fusing bathymetric and range information*, *Measurement* 242 (2025) 116223, DOI `10.1016/j.measurement.2024.116223`. |

## Remaining Citation Risks

## Final Closure For Current Preprint Round

- Final closure time: 2026-04-26 CST.
- Citation-key integrity was rechecked in `latex/template.tex`: 24 cite keys, 24 bibitems, no missing entries, and no unused bibitems.
- High-priority source checks remain anchored to official or publisher pages already listed above, including GEBCO, IEEE/arXiv metadata, and MDPI pages.
- The deep-pass additions above were verified through direct DOI metadata lookup against Crossref with local proxy variables bypassed (`requests.Session().trust_env = False`) because the shell environment proxy was stale.
- Full AMiner API verification was not run because no AMiner token is configured in the local session. This is closed as a tooling boundary for the current preprint round, not as a claim that every bibliography field is target-journal-final.
- Several references still use `et al.`. This is acceptable for the current embedded-bibliography preprint draft, but a named target journal may require full author-list normalization and DOI completion in that journal's reference style.
