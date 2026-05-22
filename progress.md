# Geo Hard Evidence Extension Progress

## 2026-05-14

- 读取了当前交接摘要、老师意见核对 MD、主 benchmark 脚本与 manuscript 结构。
- 确认两个 LaTeX 版本上一轮已可编译，但本轮尚未重新编译。
- 确认需要追加证据型实验，而不是只继续润色文字。
- 建立本轮文件化计划，后续每完成阶段更新。
- 新增 `make_threshold_local_failure_extension.py`，重建两个 GEBCO 主场景和 USGS high-complexity crop 的代表性布局。
- 完成 smoke test 与正式 20-seed 运行，输出 `threshold_local_failure_extension/threshold_local_failure_raw.csv`、`threshold_local_failure_summary.csv`、`threshold_local_failure_summary.json` 和 `threshold_local_failure_journal.png`。
- 新图已复制到 `manuscript/latex/pic/journal_threshold_local_failure.png` 和 `manuscript/mdpi_jmse/pic/journal_threshold_local_failure.png`。
- 已将新增 threshold/local-failure 诊断写入两套 LaTeX 模板，包括方法门槛说明、结果小节、讨论边界、风险矩阵、结论和 Data Availability。
- 发现 Ghostscript `pngalpha` 预览会把带 alpha 的图像渲染出黑块风险，因此将 `make_threshold_local_failure_extension.py` 改为保存后合成白底 RGB PNG。
- 重新运行正式命令 `conda run -n uu python make_threshold_local_failure_extension.py --seed-count 20`，核心数值保持一致，输出 PNG 均已确认 `hasAlpha: no`。
- 强制重编 `manuscript/mdpi_jmse` 与 `manuscript/latex`，两套 PDF 均为 43 页。
- 严格日志扫描未发现 `LaTeX Error`、`Undefined control sequence`、undefined citations/references、`Float too large`、`Overfull \hbox`、`Overfull \vbox`、fatal/emergency stop 等命中。
- 已复制最终交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`。
- 重新运行 `conda run -n uu python make_reproducibility_manifest.py`，`reproducibility_manifest.json` 更新为 233 entries。
- 继续处理老师二轮“大修但肯定”意见：摘要从约 248 words 压缩到 194--198 words 区间，并保留 GEBCO、USGS、负结果边界。
- 将两套 LaTeX 模板同步改为：Simple Greedy 是 best-heading constant-spacing fairness baseline；Fixed-Spacing 是 \(0^\circ\) reference baseline；Adaptive Spacing without GA 才是 terrain-aware spacing 主效应；GA 降调为 local repeatability/refinement。
- 将 Table 7 从三方法扩展为四方法：Fixed-Spacing、Simple Greedy、Adaptive Spacing without GA、Full Geometry-Aware Hybrid GA，并补充 heading 和 line count 列。
- 在 swath model 方法段写明共同 evaluator 细节：denominator signed lower bound \(10^{-3}\)、non-finite width 映射为 0、\(W_{\min}=30\) m、\(W_{\max}=1800\) m、无额外 slope-class exclusion，且所有方法使用同一规则。
- 新增 `make_gebco_tid_audit.py`，使用 GEBCO 2025 subset API `grid_id=2`、`data_source_ids=[6]`、GeoTIFF 格式下载两个主场景 TID 栅格。
- 运行 `conda run -n uu python make_gebco_tid_audit.py`，输出 `gebco_tid_audit/gebco_tid_audit_summary.csv`、`gebco_tid_audit/gebco_tid_audit_summary.json` 和两套 TID GeoTIFF 子集。
- 将 GEBCO TID 审计写入 Methods 新表：Cascadia TID 10/11/40/44 = 0.41/91.05/5.44/3.10%；Monterey = 0.02/95.47/2.92/1.58%；明确 planner 不按 TID 加权。
- 新增 `gebco_tid_grid` 参考文献，AI 使用声明更新为 language polishing、revision-structure checking、code-editing assistance，并声明作者独立核验数据处理、实验命令、数值结果和正文。
- 重新运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 仍为 233 entries。
- 最终重编 `manuscript/mdpi_jmse` 与 `manuscript/latex`：`compile_after_teacher_tid_final_20260514_pass1.log` 和 `pass2.log` 均输出 44 pages。
- 最终日志扫描未发现 `LaTeX Error`、`Undefined control sequence`、undefined citation/reference、`Float too large`、`Overfull`、fatal/emergency stop。
- 已更新交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`。
- 视觉抽检新增 TID 表和扩展后的 Table 7：表格未越界，TID 表与公共场景表可读；新增 TID 表使页数从 43 页变为 44 页。
- 复核发现摘要实测为 208 words，略高于 JMSE 约 200 words 安全线；已再次压缩到实测 197 words，并保留 GEBCO、USGS、GA 降调和非 field/hydrographic validation 边界。
- 重新运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 保持 233 entries。
- 最终重编两套模板：`compile_after_teacher_final_abstract_v2_20260514_pass2.log` 均输出 44 pages。
- 最终交付 PDF 已更新到 2026-05-14 16:23：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`。
- 继续按用户 2026-05-14 晚间反馈修复最终图表版式：重新映射图号，确认图 4=Monterey public routes、图 7=segmented-heading repair、图 8=metric heatmap、图 9=overlap-regime、图 11/12/13/16=四组 compact heatmap/replay 诊断。
- 修改 `make_journal_figures.py`：将图 9 从三列横排改为上方双散点、下方全宽 regime ladder，放大可读文字并避免注释贴边。
- 修改 `journal_heatmap_style.py`、`make_structured_prior_error_replay.py`、`make_uncertainty_replay.py`、`make_uncertainty_margin_replay.py`、`make_coarse_prior_replay.py`：统一白底紧凑热图样式，减少空白、缩小面板间距、统一字体和边框；用已有 CSV/JSON 运行 `conda run -n uu python refresh_visuals_from_existing_outputs.py` 重新导出图，不重跑实验数值。
- 修改两套 LaTeX 模板：取消图 11/12/13/16 的 `[H]` 强制固定，改为 `[!htbp]`；压缩图 7/8/9/11/12/13/16 的插入高度，避免热图连续占页或单图过大。
- 在 GEBCO/TID 方法边界段补充说明：可以从 bathymetry 派生 slope、local relief、curvature、swath-risk、source-confidence 等规划/审计层，但不能伪造官方 TID/source fractions；缺失官方 provenance 时必须标注为 derived planning products。
- 做了一轮保守去 AI 味润色：替换 `novelty lies`、`For readability`、`The next transfer step is clear`、`specific by design` 等僵硬/模板化表达，不改变数值、引用或证据结构。
- 完成结构完整性审计：当前稿保留 6 个主 section、16 张 figure、13 张 table；比 HEAD 版本新增 Structured prior-error、Threshold/local-failure 等诊断小节，没有发现关键内容被误删。
- 最终重编两套模板：`compile_after_user_visual_ai_v10_20260514_pass2.log` 均输出 42 pages；严格日志扫描无 LaTeX Error、Undefined control sequence、undefined citation/reference、Float too large、Overfull、Fatal/Emergency stop。
- 生成最终页面预览 `audit/page_preview_20260514_final_visual_v10/contact_sheet.png`，确认图 4、7、8、9、11、12、13、16 在最终 PDF 中布局正常：图 4 不单独占页，图 7/8 同页，图 11/12 同页，图 13 与图 16 均为正常论文比例。
- 最终交付 PDF 已更新到 2026-05-14 20:10：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`；摘要约 191 words，manifest 仍为 233 entries。
- 根据用户继续反馈，对 Fig. 8/11/12/13/15/16 做第二轮 SCI-style heatmap polish：参考 Matplotlib/Seaborn/ColorBrewer 的热图建议，统一为感知清晰的低饱和顺序/发散色带、白底 RGB、细网格、标题加粗、列标签半粗、单元格数字正常字重，风险单元仅用细边框和半粗数字提示。
- 修改 `journal_heatmap_style.py`、`make_journal_figures.py`、`make_structured_prior_error_replay.py`、`make_uncertainty_replay.py`、`make_uncertainty_margin_replay.py`、`make_coarse_prior_replay.py`、`make_threshold_local_failure_extension.py`，并用已有 CSV/JSON 重绘，不重跑实验数值。
- 发现 `refresh_visuals_from_existing_outputs.py` 不包含 Fig. 15，因此额外从 `threshold_local_failure_extension/threshold_local_failure_summary.csv` 单独刷新 `journal_threshold_local_failure.png`；新版 Fig. 15 已移除色条，避免色条占版面和压缩热图。
- 生成热图 contact sheet：`audit/heatmap_current_contact_20260514_v11_final.png`，确认六组热图均为白底、无色条遮挡、无长方形挤压、文字层级一致。
- 重新编译两套 LaTeX：`compile_after_heatmap_polish_v11_20260514_pass2.log` 均输出 42 pages；严格日志扫描无 LaTeX Error、Undefined control sequence、undefined citation/reference、Float too large、Overfull、Fatal/Emergency stop。
- 生成页面预览：`audit/page_preview_20260514_heatmap_polish_v11/contact_sheet.png` 和 `audit/page_preview_20260514_heatmap_polish_v11/threshold_contact.png`；确认 Fig. 8/11/12/13/15/16 在最终 PDF 中无压图、无覆盖、无异常空白页。
- 重新复制交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`；重新运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 仍为 233 entries。
- 按用户进一步反馈移除热图内部黑白框线：`journal_heatmap_style.py` 和 Fig. 8/11/12/13/15/16 相关绘图脚本已统一为白底、连续色块、无内部网格线、无粗风险矩形的 MATLAB/engineering-paper-like 热图样式。
- 刷新现有 CSV/JSON 对应热图，不重跑实验数值；最新热图总览为 `audit/heatmap_current_contact_20260514_v12_nogrid_tight.png`。
- 修复参考文献与数据产品链接：GEBCO TID URL 从失效页面改为 `https://www.gebco.net/gebco-tid-grid`；`yan2024dual`、`xie2024three`、`han2023hybrid`、`tang2023coverage` 已去掉 `et al.` 并按 DOI 元数据修正作者/卷期/页码。
- 重新编译两套 LaTeX：`compile_after_nogrid_refcheck_v12_20260514_pass2.log` 均输出 42 pages；严格日志扫描无 LaTeX Error、Undefined control sequence、undefined citation/reference、Float too large、Overfull、Fatal/Emergency stop。
- 复制最新交付 PDF 到 `mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`，时间戳为 2026-05-14 21:28 CST。
- 重新生成 PDF 页面预览：`audit/page_preview_20260514_nogrid_heatmap_refcheck_v12/heatmap_pdf_pages_contact_20260514_v12.png`；抽查第 22、29、32、33 页确认 Fig. 8/13/15/16 无内部框线、无色条覆盖、无异常空白页。
- 更新引用审计脚本 `audit/verify_references_20260514.py`，增加 DOI.org fallback；最新输出为 `audit/reference_verification_20260514_v2.md` 和 `.json`，42 条参考文献中 `et al.` 为 0，数据产品 DOI 可解析，剩余自动失败为网络/站点策略问题。
- 重新运行 `conda run -n uu python make_reproducibility_manifest.py`，`reproducibility_manifest.json` 更新为 235 entries。
- 更新 `submission_package/final_submission_checklist.md` 与 `/Users/Apple/Developer/Pycharm/q/Geo修改请按点核对.md`，在最新状态段明确当前为 42 页、235 entries、v12 no-grid/reference-cleanup 状态；较早 43/44 页和 233 entries 记录仅作为历史迭代记录保留。
- 按用户 2026-05-14 夜间图表反馈完成 v13 尺寸/字体/配色返修：图 2 在 LaTeX 中改为满宽展示；图 5 和图 10 在 LaTeX 中从 0.76\textwidth 放大到 0.96\textwidth；图 3/4 路线图只放大内部 panel 标签、比例尺和 summary strip 字体，不改数据、线型或方法颜色。
- 将 `make_vehicle_aware_posteval.py` 从 serif 改为 Helvetica/Arial/DejaVu Sans 统一 sans-serif，并改为白底 RGB PNG 输出，避免透明通道问题。
- 将 Fig. 8/11/12/13/15/16 热图色带统一为更接近期刊图表的色盲友好蓝色 sequential、蓝/暖色 diverging 和暖色 risk palette；不改热图数值和结构。
- 重编两套 LaTeX：`compile_after_user_figsize_palette_v13_20260514_pass2.log` 均输出 42 pages；严格日志扫描无 LaTeX Error、Undefined control sequence、undefined citation/reference、Float too large、Overfull、Fatal/Emergency stop。
- 生成最终页面预览：`audit/page_preview_20260514_user_figsize_palette_v13/contact_fig2_5_10_after_v13.png`，并抽查第 17/18/20/25/28/29/30/31/32/33 页，未见空白页、色条覆盖、热图内部框线、透明黑底或图片异常拉伸。
- 继续按用户要求完成 v14 图件校对返修：图 2 删除 LaTeX 高度限制，真正按 `\textwidth` 铺满；图 5 改为 `\textwidth` + 更高上限；图 10 通过更高画布和 `\textwidth` 显示放大，但不改变柱状图数据或语义。
- 修改 `make_journal_figures.py`：放大 Fig. 3/4 的 panel 标签、比例尺、summary strip、表格数字和图内说明；Fig. 8 改为方形单元热图，避免被 `aspect=auto` 拉成长条。
- 修改 `make_vehicle_aware_posteval.py`：继续统一 sans-serif 字体、放大关键标注，并移除 panel (c) 的内部白色网格线，使其与其它无网格热图一致。
- 重编两套 LaTeX：`compile_after_user_figsize_palette_v14_20260514_pass2.log` 均输出 42 pages；严格日志扫描无 LaTeX Error、Undefined control sequence、undefined citation/reference、Float too large、Overfull、Fatal/Emergency stop。
- 生成新版页面预览：`audit/page_preview_20260514_user_figsize_palette_v14/contact_figures_after_v14.png`，抽查第 17/18/20/22/25/28/29/30/32/33 页，确认图 2/3/4/5/8/10 和主要热图无空白页、无色条覆盖、无内部黑白框线、无透明黑底。
- 已同步交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`；重新运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 保持 235 entries。

## 2026-05-15

- 读取并核对 `/Users/Apple/Developer/Pycharm/q/Geo修改请按点核对.md`、`task_plan.md`、`progress.md`、`findings.md`、两套 LaTeX 模板和最终投稿清单。
- 确认老师意见中的 Simple Greedy baseline、GA 降调、swath clipping/denominator 保护、GEBCO TID audit、AI 使用声明和图件 v14 状态已经在正文中闭环。
- 发现摘要仍为实测 213 words，略高于 JMSE 约 200 words 安全线；将两套 LaTeX 摘要同步压缩到实测 197 words。
- 重新编译 `manuscript/mdpi_jmse/template.tex` 与 `manuscript/latex/template.tex` 两遍，输出日志 `compile_after_teacher_checklist_v15_20260515_pass1.log` 和 `compile_after_teacher_checklist_v15_20260515_pass2.log`。
- 严格扫描最新 pass2 日志：无 LaTeX hard error、undefined citation/reference、Float too large、Overfull、Fatal error、Emergency stop；两套 PDF 均输出 42 pages。
- 更新 `/Users/Apple/Developer/Pycharm/q/Geo修改请按点核对.md`，新增 v15 点对点闭环核对表，明确每条老师意见的处理状态、证据位置和辩证保留边界。
- 更新 `submission_package/final_submission_checklist.md`、`task_plan.md`、`progress.md` 与 `findings.md`，记录 v15 收口状态。
- 按用户 5 条要求继续做 v16 复核：再次扫描 GA/overlap 相关措辞，将残留的 “Hybrid GA repairs/reduces/suppresses” 风险表述改为 reported hybrid layout、terrain-aware spacing、optional local cleanup、repeatability check 等低风险表达。
- 在 swath model 段补明 transducer draft/sonar-head offset 近似：公共栅格不含 draft、sonar-head offset、tide、heave，benchmark 将 draft 置零/吸收到 \(D_0\)，真实部署应以 \(D_0-z_T\) 并经 tide/heave 修正后再应用同一 evaluator 和 clipping rules。
- 重新编译两套模板：`compile_after_user_5point_v16_20260515_pass2.log` 均输出 42 pages；严格扫描仍无 LaTeX hard error、undefined citation/reference、Float too large、Overfull、Fatal error、Emergency stop。
- 重新运行引用审计 `audit/verify_references_20260514.py`，输出 `total 42 failed 0 et_al 0`。
- 重新渲染关键页面并生成视觉 QA contact sheet：`audit/page_preview_20260515_user_5point_v16/contact_sheet.png`；抽查封面、图 2/3/4/5/8/10/11/12/13/15/16 与 references 页，无明显空白页、热图遮挡、黑底透明层或压缩拉伸。
- 重新运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 保持 235 entries。
- 按用户对 Fig. 2、Fig. 6、Fig. 14 的最新反馈完成 v17 专项返修：`make_journal_figures.py` 已将 Fig. 2 右上说明卡片改为 `(c) Evidence roles` 并手动换行最后说明，避免英文越框；`make_failure_mode_figure.py` 修正输出目录到 `manuscript/latex/pic` 与 `manuscript/mdpi_jmse/pic`，并将图内字体统一为 Helvetica/Arial/DejaVu Sans；`make_survey_grade_extension.py` 改为白底 RGB 输出、去除底部指标矩阵内部白网格、扩大画布。
- 重新运行 `conda run -n uu python make_journal_figures.py`、`conda run -n uu python make_failure_mode_figure.py`、`conda run -n uu python make_survey_grade_extension.py --seed-count 20`，确认 Fig. 2、Fig. 6、Fig. 14 已写入两套 manuscript 图片目录，关键 PNG 均为 RGB。
- 同步两套 LaTeX：Fig. 6 caption 明确单一渐变比例尺只服务底排 (d)--(f) 连续 excess-overlap panels；Fig. 14 `includegraphics` 高度上限放宽到 `0.50\textheight`；正文将残留强修辞降调为更审稿友好的边界表述。
- 重新编译 `manuscript/mdpi_jmse/template.tex` 与 `manuscript/latex/template.tex` 两遍，最终日志为 `compile_after_user_figtext_v17b_20260515_pass2.log`；两套 PDF 均输出 43 pages，严格扫描仅命中正常 `Output written`。
- 渲染关键页 17/21/32 并生成视觉 QA：`audit/page_preview_20260515_v17b_after/contact_sheet.png`。抽查确认 Fig. 2 无英文越框，Fig. 6 只有底排共享连续色条且无色条覆盖，Fig. 14 版式放大后无压缩、无透明黑底、无内部白网格。
- 重新运行引用审计 `python3 audit/verify_references_20260514.py`，结果为 `total 42 failed 0 et_al 0`；正文结构仍为 16 figures、13 tables、42 unique citation keys。
- 已复制最新交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`；重新运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 保持 235 entries。

