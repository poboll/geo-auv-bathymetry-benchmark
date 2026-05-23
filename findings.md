# Geo Hard Evidence Extension Findings

## 已确认事实

- 当前主线已从 field-ready AUV 改为 depth-referenced/general MBES public-grid fixed-line benchmark。
- `run_5/all_results.npy` 只保存行级指标字典，不含 `line_positions`，无法直接恢复局部覆盖斑块。
- `geo_public_bathy_benchmark.py` 已提供可复用函数：`fixed_spacing_plan`、`adaptive_spacing_plan`、`full_geometry_aware_hybrid_ga_plan`、`coverage_counts`、`cellwise_excess_overlap`、`make_context`。
- GEBCO 主场景是低重叠 regime，主要价值是 overlap discipline；USGS high-complexity crop 才是高重叠强证据。

## 本轮需要补的证据

- 严格覆盖阈值：95%、97%、98%、99%、99.5%。
- 严格重叠阈值：1%、2%、3%、5%。
- 局部漏测风险：uncovered cell ratio、largest connected uncovered patch、uncovered component count。
- 局部过重叠风险：p95/p99 cellwise excess overlap、max cellwise excess overlap、coverage-count histogram。

## 风险边界

- 这些诊断仍是 public-grid numerical evaluator，不是 hydrographic QA、sea-trial validation 或 altitude-controlled AUV validation。
- 若严格 99%/99.5% 阈值下部分 Hybrid 布局不通过，应如实写为边界，不要包装成全面胜利。

## 2026-05-14 阈值/局部失败正式结果

- 新脚本：`make_threshold_local_failure_extension.py`。
- 新输出目录：`threshold_local_failure_extension/`。
- 正式运行：`conda run -n uu python make_threshold_local_failure_extension.py --seed-count 20`。
- GEBCO Cascadia Hybrid：默认 `C97/O3` 可行，平均覆盖 98.97%，平均超额重叠 0.106%，但 `C99/O2` 通过率只有 0.45，`C99.5/O2` 为 0。
- GEBCO Monterey Hybrid：默认可行，平均覆盖 99.63%，平均超额重叠 0.085%，`C99/O2` 通过率 1.0，`C99.5/O2` 通过率 0.55。
- USGS High Hybrid：默认可行，平均覆盖 98.44%，平均超额重叠 1.732%，但 `C99/O2` 通过率 0，p99 cellwise excess overlap 约 26.03%。
- Fixed-Spacing 在 GEBCO 上虽然均值可通过严格屏幕，但 p99 cellwise overlap 很高：Cascadia 59.89%，Monterey 30.56%，说明均值指标确实会隐藏局部强重叠。

## 2026-05-14 编译与视觉 QA 发现

- 新增图源 PNG 的原始面板布局是干净白底、2x3 结构，色条未遮挡面板。
- 带 alpha 通道的 PNG 在 `gs -sDEVICE=pngalpha` 预览时可能出现黑块假象；实际 `png16m` 白底渲染正常。
- 已将脚本修正为白底 RGB 输出，重新生成后 `threshold_local_failure_journal.png` 和两套 manuscript 图片均为 `hasAlpha: no`。
- 重编后图 15 所在第 32 页用 `pngalpha` 与 `png16m` 预览均正常，无黑块、无色条遮挡。
- 两套 LaTeX PDF 均为 43 页，严格日志扫描无硬错误；旧记录中的 41 页已过期。

## 2026-05-14 老师二轮意见点对点返修发现

