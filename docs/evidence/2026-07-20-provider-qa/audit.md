# Provider、竞彩与启动验收记录

验收日期：2026-07-20（Asia/Taipei）

## 已执行

| 目标 | 操作与结果 | 证据 |
|---|---|---|
| 环境与 KEK | `make verify-kek`，退出码 0；现有 KEK 加解密往返与错误 AAD 拒绝均通过，未显示密钥 | 终端输出；`.env` 权限 `0600` |
| Python 锁 | `uv lock --check`、`uv sync --locked`，退出码 0；解析 75 个包，检查 73 个包 | `api/uv.lock` |
| Bun 锁与构建 | `bun install --frozen-lockfile`、`bun run build`，退出码 0；448 packages 无变更，23 个静态/动态路由生成 | `web/bun.lock` |
| 工具版本 | Supabase CLI `2.109.1`；uv `0.11.28`；本机 Bun `1.3.8` | `packageManager`/容器固定为 Bun `1.3.10`，但该二进制版本未在本机执行 |
| 仓库门禁 | `make check`，退出码 0；API 84 passed / 13 skipped / 0 failed，Web 25 passed / 0 failed；mypy/tsc/lint 通过 | 13 个 skip 均因缺 `GATE0_DATABASE_URL` |
| 数据库 push | `supabase db push --dry-run --include-all`，退出码 1：项目未 `supabase link`；`make db-push ENV=local`，退出码 2：缺 `SUPABASE_DB_URL` | 未尝试猜测或回显密码 |
| 启动 | `make dev` 首次暴露并修复后台 runner 工作目录错误；再次执行退出码 2：四个服务角色 DSN 缺失，Docker daemon 未运行 | 宿主 runner 由 trap 清理 |
| CLI 运行时 | 实际 runner `POST /internal/v1/execute` 返回 200；结构化 `predict_score`、usage 与 latency 均存在；页面探测和测试连接通过 | `web-lineup-cli-1440x900.png`、`web-lineup-cli-390x844.png` |
| API Provider UI | 切换 API 模式；验证 HTTPS/allowlist 字段、替换输入、清除状态、1/3 实例与保存失败反馈 | `web-lineup-api-1440x900.png` |
| OpenDesign | CLI/API 切换、重新扫描、严格 Schema 测试；桌面与移动渲染；移动保存栏遮挡已修复 | `opendesign-lineup-cli-1440x900.png`、`opendesign-lineup-api-1440x900.png`、`opendesign-lineup-api-390x844.png` |
| 竞彩规则设置 | 初次点击证实死控件；随后实现可展开历史、4 项来源台账、在线复核待接入与安全回退状态 | `web-settings-sporttery-1440x900.png` 是修复前证据；修复后尚缺新浏览器截图 |
| P0 圆桌 | 删除实际页面的固定 5/7、71% 与七 Provider 成功态；当前 1 个真实 Provider 时展示 `NO-QUORUM` 并禁用圆桌/共识动作 | `web-predictions-no-quorum-1440x900.png`、`web-predictions-no-quorum-state-390x844.png` |

## 数据库已验证子集

通过 Supabase 插件应用并对齐 6 个时间戳迁移。四个服务角色均为
`LOGIN / NOSUPERUSER / NOCREATEDB / NOCREATEROLE / NOINHERIT`；插件查询验证了
API、worker、dispatcher、scheduler 的最小权限矩阵。Security advisor 剩余 4
个已知 authenticated `SECURITY DEFINER` warning；performance advisor 为新空表
unused-index INFO。

## 未验证与阻塞

- 缺 `SUPABASE_DB_URL`、`DATABASE_URL_ALEA_API`、
  `DATABASE_URL_ALEA_WORKER`、`DATABASE_URL_ALEA_DISPATCHER`、
  `DATABASE_URL_ALEA_SCHEDULER`，因此四角色直连、SCRAM 密码状态、真实 G1/G2
  RLS 矩阵和 `make db-push` 未执行。
- `realtime.messages` 由 `supabase_realtime_admin` 所有；当前插件迁移身份不能创建
  私有 channel read policy，G2 保持未完成。
- Provider 管理数据库 gateway 尚未接入；UI 的保存动作刻意显示失败，CRUD
  persistence、密钥替换/清除落库和真实 API Provider 连接测试未验证。
- 竞彩规则历史、来源待确认和安全回退已实现，但发生在本轮浏览器会话结束后，
  尚缺修复后的双视口视觉证据；OpenDesign 系统设置页仍缺。
- OpenDesign 预测页源码已同步 no-quorum，但尚缺同步后的双视口新截图。
- 本机 Docker daemon 未运行，Redis、API、worker、dispatcher、scheduler、Web
  与 nginx 的 Compose health 未验证。
- 本机实际 Bun 为 `1.3.8`；虽然仓库与容器合同已固定 `1.3.10`，仍需在 CI
  或镜像构建中执行该精确版本。
- 无目标 Linux 主机权限，systemd、专用用户、device-auth 和生产 smoke 未验证。
- 浏览器范围仅覆盖本记录列出的受影响页面，不代表全产品、全路由或完整 E2E。
