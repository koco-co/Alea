# Alea 发布阻塞复核报告（2026-07-22）

## 本轮范围

在 `fix/alea-full-hardening` 分支上完成修复包后续复核：真实 Docker 全栈、排行榜路由/API 投影、数据库迁移、备份恢复、Playwright E2E 与 Codex 内置 Browser 视觉检查。

## 已完成

- 新增 `20260722030000_rankings_projection.sql`，补齐 `/v1/rankings` 与模型档案查询的安全数据库契约；没有结算事实时只返回空投影。
- `/console/rankings` 与 `/console/rankings/[aiId]` 已接入真实会话、Next.js API 代理、FastAPI Gateway 和 `alea_api`，移除固定模型、比分、命中率和静态理由。
- 修复只读 GET API 代理误用 Origin 校验导致的浏览器 403；状态变更请求仍保留同源校验。
- 完成从空迁移库到人工 Gate 0 fixture 的分层恢复演练：Auth、Profile、来源、比赛、赔率恢复成功，G1/G2 真实数据库测试通过。
- 内置 Browser 已重新打开排行榜桌面与移动状态，并检查视觉截图；全部 17 个当前控制台/管理列表路由无 404、无加载卡死。`/console/rankings` 的正确状态为“暂无已结算的公证预测”。

## 验证命令与结果

| 命令 | 结果 |
|---|---|
| `python scripts/verify_hardening_contracts.py` | 通过 |
| `make test-hardening` | 12 passed |
| `bunx supabase@2.109.1 db reset --local --yes` | 通过，14 个迁移从空库顺序执行 |
| `bunx supabase@2.109.1 migration list --local` | 通过，最高 `20260722030000` |
| `cd api && UV_CACHE_DIR=../.uv-cache uv run --locked pytest` | 全量 API 测试通过 |
| `cd web && bun test src/lib/rankings-model.test.ts` | 2 passed |
| `cd web && bun run typecheck && bun run lint` | 通过；仅既有 `<img>` 优化警告 |
| `cd web && bun run build` | 通过，包含排行榜 API、列表和档案路由 |
| `ALEA_E2E_REAL=1 ... PLAYWRIGHT_BASE_URL=http://127.0.0.1 make test-e2e` | 20 passed |
| Docker `/readyz` | ready；database、migration、Redis、Supabase、Dispatcher、Worker、executor factory 全部 true |
| G1/G2 真实数据库测试 | 17 passed，0 failed，0 skipped |

## 数据与未完成边界

- Gate 0 只使用人工 fixture；未授权前未启用 Sporttery Web Source。
- `同步能力已完成，但历史数据未实际导入`。当前没有授权历史数据文件，未伪造世界杯或五大联赛数据。
- 当前数据库没有已结算的公证预测，因此排行榜只展示合法空态；这不是用假数据证明排行榜通过。
- 圆桌本地 provider 执行链已经通过预测、辩论、投票、共识、记账/公证到 `published_pending` 的既有验证，但赛后真实结果同步、正式发布公开投影、结算复盘和排行榜非空名次仍需授权赛事结果与完整业务 fixture 才能验收。
- 定时圆桌当前按 PRD 明确隐藏，后端拒绝未实现的 scheduled 任务，不展示不会被消费的入口。

## 视觉证据

- 桌面排行榜：`/tmp/alea-iab-rankings-desktop-20260722.png`
- 移动 emulation 检查：`/tmp/alea-iab-rankings-mobile-20260722.png`
- 用户与管理员路由扫描：`/tmp/alea-iab-route-*-20260722.png`

上述临时证据位于 Git 工作树外，不进入提交；正式归档时应将必要截图复制到 `docs/evidence/` 并纳入 manifest。