- 摘要最终实测为 197 words，符合 JMSE 约 200 words 的安全范围。
- `run_5/benchmark_method_statistics.csv` 已包含 Simple Greedy，因此无需重跑大实验即可补齐 best-heading constant-spacing fairness baseline。
- Simple Greedy 显示 Monterey 的 line-count reduction 和大部分 route-length change 可由 heading rotation 捕获；因此正文已把 terrain-aware spacing 的独立贡献改写为 coverage/overlap balance 和 overlap discipline，而不是把所有路线收益归因于 adaptive spacing。
- GEBCO Cascadia 的 Simple Greedy：75 deg、111 lines、15084.32 km、99.99% coverage、0.01% excess overlap。
- GEBCO Monterey 的 Simple Greedy：90 deg、59 lines、6656.37 km、99.18% coverage、0.30% excess overlap。
- swath evaluator 的实际硬边界来自代码：denominator signed lower bound \(10^{-3}\)，non-finite width to 0，final width clip to 30--1800 m，无单独 slope-class exclusion。
- GEBCO 2025 TID audit 可通过官方 subset API 获取，参数为 `grid_id=2`、`data_source_ids=[6]`、`formats=[2]`。
- TID audit 结果：Cascadia TID 10/11/40/44 = 0.41/91.05/5.44/3.10%；Monterey = 0.02/95.47/2.92/1.58%。
- TID audit 是 provenance/source-type evidence，不应被写成 survey-grade truth；正文已明确 planner 不按 TID 或 source-specific uncertainty 加权。
- 新增 TID 表后 PDF 从 43 页增至 44 页；最终无 LaTeX hard errors、undefined citations/references、overfull 或 float-too-large。
- 最新最终日志为 `compile_after_teacher_final_abstract_v2_20260514_pass2.log`；两套 PDF 仍为 44 页，摘要压缩未引入引用或浮动体错误。

## 2026-05-14 晚间图表版式与正文完整性复核

- 图 4 和图 7 在上一版 PDF 中不是严格意义的“单独空白页”，但图 7/8/9 之间的版式显得松散，图 11/12/13/16 受 `[H]` 强制浮动和较大 `height` 影响，形成连续热图霸屏。
- 图 11=structured prior-error replay，图 12=execution-uncertainty replay，图 13=uncertainty-aware margin replay，图 16=coarse-prior replay；它们应使用统一白底 compact heatmap 风格，而不是大海报式热图。
- 图 9 原三列横排导致中间文字和注释在 PDF 中偏小；改为上方双散点、下方全宽 regime ladder 后，机制读法更清楚。
- 最终 PDF 页码：图 4 第 18 页，图 7/8 第 22 页，图 9 第 23 页，图 11/12 第 28 页，图 13 第 29 页，图 16 第 33 页。
- 页数从 44 变为 42 的原因是图源高度压缩、取消 `[H]` 强制浮动和 LaTeX 更紧凑排布，不是删正文。当前稿仍保留 16 张图、13 张表和新增诊断小节。
- 关于图层：可以基于 bathymetry 自己派生 slope、relief、curvature、swath-risk、source-confidence 等规划层；不能把派生层写成官方 TID/source provenance，也不能伪造缺失的 TID/source fraction。
- 常见 AI 模板句扫描已清理：未命中 `This subsection`、`We now turn`、`Taken together`、`TODO/TBD/FIXME`、`...` 等明显模板/占位痕迹。保留的 AI 使用声明位于 Acknowledgments，符合透明披露需求。

## 2026-05-14 热图二轮审美返修发现

- Matplotlib 官方建议优先使用感知均匀的 colormap，并按数据语义区分 sequential/diverging；ColorBrewer 也强调 sequential/diverging/qualitative 三类色带需要匹配数据类型；Seaborn heatmap 的常规参数则支持 annotation、linewidths、square/cbar 等矩阵呈现控制。对应到本文，热图不应继续依赖高饱和大色条，而应使用克制的连续色带、细网格和明确风险标记。
- Fig. 8/11/12/13/16 的主要问题不是数值，而是视觉层级：红框偏重、色彩略硬、文字层级未统一；已统一为“标题/列标签强调，单元格正常字重，风险单元细边框”的期刊矩阵风格。
- Fig. 15 原本仍保留独立样式和色条，是导致它看起来不像 Fig. 8/11/12/13/16 的主要残留；已改为无色条 2x3 compact matrix，右下角 reading guide 保留，顶部说明交给 caption，不再在图内压字。
- 最新 PDF 页码抽查：Fig. 8 在第 22 页，Fig. 11/12 在第 28 页，Fig. 13 在第 29 页，Fig. 15 在第 32 页，Fig. 16 在第 33 页；这些页面未见热图拉伸、色条覆盖、异常空白页或标题/文字重叠。

## 2026-05-14 no-grid 热图与参考文献收口发现

