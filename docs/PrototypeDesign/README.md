# Alea 原型设计迁移包

本目录是从 OpenDesign 内部项目目录迁出的可版本化工作副本，用于在另一台电脑继续执行生产级原型 Goal。

## 目录

- `open-design/`：可直接运行或导入 OpenDesign 的 HTML/CSS/JS、资产、页面元数据与既有 QA 截图。
- `reference-assets/`：品牌原图、世界杯决赛主视觉和西班牙/阿根廷旗帜源文件。
- `visual-qa/production-pass/`：路线/状态矩阵、资产台账、审计记录、研究资料和本轮截图证据。
- `PROTOTYPE_PRODUCTION_GOAL.md`：新电脑继续执行时的完整 Goal。

OpenDesign 内部生成的 `.file-versions/` 和 `.tmp/` 没有迁入：它们是设备相关的版本缓存与临时截图，不是运行原型所需输入。项目使用的 `.od-skills/` 已保留在 `open-design/`。

## 新电脑继续执行

1. 拉取仓库并完整读取 `AGENTS.md`、`docs/PrototypeDesign/PROTOTYPE_PRODUCTION_GOAL.md`、`docs/产品需求文档.md` 和 `DESIGN.md`。
2. 在 OpenDesign 中将 `docs/PrototypeDesign/open-design/` 作为 Web Prototype 项目目录打开。
3. 若只需本地预览，可在仓库根目录运行：

   ```bash
   python3 -m http.server 8767 --directory docs/PrototypeDesign/open-design
   ```

   然后访问 `http://127.0.0.1:8767/alea.html`。
4. 从 `visual-qa/production-pass/route-state-matrix.md` 中仍标记为“失败”或“未验收”的项目继续，不要把既有截图当作新电脑上的本轮验收证据。

## 当前交接边界

- 太玄问机和竞彩方案已完成 390×844 的世界杯决赛数据合同修复与实际点击验证；精确 1440×900 证据仍缺。
- 系统管理的发起推演与模型阵容已有既有证据；推演直播正在迁移为同一场 Match 104 数据合同，发布审核及终止归档仍需继续清理和验证。
- `alea-console.html` 的预测排行、盈亏账本、赛后复盘、内嵌竞彩方案和赛事资料仍存在无来源演示数据，必须按矩阵继续修复。
- 迁移包不是“生产就绪”声明；完成状态以路线/状态矩阵与新鲜双视口视觉证据为准。
