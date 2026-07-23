# Alea 全量 AI 预测验收报告（2026-07-23）

## 结论

本轮完成了本地 Gate 0 fixture 范围内的真实前后端验收：API Provider、Codex CLI、DeepSeek API、Worker、Dispatcher、Redis、数据库事件链和管理台页面均已联通。最终圆桌任务完成到预测发布前状态，结果和审计证据已持久化。

这不是生产体彩数据验收。当前比赛来自人工整理的本地 fixture，界面明确显示“Fixture / 非生产数据”，未执行真实投注。

## 数据范围

- 导入日期：2026-07-24；竞彩编号 201–207，共 7 场。
- 导入内容：联赛、球队、开赛时间、人工截止时间、胜平负与让球赔率快照、来源记录和批次哈希。
- 导入方式：通过管理员 fixture 导入命令，具备幂等批次记录；未绕过来源资格函数直接写入生产事实。
- 历史数据：同步能力已完成，但历史数据未实际导入。没有在未取得授权数据文件的情况下伪造世界杯、五大联赛或俱乐部历史数据。

## 真实 AI 圆桌证据

最终任务：`929f1c7b-8d38-460e-8987-e033b94d5882`

- 参与实例：1 个 Codex CLI、2 个 DeepSeek API；覆盖 2 个 Provider 家族。
- 7 场均通过资格校验并进入 match run。
- 72/72 个 Provider phase succeeded，失败数为 0。
- 76 条圆桌事件连续持久化，序号无缺口；Outbox 已发布 73 条。
- 7 条预测结果完成公证，no_quorum 数为 0。
- 任务状态为 `completed`，同时记录 `roundtable.published_pending`；由于 7 场比赛尚未到销售截止时间，`public_notarized_predictions` 当前为 0，管理端展示的是冻结后的内部公证结果，停售后由投影任务公开。
- Provider receipt、模型输出、投票、共识、阶段耗时、重试和审计记录均留在数据库中。

## 执行门禁

| 命令 | 结果 |
| --- | --- |
| `python scripts/verify_hardening_contracts.py` | 通过 |
| `make test-hardening` | 17 passed |
| `bunx supabase@2.109.1 db reset --local --yes` | 通过，空库顺序迁移 |
| `bunx supabase@2.109.1 migration list --local` | 通过，21 个迁移同步 |
| `cd api && uv run ruff check .` | 通过 |
| `cd api && uv run ruff format --check .` | 通过，97 files |
| `cd api && uv run mypy app/` | 通过，68 个源码文件 |
| `cd api && uv run pytest -q` | 269 passed，13 skipped，1 warning |
| `cd web && bun test` | 47 passed，0 failed |
| `cd web && bun run typecheck` | 通过 |
| `cd web && bun run lint` | 0 errors，21 个既有 `<img>` 警告 |
| `cd web && bun run build` | 通过 |
| `make check` | 通过 |
| `ALEA_E2E_REAL=1 ... bunx playwright test . --config=playwright.config.ts` | 20 passed，覆盖 1440×900 与 390×844 |
| `GET /readyz` | ready；数据库、迁移、Redis、Supabase、Dispatcher、Worker、executor factory 均为 true |

API 测试中的 13 个跳过项是需要 `GATE0_DATABASE_URL` 的真实数据库 G1/G2 用例，不是失败。未将 `mypy .` 的既有测试夹具类型错误混入项目正式门禁；正式门禁范围为 `mypy app/`。

## 浏览器与视觉验收

在内置浏览器以 1440×900 和 390×844 检查了以下真实页面和状态：

- `/console/fixtures`：7 场均可见，来源、日期和 Fixture 标识清晰；移动端无页面横向溢出。
- `/console/admin/sync`：Sporttery Web 未授权时保持禁用，两个持久化批次显示成功与 7/7 计数。
- `/console/admin/lineup` API 标签：11 个 API 目录、DeepSeek 连接测试、2/3 实例和掩码密钥尾号可见。
- `/console/admin/lineup` CLI 标签：11 个 CLI 目录、Codex 路径、版本、认证状态、模型和连接测试可见。
- `/console/admin/roundtable/929f1c7b-8d38-460e-8987-e033b94d5882`：completed、76 条事件、方案终投、已公证和三个 Provider 卡片可见；阶段条只在自身区域滚动。
- `/console/calculator`：没有授权销售数据时明确禁用采纳、出图和下载，不展示虚构赔率或投注方案。

Playwright 生成的 `tests/e2e/test-results` 已清理，临时截图不进入 Git 提交。

## 当前边界与发布注意事项

- 7 场数据是本地非生产 fixture；Sporttery Web Source 在未确认授权前默认禁用。
- 没有授权历史文件，因此历史数据未实际导入。
- Docker API/Web/Redis 健康；Codex CLI 的真实执行由宿主机 Worker 完成，Linux 容器 Worker 不承担 macOS CLI 调用。
- `docker compose` 在未补充 `SUPABASE_JWT_ISSUER`、`SUPABASE_JWKS_URL` 的 `.env` 下会给出配置警告；宿主机 API 使用显式本地值并已通过 `/readyz`。
- 这份报告证明本地 fixture 验收链路，不等同于已取得体彩数据授权或生产上线批准。
