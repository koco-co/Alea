# 圆桌前后端数据库链路验收

日期：2026-07-21

## 已验证

- 环境：本地 Supabase、FastAPI `127.0.0.1:8000`、Next `127.0.0.1:3002`、Redis、Celery Dispatcher、Worker；内置浏览器已登录管理员账号。
- 管理台 `/console/admin/roundtable` 从真实接口读取 2 个可参赛实例：Codex CLI 与 DeepSeek API。
- 点击“发起圆桌”后，FastAPI 返回真实 `job_id` 并跳转直播页；数据库事务写入任务、参与者、比赛运行、首个事件和 Outbox。
- Dispatcher 从 Outbox 发布 `roundtable.lifecycle`；Worker 成功消费并追加 `worker_received` 持久化事件。
- 直播页通过 Next BFF 回补 `/v1/roundtables/{job_id}/events`，显示 `2 条持久化事件`，事件序号连续为 `#1`、`#2`。
- Worker 成功任务：`470cf7d0-ad5c-48b1-93a6-7dc8192c96f1`；截图：
  - `roundtable-start-real-instances.png`
  - `roundtable-worker-ack-1440x900.png`

## 自动化检查

- `make check`：通过；API 233 passed / 13 skipped，Web 36 passed；静态检查、类型检查通过。
- 定向圆桌 API/迁移测试：9 passed。
- `bun test src/lib/realtime.test.ts`：2 passed。
- 13 个跳过项是需要 `GATE0_DATABASE_URL` 的真实 RLS/Realtime 测试，不是本次链路失败。

## 未包含在本次门禁

- 本次只验证“任务创建 → Outbox → Dispatcher → Worker → 持久事件 → 直播回补”。Provider 九阶段 AI 调用、完整结果落库、公证与发布仍需单独验收；当前 Worker lifecycle task 明确只负责首个 Worker 回执。
- 截图由内置浏览器当前窗口生成，实际捕获尺寸为浏览器窗口的 1265×712；未宣称其等同于 1440×900 设计验收视口。