- 用户指出的“热图内部黑白框线”确实是视觉问题：它让连续误差/风险矩阵看起来像 Excel 表格或分类格子，而不是期刊工程热图。本轮已移除内部 gridline 和粗风险矩形，只保留连续色块、轻量 annotation 和 caption 解释。
- Fig. 8/13/15/16 在最终 PDF 中均为白底、无内部框线、无色条遮挡；Fig. 13/15 信息密度仍较高，但属于“审稿可接受的紧凑诊断图”，不再是版式错误。
- Abbreviations 表不加外框是 MDPI 模板风格，不应为了“看起来像表格”强行添加边框；本轮只补齐最后一行 `\\`，保持 unframed list 形式。
- GEBCO TID 旧链接返回失败，已替换为当前可访问官方页面 `https://www.gebco.net/gebco-tid-grid`。
- 原参考文献中 4 条 `et al.` 条目已修正。特别是 `han2023hybrid` 的最终 DOI 元数据为 2024, volume 11, issue 6, pages 11058--11072；`tang2023coverage` 的 DOI 元数据为单作者 Fei Tang, Ocean Engineering 278:114354。
- `audit/reference_verification_20260514_v2.md` 显示 GEBCO 2025 Grid DOI 和 USGS data-release DOI 可通过 DOI.org 解析；它们不走 Crossref 不是引用造假。
- 重跑 `audit/verify_references_20260514.py` 后，自动引用审计报告 `total 42 failed 0 et_al 0`；正文 DOI、标题、数据产品链接和去 `et al.` 状态均已通过当前自动审计。
- 页数从 44 压到 42 是图源尺寸、浮动策略和热图版式优化造成，不是删除正文证据；当前仍保留 16 张图、13 张表和主要诊断小节。

## 2026-05-14 v13 图表尺寸、字体与配色复核

- 图 2 原先在 LaTeX 中使用 `0.86\textwidth`，导致它比图 3/4 显得保守；本轮改为 `\textwidth` 并保留 `keepaspectratio`，最终第 17 页呈现为满宽 atlas，不出现横向拉伸。
- 图 3/4 的主要问题是内部 panel 标签、比例尺和 summary strip 字体偏小；本轮只调文字、比例尺和路线线宽，不改路线数据、方法颜色或图面布局。
- 图 5 原来混用 serif 字体，与其它图表不统一；本轮改为 Helvetica/Arial/DejaVu Sans，输出为白底 RGB，最终第 20 页无透明层黑底风险。
- 图 10 只做 LaTeX 放大显示，不重设柱状图样式；最终第 25 页图体更接近正文宽度，但仍保留原柱状图结构。
- 热图配色从偏红棕体系改为蓝色 sequential、蓝/暖色 diverging、暖色 risk palette 的组合。这样高覆盖/可行率与风险/失败方向更分明，同时避免 rainbow 和过重框线。
- 当前图表字体策略：图内统一使用 sans-serif（Helvetica/Arial/DejaVu Sans fallback）；正文仍由 LaTeX 模板控制。该策略与 MDPI 对高分辨率图件要求以及 Nature 等顶刊对最终 artwork 使用 Helvetica/Arial 一类无衬线字体的建议一致。

## 2026-05-14 v14 图件放大与实际页面复核

- Fig. 2 在 v13 中虽然设置为 `\textwidth`，但同时有 `0.40\textheight` 高度约束，实际缩放仍被高度限制；v14 删除高度约束后，第 17 页 atlas 与正文宽度对齐。
- Fig. 3/4 的可读性短板集中在图内小字，而不是路线数据；v14 放大 panel 标签、比例尺、summary strip 和表格数字后，第 17/18 页能读出方法标签、比例尺和核心指标。
- Fig. 5 的 panel (c) 原有内部白色网格线会让矩阵看起来像表格；v14 移除该网格线，仅保留连续色块与数字标注，和其它 no-grid heatmap 风格一致。
- Fig. 8 是 5x5 矩阵，适合使用方形单元；v14 将 `aspect="auto"` 改为 `aspect="equal"`，第 22 页热图不再被压成长方形。
- Fig. 10 放大只通过画布和 LaTeX 显示比例完成，未改柱状图数据、分组或颜色；第 25 页图体比 v13 更接近正文宽度和可读尺寸。
- 本轮调研结论：MDPI/JMSE 重点要求图件高分辨率、清晰、字体嵌入、比例锁定；Nature/Elsevier 等顶刊 artwork 指南通常推荐 Arial/Helvetica 等 sans-serif 字体和约 5--8 pt 的最终图内文字。因此本文采用图内 Helvetica/Arial/DejaVu Sans fallback，正文保留模板字体。