## 2026-05-16

- 读取并核对 `/Users/Apple/Developer/Pycharm/q/Geo修改请按点核对.md`、`task_plan.md`、`progress.md`、`findings.md`、README、`CITATION.cff`、`.zenodo.json`、cover letter 和两套 LaTeX 模板。
- 按老师最新投前小修意见完成 v18 投稿边界补丁：在两套 LaTeX 的 swath clipping 段后补明 \(W_{\max}=1800\) m 是 declared benchmark range cap，不是 unconstrained sonar-range claim；在 Discussion 的 sensitivity boundary 中加入 transfer 前需评估 swath-width cap sensitivity 的限制句。
- 将 Data Availability 同步改为同时包含 Zenodo concept DOI `https://doi.org/10.5281/zenodo.19919505` 和初始固定版本 DOI `https://doi.org/10.5281/zenodo.19919506`，并说明如果后续 mint final frozen release，应在正式投稿前替换为最终版本 DOI。
- 用 `curl -L -I https://doi.org/10.5281/zenodo.19919506` 验证初始版本 DOI 可解析到 Zenodo record `19919506`。
- 将 README、`CITATION.cff`、`.zenodo.json` 和 `submission_package/JMSE_cover_letter_draft.md` 从 AUV-assisted/AUV survey planner framing 降调为 depth-referenced MBES fixed-line planning benchmark；README、Data Availability 和 cover letter 均说明 `geo-auv-bathymetry-benchmark` 是 historical repository name。
- cover letter 已改为更保守版本：不再写 “GA refinement mainly suppresses residual overlap”，改为 terrain-aware spacing 解释主要 public-scene route benefit，GA 是 local refinement and seed-repeatability check；同时明确不声称 hydrographic-quality assurance、sea-trial validation、mission-log replay 或 altitude-controlled AUV execution。
- 风险词扫描确认：`AUV-assisted`、`Terrain-Aware AUV Survey-Line`、`GA suppresses residual overlap`、`field-ready` 等误导性正向措辞已从正文/元数据/cover letter 中清除；剩余 `hydrographic-quality`、`field-readiness` 命中均为否定边界句。
- 重新编译 `manuscript/mdpi_jmse/template.tex` 与 `manuscript/latex/template.tex` 两遍；最终日志为 `compile_after_submission_patch_v18_20260516_pass2.log`，两套 PDF 均输出 43 pages。
- 严格日志扫描只命中正常 `Output written on template.pdf (43 pages)`；无 LaTeX Error、Undefined control sequence、undefined citation/reference、Rerun warning、Overfull、Float too large、Fatal error 或 Emergency stop。
- 重新运行引用审计 `python3 audit/verify_references_20260514.py`，结果仍为 `total 42 failed 0 et_al 0`。
- 已复制最新交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`；重新运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 保持 235 entries。

## 2026-05-17

- 读取并核对 `/Users/Apple/Developer/Pycharm/q/Geo修改请按点核对.md`、`task_plan.md`、`progress.md`、`findings.md`、两套 LaTeX、README 和投稿清单，确认本轮需要解决老师提出的 A 类投前风险：\(W_{\max}\) 敏感性、GA gate/practical significance、Methods 中 AI 披露、Data Availability 条件占位语、复现结构。
- 新增 `make_submission_boundary_diagnostics.py`，使用 `conda run -n uu python make_submission_boundary_diagnostics.py --seed-count 20` 在本地 `uu` 环境跑通，无需服务器。
- 新增输出目录 `submission_boundary_diagnostics/`：`wmax_sensitivity_raw.csv`、`wmax_sensitivity_summary.csv`、`ga_gate_practical_significance_raw.csv`、`ga_gate_practical_significance.csv`、`submission_boundary_diagnostics_summary.json` 和 `README.md`。
- 诊断结果：GEBCO 两景在 \(W_{\max}=1200/1800/2400\) m 下 Hybrid GA 均保持默认 \(C97/O3\) 可行，但绝对路径长度和线数大幅变化；USGS High 在 2400 m cap 下因 6.391% mean excess overlap 不可行，形成明确负边界。
- 诊断结果：GEBCO raw Hybrid GA 相对 Adaptive Spacing 的 median path gain 低于 0.001%，score-better 仅 2/20；USGS High median path gain 为 1.3684%，median overlap delta 为 -0.5157 pp，但 gate accepted 仅 6/20。
- 两套 LaTeX 同步新增 Methods 中 AI-assisted tools disclosure，并将 Acknowledgments 收紧为只感谢 GEBCO；Data Availability 删除 “If a later frozen submission release...” 条件式占位语。
- 两套 LaTeX 同步新增 Table `tab:ga_gate_practical` 和 Table `tab:wmax_sensitivity`，并在 Discussion、Conclusion、risk matrix、Supplementary/Reproducibility Evidence 中写入相应边界解释。
- 新增 `README_submission.md`，记录 Conda `uu` 环境、核心复现命令、submission-boundary diagnostics 和 claim boundary。
- 更新 README 与 cover letter：不再出现 future frozen DOI 条件占位语，继续保持 depth-referenced MBES fixed-line benchmark framing。
- 修改 `make_reproducibility_manifest.py`，将 `submission_boundary_diagnostics/`、`README_submission.md`、`make_submission_boundary_diagnostics.py` 纳入 manifest 范围；重新运行后 manifest 为 243 entries。
- 重新编译 `manuscript/mdpi_jmse` 与 `manuscript/latex` 两遍，最终日志为 `compile_after_submission_boundary_v19_20260517_pass2.log`；两套 PDF 均输出 44 pages。
- 严格日志扫描只命中正常 `Output written on template.pdf (44 pages)`；无 LaTeX Error、Undefined control sequence、undefined citation/reference、Rerun warning、Overfull、Float too large、Fatal error 或 Emergency stop。
- 重新运行引用审计 `python3 audit/verify_references_20260514.py`，结果仍为 `total 42 failed 0 et_al 0`。
- 渲染新增表格页并抽查：`audit/page_preview_20260517_v19/page_01.png`、`page_02.png`、`page_03.png`；Table 12 和 Table 14 无越界、遮挡、异常空白页或明显压缩。
- 已复制最新交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`，时间戳为 2026-05-17。

