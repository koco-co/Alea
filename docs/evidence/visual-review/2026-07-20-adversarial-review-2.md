# Alea 对抗性审查（第 2 次）

- 日期：2026-07-20
- 范围：运行中视觉验证、P0 主链端到端、Supabase 与 Gate 0 数据真实验证
- 结论：**不通过；本轮没有取得任何可接受的产品页截图，也没有取得 P0 主链或 Gate 0 的真实运行证据。**

## 1. 视觉验证

### 服务启动证据

| 动作 | 结果 | 退出码 / 可见证据 |
|---|---|---|
| `cd web && bun dev`（首次） | 依赖目录不完整，`next: command not found` | 127 |
| 使用本机 Bun 缓存恢复依赖后再次 `cd web && bun dev` | Next 已执行，但环境拒绝监听 `0.0.0.0:3000`，`listen EPERM` | 1 |
| 用已有 `.next/standalone` 监听 `0.0.0.0:3000` | `listen EPERM` | 1 |
| 用已有 `.next/standalone` 监听 `127.0.0.1:3000` | `listen EPERM` | 1 |
| Chrome 打开 `http://127.0.0.1:3000/` | `ERR_CONNECTION_REFUSED` | `00-blocker-localhost-1440x900.jpg` |

阻塞截图已人工检查：尺寸为 `1440 × 900`，内容是 Chrome 连接拒绝页；它仅证明阻塞，**不是**产品页视觉证据。

### 路由 / 视口矩阵

| 步骤 | 路由 | 1440 × 900 | 390 × 844 | 结论 |
|---:|---|---|---|---|
| 1 | `/` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |
| 2 | `/login` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |
| 3 | `/signup` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |
| 4 | `/console` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |
| 5 | `/console/predictions` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |
| 6 | `/console/fixtures` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |
| 7 | `/console/calculator` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |
| 8 | `/console/admin/lineup` | 跳过：服务未启动 | 跳过：服务未启动 | 阻塞 |

计数：通过 0、失败 0、跳过 16。没有逐页渲染，所以不能对原型 HTML、PRD §5.3、响应式、交互或可访问性作视觉通过声明。

## 2. P0 主链端到端

### API 启动

| 动作 | 结果 | 退出码 |
|---|---|---:|
| `cd api && uv run uvicorn app.main:app` | 默认 uv 缓存不可写 | 1 |
| 改用仓库内 uv 缓存并锁定依赖 | 网络受限，无法下载 `pycparser==3.0` | 1 |
| `make gate0` | 网络受限，无法下载 `amqp==5.3.1` | 2 |

### 链路判定

| 步骤 | 运行判定 | 结构证据 |
|---:|---|---|
| 9. 发起推演 | 未执行；确定性缺口 | PRD 对应的 `/console/admin/roundtable` 页面不存在；实施计划 Task 5.2 仍未勾选。 |
| 10. 直播监听 | 未执行；确定性缺口 | 直播详情页不存在；`main.py` 未注入 `roundtable_event_gateway`，事件 API 会返回 `503 roundtable_event_gateway_unavailable`。 |
| 11. 公证 | 未执行 | SQL 中存在 `notarize_roundtable(uuid)`，但本轮未连接真实数据库、未产生真实 job、未调用 RPC。 |
| 12. 发布 | 未执行；确定性缺口 | `/console/admin/publish` 页面不存在；`main.py` 未注入 `admin_gateway`，发布 API 会返回 `503 admin_gateway_unavailable`。 |
| 13. 用户可见 | 未执行；伪 E2E 风险 | 推演详情页直接使用硬编码 `events` 数组；静态可见内容不能证明发布后投影。 |

结论：主链通过 0、失败/确定性缺口 4、仅存在局部构件但未验证 1。当前不能建立“发起推演 → 直播监听 → 公证 → 发布 → 用户可见”的端到端证据。

## 3. Supabase 与 Gate 0

| 检查 | 结果 | 退出码 / 证据 |
|---|---|---|
| `python3 scripts/validate_env.py --file .env --require-database` | 失败：`.env` 为 `0644`，要求 `0600` | 1 |
| 配置名对齐 | 失败：根配置是 `PROJECT_URL/PUBLISHABLE_KEY/SECRET_KEY`；Web 读取 `NEXT_PUBLIC_SUPABASE_*`；API 读取 `SUPABASE_URL/SUPABASE_SECRET_KEY` | 静态确定 |
| Supabase REST（当前代理） | 代理指向不可达的 `127.0.0.1:7897` | curl 7 / HTTP 000 |
| Supabase REST（取消代理直连） | DNS 无法解析项目域名 | curl 6 / HTTP 000 |
| Chrome 打开项目 REST 根路径 | `ERR_BLOCKED_BY_CLIENT` | 未形成凭据有效性证据 |
| `make db-push ENV=local` | Supabase CLI 未安装，迁移未开始 | make 2；内部命令 127 |
| `make gate0` | 依赖下载被阻断，测试未开始 | 2 |
| `run_gate0.py` 外部门槛 | `.env` 未提供脚本读取的 `GATE0_DATABASE_URL`、用户 ID 与其余批准标志 | Gate 0 必然不能判为通过 |

数据库 DSN 的五个角色条目均存在且主机/角色格式可解析，但本轮无法证明密码正确、数据库可达、迁移已应用、RLS 生效或种子一致。

## 4. PRD §5.3 对照边界

源文件可见的固定数据（西班牙 vs 阿根廷、`2 : 1`、半场 `1 : 0`、`5/7`、`71%`、`N8C4-02`）与 §5.3 的固定 fixture 表面一致；但未取得当前渲染截图，以下全部未验证：

- 页面级 `来源：FIFA · 采集 2026-07-19` 与 `AI 推演数据` 是否在双视口可见；
- 体彩编号、赔率、首发、伤停、裁判、技术统计是否统一显示规定缺失态；
- 当前事实记录是否与组件状态样例、结算态、撤回态严格隔离；
- 八个路由是否与 `docs/PrototypeDesign/open-design/` 同视口匹配；
- 键盘焦点、触屏目标、动态状态文字、对比度与响应式回流。

## 5. 未验证清单

1. 八个目标路由的 16 张产品页截图。
2. 每个目标页的导航、标签、菜单、表单、空态、错误态、权限态与恢复路径。
3. 真实 API health 与认证请求。
4. 真实圆桌 job、Realtime 私有频道、补拉去重与断线恢复。
5. `notarize_roundtable` 真实事务、发布质检、发布投影和注册用户读取。
6. Supabase 凭据有效性、数据库连接、迁移历史、Gate 0 seed 与 RLS。
7. Gate 0 的真实 Provider、数据许可、容量、RPO/RTO、恢复与负载批准项。