## 2026-05-15 老师意见闭环发现

- 摘要在 v14 之后仍为实测 213 words，虽然低于早期 248 words，但对 JMSE “about 200 words maximum”的口径仍偏冒险；v15 压缩到实测 197 words。
- 两套 LaTeX 的摘要内容已经同步，抽取 diff 为空。
- v15 没有改变实验数值、图件数据或 claim boundary；它是投稿前 teacher-checklist closure，不是新实验轮次。
- 本轮再次确认：Simple Greedy baseline 已在 Table `tab:table2` 和方法/结果文字中完成；swath denominator protection 和 \(W_{\min}/W_{\max}\) 已写明；GEBCO TID audit 只用于 provenance evidence；GA 仍被限定为 local repeatability/refinement layer。
- 最新两套 pass2 编译均输出 42 pages；严格日志扫描未发现 LaTeX hard error、undefined citation/reference、Float too large、Overfull、Fatal error 或 Emergency stop。参考文献区仍有 Underfull hbox 换行警告，但不是投稿阻断项。
- 当前无需使用服务器。若后续要新增 operational gated-GA、更多 public datasets 或重新跑多场景大实验，再上服务器才有必要。

## 2026-05-15 v16 五点专项复核发现

- GA 归因再降调：残留的 “Hybrid GA repairs/reduces/suppresses overlap” 风险句已改为 reported hybrid layout、terrain-aware spacing、optional local cleanup、repeatability check 或 overlap discipline；GA 不再被写成主 overlap-control mechanism。
- Baseline 公平性仍成立：Table `tab:table2` 保留 Simple Greedy / best-heading constant-spacing baseline；正文明确 Fixed-Spacing 是 \(0^\circ\) reference baseline，不是最优 constant-spacing baseline。
- 模型细节更完整：正文已同时写明 \(W_{\min}=30\) m、\(W_{\max}=1800\) m、denominator signed lower bound \(10^{-3}\)、non-finite width to zero、无额外 slope-class exclusion、所有方法同一 evaluator，并新增 transducer draft/sonar-head offset 的零近似与 \(D_0-z_T\) 部署替换规则。
- GEBCO TID 已作为表格证据保留：Cascadia 与 Monterey TID 10/11/40/44 比例仍在 Methods 表中，且明确不 TID-weighted；USGS 30 m extension 仍作为更强 high-resolution public-grid transfer check。
- 图表与投稿声明复核通过：关键页 contact sheet 显示无空白页、热图遮挡、黑底透明层或明显拉伸；AI 声明、Data Availability、GitHub/Zenodo concept DOI、reference DOI、单位和 hyphenation 均经本轮扫描/编译/引用审计复核。

## 2026-05-15 v17 图 2/6/14 专项复核发现

- Fig. 2 的用户反馈对应右上说明卡片。旧版“Benchmark roles”式说明容易挤到卡片边缘；新版改为 `(c) Evidence roles`，三条证据角色和最后说明均手动换行。源图 `journal_scene_atlas.png` 原始检查显示最后一句 `Square map cards keep native aspect; depth ranges are local to each scene.` 已在卡片内完整显示。
- Fig. 6 只保留一个渐变比例尺是正确的：上排 (a)--(c) 是红色二值 zero-coverage overlay，不应使用连续 colorbar；下排 (d)--(f) 才是 cellwise excess-overlap 连续场，因此共享一个渐变 colorbar。caption 和图内色条标签已经同步说明这个关系。
- Fig. 6 生成脚本原先写到项目根下的 `latex/pic` 和 `mdpi_jmse/pic`，不会覆盖正文实际图片；v17 已修正到 `manuscript/latex/pic` 和 `manuscript/mdpi_jmse/pic`。
- Fig. 14 的源图已扩大到 3030x1961 RGB，底部三组指标矩阵去掉内部白网格，LaTeX 高度上限从 `0.44\textheight` 放宽到 `0.50\textheight`。最终第 32 页仍是单图页，但没有异常空白页、压缩拉伸、透明黑底或色块覆盖。
- 当前图内字体策略已统一到 sans-serif：`Helvetica`、`Arial`、`DejaVu Sans` fallback。图内只保留短 panel label、方法名、metric heading 和必要说明；完整解释放在 caption。加粗仅用于 panel label、方法/metric heading 或表头，普通数值和说明文字不加粗。
- v17 PDF 为 43 页，页数增加来自 Fig. 14 放大和浮动重新排版，不是正文丢失或异常空白。当前正文仍保留 16 张图、13 张表、42 个唯一 cite key。
- 最新引用审计仍为 `total 42 failed 0 et_al 0`。保留的 `field validation`、`sea-trial validation`、`field-readiness guarantee` 等扫描命中均为否定边界句，用于防止过度声明，不属于“鬼故事”。

