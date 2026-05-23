# Geo Hard Evidence Extension Plan

## 目标
对 Geo/MBES 稿件做一轮证据型硬补，重点回应老师和审稿人可能追问的三类问题：严格阈值下是否仍成立、平均覆盖/重叠是否隐藏局部失败、USGS 高复杂度证据是否真正支撑主张。

## 阶段

- [x] 阶段 1：恢复上下文，确认当前 manuscript、PDF、实验文件状态。
- [x] 阶段 2：实现阈值敏感性与局部失败诊断脚本。
- [x] 阶段 3：运行诊断并生成 CSV/JSON/PNG 证据。
- [x] 阶段 4：把新增证据回写到 LaTeX 正文、结论、审计文件和老师意见核对 MD。
- [x] 阶段 5：重新编译 `manuscript/mdpi_jmse` 与 `manuscript/latex`，复制交付 PDF。
- [x] 阶段 6：最终复核，给出 SCI/JMSE 投稿状态判断与下一步补强建议。

## 当前决策

- 不把 depth-referenced 结果强行改口为真实低空 AUV altitude-aware 结果。
- 本轮补实验优先使用现有规划函数重建代表性布局，不盲目重跑大规模服务器实验。
- 新证据以紧凑表格和诊断图为主，避免继续堆大面积热图导致版式失控。
- 图 15 已改为白底 RGB PNG、无 alpha 通道，避免 PDF/渲染器透明通道黑块问题。
- 当前可交付 PDF 均为 43 页；严格日志扫描无 LaTeX hard error、undefined citation/reference、overfull 或 float-too-large 命中。
- 2026-05-14 老师二轮意见已点对点硬补：摘要压到实测 197 words，Table 7 纳入 Simple Greedy/best-heading constant-spacing baseline，GA 贡献降调为 local repeatability/refinement，swath clipping/denominator 保护写明，新增 GEBCO TID 审计表。
- 新增 TID 表后当前可交付 PDF 均为 44 页；最终严格日志扫描无 LaTeX hard error、undefined citation/reference、overfull 或 float-too-large 命中。
- 2026-05-14 晚间最终视觉返修已完成：图 9 重排为期刊主图式机制图，图 11/12/13/16 统一 compact heatmap 样式，图 7/8/9/11/12/13/16 的 LaTeX 尺寸和浮动策略已收紧。
- 当前可交付 PDF 均为 42 页；页数降低来自图表压缩和浮动优化，不是正文删除。结构审计显示 16 figures、13 tables、主要新增诊断小节均保留。
- 当前最终日志为 `compile_after_user_visual_ai_v10_20260514_pass2.log`；严格扫描无 LaTeX hard error、undefined citation/reference、overfull 或 float-too-large。
- 2026-05-14 热图二轮 polish 已完成：Fig. 8/11/12/13/15/16 统一为白底低饱和矩阵热图，Fig. 15 已移除色条并并入同一视觉系统。
- 上一阶段最终日志为 `compile_after_heatmap_polish_v11_20260514_pass2.log`；两套 PDF 为 42 页，严格扫描无 LaTeX hard error、undefined citation/reference、overfull 或 float-too-large。
- 2026-05-14 no-grid/reference-cleanup 收口已完成：Fig. 8/11/12/13/15/16 移除内部网格线和粗风险矩形，GEBCO TID 链接改为当前官方页面，4 条 `et al.` 参考文献已修正，两套 PDF 仍为 42 页。
- 当前最终日志更新为 `compile_after_nogrid_refcheck_v12_20260514_pass2.log`；最新页面预览为 `audit/page_preview_20260514_nogrid_heatmap_refcheck_v12/heatmap_pdf_pages_contact_20260514_v12.png`。
- 最新引用审计为 `audit/reference_verification_20260514_v2.md`；最新 manifest 为 235 entries。
- 2026-05-14 v13 图表尺寸/字体/配色返修已完成：Fig. 2 满宽，Fig. 5/10 放大，Fig. 3/4 内部文字增强，Fig. 8/11/12/13/15/16 热图换为更克制的蓝/暖色期刊色带。当前最终日志为 `compile_after_user_figsize_palette_v13_20260514_pass2.log`。
- 2026-05-14 v14 图件返修已完成：Fig. 2 删除高度限制后真正满宽；Fig. 5/10 进一步放大；Fig. 3/4 小字增强；Fig. 8 改为方形单元；Fig. 5 panel (c) 移除内部网格线。当前最终日志为 `compile_after_user_figsize_palette_v14_20260514_pass2.log`，最新页面预览为 `audit/page_preview_20260514_user_figsize_palette_v14/contact_figures_after_v14.png`。
- 2026-05-15 v15 老师意见闭环已完成：摘要压缩到实测 197 words，两套 LaTeX 同步；点对点核对 MD 已补充完成/证据/辩证保留；两套 PDF 均为 42 页，最新日志为 `compile_after_teacher_checklist_v15_20260515_pass2.log`。
- 2026-05-15 v16 五点专项复核已完成：进一步压低 GA 过强归因措辞，补明 transducer draft/sonar-head offset 近似；Reference audit 为 42 references / 0 failed / 0 et_al；关键图页预览为 `audit/page_preview_20260515_user_5point_v16/contact_sheet.png`；两套 PDF 均为 42 页，最新日志为 `compile_after_user_5point_v16_20260515_pass2.log`。
- 2026-05-15 v17 图 2/6/14 专项返修已完成：Fig. 2 说明卡片改为不溢出的 Evidence roles，Fig. 6 修正输出路径并明确单一渐变比例尺只对应底排连续 excess-overlap 图，Fig. 14 以白底 RGB 重绘并放宽 LaTeX 高度上限。两套 PDF 均为 43 页，严格日志扫描无 LaTeX hard error、undefined citation/reference、Overfull、Float too large、Fatal/Emergency stop；最新页面预览为 `audit/page_preview_20260515_v17b_after/contact_sheet.png`。
- 2026-05-16 v18 投稿边界小补丁已完成：正文补明 \(W_{\max}=1800\) m 是 declared benchmark range cap，不是 sonar-range truth；Data Availability 加入 Zenodo concept DOI `10.5281/zenodo.19919505` 与初始固定版本 DOI `10.5281/zenodo.19919506`；README/CITATION/.zenodo/cover letter 改为 depth-referenced MBES fixed-line benchmark framing，并说明 repo 名称中的 AUV 是 historical naming。两套 PDF 均为 43 页，严格日志扫描无 hard error、undefined citation/reference、Overfull、Float too large、Fatal/Emergency stop；引用审计仍为 42 references / 0 failed / 0 et_al，manifest 为 235 entries。
- 2026-05-17 v19 投前 A 类硬补已完成：新增 `submission_boundary_diagnostics/`，跑通 \(W_{\max}=1200/1800/2400\) m 敏感性和 Adaptive-vs-Hybrid GA gate/practical-significance 诊断；正文新增 Table 12 和 Table 14，Methods 加入 AI-assisted tools disclosure，Data Availability 删除条件式 future-release 占位语；新增 `README_submission.md`。两套 PDF 均为 44 页，严格日志扫描无 hard error、undefined citation/reference、Overfull、Float too large、Fatal/Emergency stop；引用审计仍为 42 references / 0 failed / 0 et_al，manifest 为 243 entries。
- 2026-05-22 v20 老师大修清单继续硬补：新增 `heading_resolution_diagnostic/` 和 `public_window_statistics/`，回应 P11 航向分辨率、P7 外部效度、P9 统计不足。\(5^{\circ}\) 诊断显示 Adaptive Spacing 在 GEBCO Cascadia、GEBCO Monterey 和 USGS High 上与 \(15^{\circ}\) 主扫描完全一致；九窗口 paired audit 显示 Adaptive/Hybrid 均在 9/9 public windows 上改善 overlap，Wilcoxon \(p=0.00195\)，路径收益 7/9 为正，Wilcoxon \(p=0.00977\)。两套 PDF 均为 45 页，严格日志扫描无 hard error、undefined citation/reference、Overfull、Float too large、Fatal/Emergency stop；manifest 为 257 entries。
- 2026-05-22 v21 Figure 1 与 P12 surrogate 审稿风险继续硬补：Figure 1 重绘为 LaTeX/TikZ 小圆节点细箭头图；新增 `ga_surrogate_audit/`，验证 stride-3 GA fitness 与 full-grid rescoring 的本地排名一致性。三场景 Spearman 为 0.934/0.968/0.989，最大 full-grid regret 为 0.0610%。两套 PDF 均为 46 页，严格日志扫描无 hard error、undefined citation/reference、Overfull、Float too large、Fatal/Emergency stop；manifest 为 264 entries。
- 2026-05-23 v22 release-readiness 收紧进行中：新增 `check_release_readiness.py`，`make_reproducibility_manifest.py` 改为只纳入 Git-tracked artifact 并记录当前 Git revision；Data Availability 将 GEBCO TID 原始 GeoTIFF 再分发表述改为 TID 审计表、basket id 与检索元数据。下一步是精确 stage 正文承诺的证据目录、重跑 manifest/readiness、编译两套 PDF 并推送。
