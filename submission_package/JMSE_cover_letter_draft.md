# Cover Letter Draft for JMSE Special Issue

Dear Guest Editors,

We are pleased to submit our manuscript entitled “Terrain-Aware AUV Survey-Line Planning for Multibeam Bathymetric Mapping Using Public Bathymetry Benchmarks” for consideration in the JMSE Special Issue “Advancements in Autonomous Systems for Complex Maritime Operations”.

The manuscript addresses AUV-assisted bathymetric surveying, a topic that is directly aligned with the Special Issue scope on autonomous marine systems and ocean bathymetric surveying technologies using AUVs/ASVs. We study a pre-mission planning problem that is common in multibeam echo sounder (MBES) mapping: a simple fixed lawnmower survey pattern is easy to inspect and execute, but uniform spacing can be poorly matched to terrain-dependent swath variation. The paper therefore develops a terrain-aware fixed-pattern survey-line planner that combines a local sensor-terrain footprint model, orientation search, adaptive spacing, and a small Genetic Algorithm refinement step for cross-track line positions.

The contribution is framed as a public-bathymetry numerical benchmark rather than as a sea-trial or mission-log validation. The main evidence uses two GEBCO 2025 public gridded bathymetry scenes, three synthetic stress-test terrains, a supplemental four-window GEBCO scene-expansion check, an independent USGS Southern Cascadia 30 m public-grid extension, a coarse-prior/fine-grid replay, and an execution-uncertainty replay. The public GEBCO results show that the principal benefit is overlap discipline and layout regularization rather than dramatic route shortening: the Full Geometry-Aware Hybrid GA reaches 98.97--99.63% predicted coverage, reduces mean scene-level excess-overlap violation from about 0.81% to 0.095%, and achieves a 0.75% mean scene-level path-length reduction relative to Fixed-Spacing. Ablation and optimizer diagnostics show that terrain-aware spacing is the main source of the public-scene path benefit, while GA refinement mainly suppresses residual overlap and stabilizes the final line layout across seeds.

We believe the manuscript fits the Special Issue because it contributes an auditable prior-map geometry layer for autonomous maritime survey planning. It also explicitly reports transfer boundaries that are important for operation-oriented readers: GEBCO is a public benchmark input rather than a survey-grade product, the hardest complex-terrain stress test remains infeasible under the single-heading lawnmower assumption, and stronger execution perturbations require explicit uncertainty margins before field deployment.

The manuscript is original, has not been published elsewhere, and is not under consideration by another journal. All authors have approved the submitted version. The manuscript-specific code, derived benchmark outputs, figure scripts, LaTeX artifacts, and SHA-256 reproducibility manifest are available in the public GitHub repository https://github.com/poboll/geo-auv-bathymetry-benchmark, with the Zenodo release series archived under concept DOI https://doi.org/10.5281/zenodo.19919505. The raw public bathymetry sources are cited through their official GEBCO and USGS DOI landing pages.

Thank you for considering our manuscript.

Sincerely,

Changlong Li  
School of Information Technology and Engineering  
Guangzhou College of Commerce  
Email: 20210485@gcc.edu.cn