## 2026-05-16 v18 投稿边界小补丁发现

- 老师最新意见属于投前小修补，不需要新实验或服务器：最关键的是解释 \(W_{\max}=1800\) m、写入固定 Zenodo version DOI、说明 repo 名称历史原因、清除 AUV/GA 过度表述并保守化 cover letter。
- `https://doi.org/10.5281/zenodo.19919506` 可通过 DOI.org 解析到 Zenodo record `19919506`，因此可作为当前 pre-submission package 的初始固定版本 DOI 写入 Data Availability、cover letter 和 citation metadata。
- \(W_{\max}=1800\) m 现在被定义为 declared benchmark range cap，用于避免深水 GEBCO cells 在 depth-referenced approximation 下生成不现实的超宽 spacing；它不是 sonar-range truth，结果应解释为同一 declared evaluator 内的相对 fixed-line layout improvement。
- README、`CITATION.cff`、`.zenodo.json` 和 cover letter 中的 AUV-assisted/AUV survey planner framing 已降调为 depth-referenced MBES fixed-line planning benchmark。repo 名 `geo-auv-bathymetry-benchmark` 被保留但明确说明为 historical naming。
- cover letter 的 GA 表述已从 “mainly suppresses residual overlap” 改为 local refinement and seed-repeatability check；这与正文 ablation 一致，也避免把 GA 写成 public-scene overlap-control 主机制。
- 风险词扫描后剩余的 `hydrographic-quality`、`field-readiness` 和 `AUV execution` 都在否定边界句中出现，功能是防止过度声明，不是正向 claim。
- v18 两套 LaTeX pass2 日志均输出 43 pages；严格扫描无 LaTeX hard error、undefined citation/reference、Rerun warning、Overfull、Float too large、Fatal error 或 Emergency stop。
- 最新自动引用审计仍为 42 references / 0 failed / 0 et_al；manifest 仍为 235 entries。当前不需要动服务器。

## 2026-05-17 v19 投前 A 类硬补发现

- \(W_{\max}\) 敏感性不是装饰性实验：cap 从 1200 到 2400 m 会显著改变线数和路径总长，因此正文必须继续把 \(W_{\max}\) 写成 declared evaluator parameter，而不是物理 sonar truth。
- GEBCO Cascadia 和 Monterey 在 \(W_{\max}=1200/1800/2400\) m 下 Hybrid GA 均保持默认 \(C97/O3\) 可行，说明低重叠 public-prior regime 的解释没有被 cap 审计推翻。
- USGS High 是真正的 cap-sensitive 负边界：\(W_{\max}=2400\) m 时 Hybrid GA mean coverage 为 98.81%，但 mean excess overlap 升到 6.391%，默认 \(C97/O3\) feasibility rate 为 0。这应作为“overlap-stressed terrain 中 cap selection material”的诚实边界写入，而不是隐藏。
- Adaptive-vs-Hybrid gate diagnostic 支持继续降调 GA：GEBCO 两景 raw Hybrid GA 相对 Adaptive Spacing 的 median path gain 只有 0.0003--0.0004%，且 score-better rate 只有 0.10；保守 operational gate 会多数情况下回退到 Adaptive。
- USGS High 中 GA cleanup 有实际价值但仍需要 gate：raw Hybrid GA 相对 Adaptive 的 median path gain 为 1.3684%，median excess-overlap delta 为 -0.5157 pp，score-better rate 为 1.0；但 coverage median delta 为 -0.1167 pp，gate accepted rate 只有 0.30。
- Methods 中加入 AI-assisted tools disclosure 比单放 Acknowledgments 更稳；Acknowlegments 现在只感谢 GEBCO，避免把合规声明放在非方法位置。
- Data Availability 已删除 future frozen release 条件占位语，改为当前 manuscript package associated fixed version DOI，减少“提交版还没冻结”的编辑风险。
- `README_submission.md` 与 manifest 243 entries 使复现结构更完整；新增 `submission_boundary_diagnostics/` 已被 manifest 收录。
- v19 页数从 v18 的 43 页变为 44 页，原因是新增两个投前边界诊断表；页面预览显示不是异常空白页。

