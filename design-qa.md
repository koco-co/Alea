# Alea Next.js 前端设计 QA

日期：2026-07-20

## Source of truth

- 产品行为：`docs/产品需求文档.md` §6–§14
- 视觉系统：`DESIGN.md`，主背景 `#FAF9F5`、强调色 `#CC785C`
- OpenDesign 原型：`docs/PrototypeDesign/open-design/alea.html`、`alea-predictions.html`、`alea-console.html`、`alea-calculator.html`
- 同视口参考截图：
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/marketing-1440x900.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/marketing-390x844.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/predictions-today-1440x900.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/predictions-today-390x844.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/console-fixtures-1440x900.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/console-fixtures-390x844.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/console-fixture-detail-1440x900.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/console-fixture-detail-390x844.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/calculator-fact-1440x900.png`
  - `docs/PrototypeDesign/open-design/qa/final-production-audit-20260719/after/calculator-fact-390x844.png`

## Implementation targets

- `/`
- `/console/predictions`
- `/console/predictions/match-104`
- `/console/fixtures`
- `/console/fixtures/104`
- `/console/calculator`

Acceptance viewports: `1440 × 900` and `390 × 844`.

## Automated evidence

- TypeScript (`tsc --noEmit`)：通过，退出码 0。
- Web tests (`bun test`)：25 通过 / 0 失败，退出码 0。
- Next.js 生产构建（Webpack）：通过，退出码 0。
- 静态资源引用：通过；全部 `/assets/*` 引用均存在于 `web/public/`。
- 服务器静态渲染 HTML：`docs/evidence/frontend-visual-20260720/`。该证据只检查结构与样式注入，不替代浏览器截图和交互验证。

## Full-view comparison

状态：阻断。执行环境对本地监听端口返回 `EPERM`；已选浏览器的安全策略同时禁止打开 `file://` 证据。未生成任何 Next.js 实现截图，因此没有用 OpenDesign 旧截图或静态 HTML 冒充同视口对比。

## Focused comparison

状态：阻断。以下重点尚未获得实现截图：首屏动画密度与裁切、推演卡四层层级、详情五 Tab、计算器三栏与移动三步、票面 Canvas 输出。

## Findings

- `[P0]` 全部目标路由：缺少 Next.js 实现的 1440×900 与 390×844 新鲜渲染证据。影响：无法接受性判断溢出、折行、粘性元素、焦点、动画、图像裁切和响应式重排。修复：在允许本地 loopback 监听的环境启动 `web`，逐路由截图，与同视口参考并排检查后再修正。
- `[P1]` `/console/calculator`：复制、PNG 下载与移动三步依赖真实浏览器 API，尚未执行。修复：分别在桌面与移动完成选择、配置、预览、复制和下载流程，打开 PNG 检查品牌图与声明区。
- `[P1]` `/console/fixtures/[id]`：五 Tab、缺失态与返回路径尚未执行。修复：逐 Tab 记录操作、结果、截图与剩余边界。
- `[P1]` `/console/predictions/[id]`：辩论回放时间线与投票行 hover / focus 尚未执行。修复：键盘与指针分别验证并记录。

## Unverified remainder

1. 营销页动画启停、锚点导航、CTA 与 reduced-motion。
2. 推演卡投票行 tooltip / focus、详情导航、辩论回放。
3. 赛程筛选组合、重置、空态、比赛详情五 Tab 与恢复路径。
4. 计算器事实 / 样例切换、玩法与倍数、移动三步、复制、PNG 下载。
5. 两个验收视口的页面级横向溢出、折行、裁切、控制台错误和资源加载。

final result: blocked