## 2026-05-22

- 读取并核对 `/Users/Apple/Developer/Pycharm/q/Geo修改请按点核对.md`、`task_plan.md`、`progress.md`、`findings.md`、两套 LaTeX、当前实验 CSV/JSON 和已有 v19 交付状态，确认本轮优先回应 P11 航向分辨率、P7 主公共场景太少、P9 统计显著性不足。
- 新增 `make_heading_resolution_diagnostic.py`，使用现有 `geo_public_bathy_benchmark.py` evaluator 和 `make_threshold_local_failure_extension.py` scene loader，在 `uu` 环境运行 `conda run -n uu python make_heading_resolution_diagnostic.py --scenes all`。
- 新增输出目录 `heading_resolution_diagnostic/`：`heading_resolution_raw.csv`、`heading_resolution_summary.csv`、`heading_resolution_summary.json`、`journal_heading_resolution_diagnostic.png`，并同步 PNG 到两套 manuscript 图片目录。
- 航向分辨率结果：Adaptive Spacing 在 GEBCO Cascadia、GEBCO Monterey 和 USGS High 上，\(5^{\circ}\) 与 \(15^{\circ}\) 的 selected heading、line count、path length、coverage、overlap 完全一致；Simple Greedy 仅 Cascadia 从 \(75^{\circ}\) 改为 \(95^{\circ}\)，路径缩短 0.123% 但 overlap 增加 0.084 pp，仍保持可行。
- 新增 `make_public_window_statistics.py`，从已有 `run_5/benchmark_method_statistics.csv`、`gebco_scene_expansion/gebco_scene_expansion_summary.csv`、`survey_grade_extension_usgs_cascadia/benchmark_method_statistics.csv` 复算九个 public windows 的 paired deltas、bootstrap CI、Wilcoxon signed-rank 和 rank-biserial effect size。
- 新增输出目录 `public_window_statistics/`：`public_window_paired_deltas.csv`、`public_window_statistics_summary.csv`、`public_window_statistics_summary.json`、`journal_public_window_statistics.png`，并同步 PNG 到两套 manuscript 图片目录。
- 九窗口统计结果：Adaptive Spacing 和 Hybrid GA 均为 9/9 feasible public windows；两者 overlap cleanup 均为 9/9 正向，one-sided Wilcoxon \(p=0.00195\)，rank-biserial 1.00；路径收益均为 7/9 正向，one-sided Wilcoxon \(p=0.00977\)，median path gain 0.681%。
- 两套 LaTeX 同步写回：Methods 增加 \(5^{\circ}\) heading-resolution audit 解释；Sensitivity 表新增 Heading resolution 行；Results 新增 Table `tab:public_window_stats`；Discussion/Conclusion/Data Availability 同步加入 heading-resolution 和 public-window paired-statistics 证据边界。
- 重新编译 `manuscript/mdpi_jmse` 与 `manuscript/latex` 两遍，最终日志为 `compile_after_public_window_stats_20260522_pass2.log`；两套 PDF 均输出 45 pages，严格扫描无 LaTeX Error、Undefined control sequence、undefined citation/reference、Rerun、Overfull、Float too large、Fatal 或 Emergency stop。
- 使用 PyMuPDF 抽查 PDF：Table `tab:public_window_stats` 位于第 21 页，Heading resolution 行位于第 28 页；已渲染页面预览到 `audit/page_preview_20260522_heading_public_stats/page_21.png` 至 `page_24.png`，表格文字可读且未截断。
- 更新 `make_reproducibility_manifest.py`，将 `heading_resolution_diagnostic/`、`public_window_statistics/`、两个新脚本和对应 manuscript PNG 纳入 manifest；运行 `conda run -n uu python make_reproducibility_manifest.py` 后 manifest 为 257 entries。
- 重新运行引用审计 `python audit/verify_references_20260514.py`，结果为 42 references、0 `et_al`；唯一 automated failed 为 `xie2024three` 的 DOI HTTP 403。已用 MDPI 官方页面人工核验 `10.3390/jmse12081366` 真实存在，元数据与稿件一致。
- 已复制最新交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`，时间戳为 2026-05-22。
- 2026-05-22 v21 继续按老师大修清单推进：重绘 Figure 1 的 LaTeX/TikZ 流程图，保留小圆节点、细箭头和三段括号式逻辑，移除任何厚矩形外框/幻灯片式卡片感；修复 `make_method_pipeline_figure.py` 指向旧 `latex/pic` 的路径问题，改为同步生成到 `manuscript/latex/pic` 和 `manuscript/mdpi_jmse/pic`。
- 新增 `make_ga_surrogate_audit.py`，运行 `conda run -n uu python make_ga_surrogate_audit.py --scenes all --seeds 12 --candidates-per-seed 12`，输出 `ga_surrogate_audit/ga_surrogate_raw.csv`、`ga_surrogate_summary.csv`、`ga_surrogate_summary.json` 和 `journal_ga_surrogate_audit.png`，并同步 PNG 到两套 manuscript 图片目录。
- GA surrogate audit 结果：每个场景 144 个本地候选；GEBCO Cascadia/Monterey/USGS High 的 stride-3 vs full-grid GA-fitness Spearman 相关分别为 0.934/0.968/0.989，Kendall tau 为 0.804/0.855/0.920，top-10 overlap 为 0.80/0.70/0.80，best-stride full-grid regret 为 0.0008/0.0028/0.0610%。三者 stride-selected candidate 在 full-grid 上均仍满足 C97/O3。
- 两套 LaTeX 同步写回：Methods 增加 stride-3 surrogate audit 说明；Results 新增 Table `tab:ga_surrogate_audit`；Discussion 补明 surrogate-evaluator agreement、full-grid rescoring 和 GA gate 是对 P12 的 safeguards；Data Availability 增加 GA surrogate-audit CSV/JSON/PNG 文件。
- 运行 `conda run -n uu python make_reproducibility_manifest.py`，manifest 更新为 264 entries，已纳入 `ga_surrogate_audit/` 和 `make_ga_surrogate_audit.py`。
- 重新编译 `manuscript/mdpi_jmse` 与 `manuscript/latex` 两遍，最终日志为 `compile_after_surrogate_fig1_v21_20260522_pass2.log`；两套 PDF 均输出 46 pages。严格扫描无 LaTeX Error、Undefined control sequence、undefined citation/reference、Rerun、Overfull、Float too large、Fatal 或 Emergency stop。
- 更新交付 PDF：`mdpi_jmse_jmse_submission_draft.pdf`、`paper_refined.pdf`、`geo_public_bathy_rebuild.pdf`。
- PDF 视觉 QA：渲染 `audit/page_preview_20260522_surrogate_fig1_v21/page_05.png`、`page_27.png`、`page_28.png`、`page_29.png`。人工检查 Figure 1 无文字溢出/厚框，Table 14 无截断、遮挡、异常空白或压缩。
- 重新运行引用审计 `python audit/verify_references_20260514.py`，结果为 42 references、0 et_al、4 automated DOI failures。失败项为 DOI.org/出版商访问策略或 SSL EOF：`shi2020data`、`jiang2018route`、`li2024full`、`ji2022multi`；本轮未改参考文献，且这些条目已通过出版商/检索结果人工核验为真实存在，属于网络解析失败而非假文献。