## 2026-05-22 v20 航向分辨率与九窗口统计发现

- P11 航向分辨率质疑可以正面回答：在当前 evaluator 下，Adaptive Spacing 的 \(5^{\circ}\) finer scan 与 \(15^{\circ}\) main scan 在两幅 GEBCO 主场景和 USGS High 上完全一致；因此 Hybrid GA 继承的 deterministic adaptive base 没有被 \(15^{\circ}\) 量化误差主导。
- Simple Greedy 的 Cascadia 结果对 heading resolution 有小幅变化：\(75^{\circ}\rightarrow95^{\circ}\)，路径 -0.123%，coverage +0.011 pp，overlap +0.084 pp。这个变化小于主文 public overlap-cleanup 量级，且不改变 feasibility，因此应写作支持 \(15^{\circ}\) benchmark，而不是把 \(5^{\circ}\) 宣称为新主方法。
- P7/P9 的证据补强不需要伪装成海试：九窗口 paired audit 已把两幅主 GEBCO、四幅补充 GEBCO、三幅 USGS 30 m public crops 统一成 public-window statistics。它不证明全球代表性，但能显著降低“只挑两张图”的风险。
- 九窗口结果的核心结论是 overlap discipline：Adaptive 与 Hybrid 都在 9/9 public windows 上实现 positive overlap cleanup，one-sided Wilcoxon \(p=0.00195\)，rank-biserial 1.00。路径收益是次级结论：7/9 正向，median 0.681%，\(p=0.00977\)，低/中 USGS easy crops 仍可出现轻微负路径收益。
- Coverage delta 是保持保守叙事的关键：Hybrid GA 的 coverage delta median 为 -0.933 pp，coverage-positive windows 只有 2/9，说明 GA 仍必须写成 gated local refinement，不应写成无条件优于 Adaptive Spacing。
- PDF QA：新增九窗口统计表在第 21 页，Heading resolution 行在第 28 页；两者在 MDPI PDF 中未截断、未越界。两套 PDF 均为 45 页，页数增加来自新增证据文本和表格，不是异常空白。
- 自动引用审计的 `xie2024three` DOI failure 是 HTTP 403 站点策略问题；MDPI 官方页面确认该文为 Xie, Hui, Zhou, Shi, JMSE 2024, 12(8), 1366, DOI 10.3390/jmse12081366。不能把这条自动失败误判为假文献。

## 2026-05-22 v21 Figure 1 与 GA surrogate audit 发现

- Figure 1 的旧生成脚本 `make_method_pipeline_figure.py` 指向根目录旧路径 `latex/pic` 和 `mdpi_jmse/pic`，而当前实际投稿稿使用 `manuscript/latex/pic` 与 `manuscript/mdpi_jmse/pic`。这会造成“脚本改了但投稿图没有同步”的风险；v21 已修复脚本路径并重新生成两套 PDF 图源。
- 新 Figure 1 使用 LaTeX/TikZ standalone、`mathpazo` 字体、小圆节点、细箭头和三段括号，不再使用厚长方形外框。PDF 第 5 页抽查显示无文字溢出、无框线拥挤，视觉上比幻灯片式流程图更像期刊方法示意图。
- GA 的 stride-3 surrogate 不是完全无风险，因此不能只用文字解释。v21 新增 `ga_surrogate_audit/`，对 Adaptive Spacing base 附近的本地扰动候选做 stride-3 fitness ranking 与 full-grid rescoring 对比。
- surrogate audit 结果支持当前实现：三类场景 Spearman 均 >= 0.934，Kendall tau 均 >= 0.804，stride-selected best candidate 的 full-grid regret 最大只有 0.0610%。这说明 stride-3 fitness 在本地微调云中可作为筛选加速，但正文仍必须保留 full-grid final rescoring 与 GA gate 作为 safeguards。
- 新增 Table 14 后 PDF 从 45 页变为 46 页，这是新增证据表造成的正常页数增加，不是异常空白页。第 28 页表格未越界、未遮挡。
- 引用审计本轮自动失败 4 条，但均是站点访问策略/SSL 网络问题，不是新增引用或 DOI 假条目。本轮未修改 bibliography，因此 v20 的人工核验结论仍可沿用，并在最终汇报中说明自动 DOI resolver 的局限。

