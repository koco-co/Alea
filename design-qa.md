# Alea 端到端与视觉验证报告

日期：2026-07-21

## 验证口径

- 浏览器：Codex 内置 Browser；本轮不使用 Chrome。
- 服务：本地 Supabase、FastAPI、Next.js、Redis、Worker、Scheduler、Dispatcher。
- 账号：本地管理员 `admin@alea.local`。
- AI：DeepSeek API、Codex CLI。
- 视口：`1440 × 900`、`390 × 844`。
- 数据：Gate 0 人工 fixture；未授权前未访问 Sporttery Web Source。
- 参考：`docs/PrototypeDesign/visual-qa/production-pass/screenshots/020-admin-lineup-desktop-final.png`、`021-admin-lineup-mobile-final.png`、`037-predictions-worldcup-mobile-final.png`。

## 内置 Browser 步骤与结果

| #   | 操作                                   | 观察结果                                                                    | 状态           | 当前证据                                                                                        |
| --- | -------------------------------------- | --------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------- |
| 1   | 在内置 Browser 打开 `/login`，1440×900 | 登录页真实渲染，风险说明、输入标签和登录卡片均可见                          | 通过           | `docs/evidence/e2e-inapp-20260721/01-login-1440x900.png`                                        |
| 2   | 使用本地管理员完成邮箱登录             | 建立真实 Supabase 会话并进入 `/console/predictions`                         | 通过           | 内置 Browser URL 与 DOM snapshot                                                                |
| 3   | 打开 `/console/admin/lineup` API 标签  | 11 个 API 目录、DeepSeek 配置、掩码密钥、模型和实例来自真实后台             | 通过           | `27-lineup-final-1440x900.png`                                                                   |
| 4   | 点击 DeepSeek「测试连接」              | DeepSeek API 真实结构化测试返回 `测试通过 · 1183 ms`                        | 通过           | `05-deepseek-api-pass-1440x900.png`                                                             |
| 5   | 切换 CLI 标签                          | 11 个 CLI 目录、Codex 路径/版本/认证/模型/实例真实加载                      | 通过           | `04-lineup-cli-1440x900.png`                                                                    |
| 6   | 点击 Codex CLI「测试连接」             | Codex CLI 真实 `predict_score` Schema 测试返回 `测试通过 · 5494 ms`         | 通过           | `06-codex-cli-pass-1440x900.png`                                                                |
| 7   | 390×844 复核 API/CLI 阵容页            | API/CLI 内容可纵向浏览；管理员导航已改为原型风格浅色横向浮层                | 通过           | `08-lineup-api-390x844-fixed.png`、`09-lineup-cli-390x844.png`                                  |
| 8   | 1440×900 打开用户主导航                | `/console`、`/console/fixtures`、`/console/calculator` 均真实渲染，无空白页 | 通过           | `14-console-overview-1440x900.png`、`15-fixtures-1440x900.png`、`16-calculator-1440x900.png`    |
| 9   | 1440×900 打开管理流程                  | 数据同步显示未授权来源降级；圆桌配置页可操作                                | 通过（降级态） | `17-admin-sync-1440x900.png`、`18-admin-roundtable-1440x900.png`                                |
| 10  | 390×844 打开推演、总览、发起圆桌       | 三页可渲染；用户页改为原型风格底部导航，管理员页保持管理导航                | 通过           | `28-predictions-final-390x844.png`、`21-console-390x844.png`、`22-admin-roundtable-390x844.png` |
| 11  | 点击「发起圆桌」并进入直播页           | 前端显示“任务已创建”，但实际数据库任务/事件/审计均未写入                    | **失败**       | `25-roundtable-submit-result-1440x900.png`、`26-roundtable-live-1440x900.png`                   |

## 原型对照与本轮修复

并排对照文件：`docs/evidence/e2e-inapp-20260721/12-reference-vs-inapp-lineup.png`。

已确认并修复的差异：

1. 管理员桌面页原先左贴边并使用深色满高侧栏；现改为与 PrototypeDesign 一致的居中浅色卡片式管理工作台。
2. 管理员移动页原先是黑色横向侧栏；现改为浅色圆角浮层、保留编号、隐藏冗余副标题。
3. 移动用户页原先把完整主导航挤在顶部；现隐藏顶部模块导航，增加与原型一致的底部四项导航：总览、预测、赛程、算票。
4. 阵容页仍保留 API/CLI 两个一等标签、目录搜索、真实测试、实例限制和保存状态，没有退回静态演示。

## 数据与数据库证据

当前数据库中已启用并通过测试的连接为：

```text
codex   | cli | passed | enabled | 1 enabled instance
deepseek| api | passed | enabled | 1 enabled instance
```

本次点击圆桌提交后只产生前端固定展示：

```text
roundtable_jobs=0
roundtable_events=0
execution_audits=0
```

## 自动检查

本轮视觉 CSS/导航修复后需要重新执行 `make check`；上一轮基线检查为 API 229 通过 / 13 跳过、Web 36 通过、Ruff/Mypy/TypeScript/Prettier 通过、ESLint 0 错误（29 个既有 `<img>` 警告）。本报告不把上一轮结果冒充为本轮修复后的最终检查。

## 未通过与未验证范围

- `[P0]` `/console/admin/roundtable` 仍使用 `INSTANCES`、固定任务编号和 `window.setTimeout`；未读取已验证的 DeepSeek/Codex 连接，也未调用真实 roundtable command。
- `[P0]` 圆桌直播页仍使用硬编码 OpenAI/Anthropic/Google 状态；0 条持久事件，九阶段、公证、发布、采用与结算主链未通过。
- `[P0]` `/console/predictions` 仍显示“当前只有一个真实 Provider”，与数据库实际启用的 DeepSeek API + Codex CLI 不一致。
- `[P1]` 视觉对照仍存在内容语义差异：原型展示固定演示结果，实际页按数据边界展示 no-quorum；这部分应由真实圆桌链路补齐，不应伪造结果。
- 本轮未把比赛详情五 Tab、发布/撤回、账本结算、排行认定、备份恢复演练认定为通过。

最终结果：**partial**。内置 Browser 的登录、关键路由、API/CLI AI 验证、桌面/移动视觉修复和数据源降级态通过；圆桌到结算的真实后端链路仍被静态实现阻断。