## 2026-05-23 release-readiness 发现

- 目前 GitHub release 只有 `v0.1.0`，而当前稿件已推进到 v21/v22 的 46 页版本；如果要让 Zenodo DOI 对应当前稿，必须新建 GitHub release 后等待 Zenodo 自动生成新版本 DOI。
- 直接 release 当前 HEAD 仍有风险：旧 manifest 的 264 entries 中只有 142 个已经被 Git 跟踪，122 个属于本地未跟踪 artifact。若不处理，Zenodo 归档包会缺少正文 Data Availability 声明的部分诊断证据。
- `manuscript/latex/Definitions/` 是工作稿独立编译所需的 MDPI class/template 文件，但此前是未跟踪目录；新 release 若要求两套 LaTeX 均可编译，应把该目录纳入 Git。
- GEBCO TID 审计应以 audit summary、basket id 和检索元数据为主；不宜在 Data Availability 中强调“维护下载的 TID GeoTIFF subsets”，因为 raw/source public products 应通过官方 GEBCO DOI/服务重新获取。
- 新增 `check_release_readiness.py` 后，投稿包具备了一个可重复的 release gate：required PDFs/source files、evidence directories、manifest-vs-Git 一次性检查，适合在 mint Zenodo DOI 前运行。

## 2026-05-23 v23 JMSE叙事与审稿风险发现

- 当前稿最大风险不再是“没有实验”，而是证据过多导致主线被稀释；本轮将 story 收敛为 fixed-line survey design -> adaptive spacing -> public-regime evidence -> boundary diagnostics。
- 文献和标准层面，IHO C-13、NOAA HSSD 2025、AusSeabed Guidelines 可支撑一个关键说法：overlap/spacing 应由项目要求、深度、声呐范围、质量控制和 survey objective 决定；本文 15/20/C97/O3/Wmax 是 benchmark gate，不是 hydrographic standard。
- GA 小参数可防守，但必须解释成 local cleanup：主 benchmark 数据显示 Hybrid GA planning time 为 0.32--0.94 s，且 public GEBCO 上 Adaptive Spacing 已贡献主要效果，GA 不应被包装成主算法创新。
- 九窗口 public audit 应按 regime 读：8 个 low-overlap windows 的 median path gain 约 0.67%，主要是 overlap regularization；USGS High 是唯一 overlap-stressed public window，才承担大收益证据。
- 新增引用后参考文献总数为 45；自动核验 0 failed/0 et_al。MDPI 站点 403 问题需要 DOI redirect fallback，不应误判为假文献。
- 新增 implementation map 如果直接塞长路径会造成 overfull；用短路径/目录级说明更适合 MDPI 版面。

## 2026-05-23 v24 benchmark/robustness 收束发现

- 老师报告中仍最值得补的点不是新算法，而是让投稿第一眼看到“reproducible benchmark and robustness study”。将该短语放进标题比继续使用宽泛 `planning/design using priors` 更能降低“你到底想证明什么”的审稿风险。
- 摘要加入 rank-biserial effect size 后仍为 199 words，未超过 JMSE 约 200 words 的安全线。
- 参数依据原来分散在 Methods 段落中，虽然内容存在，但审稿人需要自己拼。新增 parameter-rationale 表后，15%/20%/C97/O3/\(W_{\max}\)/score weights/GA budget 的“不是标准、是 benchmark setting、已做 sensitivity”关系更直观。
- 九窗口统计原横向表可以编译，但在 PDF 第 22 页字体过小。改为纵向统计表后，可读性明显提高，并且 coverage delta 的负向结果也进入主表，避免“只报好看的 overlap/path”的质疑。
- v24 页数从 46 增加到 47，原因是新增 parameter-rationale 表和 public-window 表重排，不是异常空白页。
- 关键页视觉 QA：第 1 页新标题不溢出；第 10 页参数表未越界；第 22 页 public-window 表可读且未压缩成密集横线图。
- v24+ 复核后引用审计已回到 45 references / 0 failed / 0 et_al；`kim2017panel` 和 `li2024full` 的 DOI/出版商自动访问可能偶发 SSL EOF、418 或 403，但 Crossref/DOI 元数据已核验，脚本已记录人工 fallback 以免把访问策略误判成假文献。
- v24+ manifest 为 290 entries，release-readiness gate 继续全 0 阻断；这说明当前证据目录、PDF、两套 LaTeX、manifest 与 Git 跟踪关系已满足后续 release/Zenodo 归档前的结构要求。仍不应在用户确认冻结投稿版前创建新 release。

## 2026-05-23 v25 老师新意见再评估

- 当前最值得继续硬补的不是扩大 GA 或继续堆图，而是把 evaluator 物理简化做成可审计证据。老师指出的 “total-width proxy / horizontal raster cell-center evaluator 与真实 MBES survey product 有鸿沟” 是 P0 风险。
- 可本地落地的补强方案是 side-specific footprint validity audit：不做完整声线折射/姿态/声速模型，但至少保留 port/starboard footprint 分解，用同一批代表布局重算 coverage/overlap，量化 total-width proxy 与更细 footprint 子模型之间的差异。
- 这项 audit 的合理表述边界：它能提高 planning-evaluator 透明度，不能替代 beam-level acoustic ray tracing、raw MBES line products、field/lake trials 或 hydrographic QA。
- v25 footprint validity audit 结果：在 GEBCO Cascadia、GEBCO Monterey、USGS High 的 Fixed/Adaptive/Hybrid 代表布局上，side-specific port/starboard 子模型没有改变任何 \(C97/O3\) feasibility decision。
- 关键数值来自 `footprint_validity_audit/footprint_validity_summary.json`：`max_abs_coverage_delta_pp=0.5`、`mean_abs_coverage_delta_pp=0.0827`、`max_abs_overlap_delta_pp=1.2166`、`mean_abs_overlap_delta_pp=0.2600`、`max_count_disagreement_pct=10.4167`、`feasibility_changes_C97_O3=0`。
- 解释边界：该结果支持“benchmark-level conclusion stable under stronger planning-layer footprint check”；但 USGS High 仍有 7.66--10.42% local coverage-count disagreement，所以不能把当前 evaluator 包装成 raw-MBES product QA。

## 2026-05-23 v25d 热图与最终 QA 发现

- 用户指出的新 footprint 热图问题成立：初版源图虽可读，但放入 PDF 后因为图内大标题和底部长说明占高，矩阵本体偏矮，字体显小，视觉上仍有“展示图”而非期刊矩阵的感觉。
- 最终修复策略是把解释完全交给 LaTeX caption：源 PNG 去掉图内标题/脚注，保留 4 列核心指标和 9 行代表布局；这比继续堆图内说明更适合 SCI/PDF 排版。
- 字体策略：该图改为 Times New Roman/STIX serif fallback，使 Figure 16 在 MDPI PDF 中更接近正文/表格观感；其它既有热图仍为 sans-serif 矩阵风格，未在本轮强行大范围改图以避免引入新排版风险。
- 最终 PDF QA 结果：`audit/page_preview_20260523_v25d_final/mdpi_page_37.png` 中 Figure 16 无遮挡、无截断、无异常空白，矩阵和数值可读；周边 caption 明确该审计不是 beam-level ray tracing、raw MBES validation 或 hydrographic QA。
- 引用审计中的 GEBCO/IHO SSL EOF 是官方站点 TLS 抖动，不是文献真实性问题；最终脚本记录 manual fallback 后，`audit/reference_verification_20260514_v2.md` 为 45 references / 0 failed / 0 et_al。
- 当前可发布结构状态：manifest 297 entries，release gate 全 0 阻断。仍不建议在用户最终确认“冻结投稿版”前创建 GitHub release，因为 Zenodo 会自动 mint 新 DOI。
