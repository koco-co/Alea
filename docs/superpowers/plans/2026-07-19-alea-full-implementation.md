# Alea — 竞彩足球 AI 预测平台 完整实施计划（v14 final，经十三轮 GPT-5.6-Sol high 审阅，共 90 项修正）

> **For agentic workers:** 本计划包含 8 个阶段 38 个任务，覆盖从 Gate 0 验证到生产上线的全部阶段。按 TECH §15 的顺序实施，每个阶段有明确完成标准。

**Goal:** 从零构建完整的 Alea 多 AI 协作竞彩足球预测平台。

**Architecture:** Monorepo — Next.js App Router 前端 + Python FastAPI/Celery 后端 + Supabase Cloud (Auth/DB/Realtime) + Redis + Docker Compose。圆桌编排为核心：自主/指定双模式，选场→逐场辩论→组单四段流水线。

**Tech Stack:** TypeScript/Next.js App Router (Bun), Python/FastAPI/Celery (uv), Supabase PostgreSQL, Redis 7, Docker Compose, shadcn/ui, TanStack Query

## 全局约束

- PRD v1.9 为产品事实唯一来源，TECH v1.5 为架构决策来源，提示词架构 v1.2 为 AI 行为规范来源
- 竞彩足球五种玩法（胜平负/让球胜平负/比分/总进球/半全场）；常规时间 90 分钟+伤停补时
- 平台只预测不购买；首版 Web 桌面优先（1440×900），移动端自适应（390×844）
- 浅色模式仅，Claude 暖色风格。DESIGN.md 为视觉系统唯一权威来源（AGENTS.md §1）：底色 `#FAF9F5`(canvas)，陶土橙强调 `#CC785C`(primary)。PRD v1.9 §5.1 中的色值（`#F4F1EA`/`#C0613B`）为早期近似值；实施前先将 PRD 色值同步至 DESIGN.md Token 一致。完整 Token 体系（typography/spacing/rounded）参见 DESIGN.md
- Gate 0 全部通过前禁止业务功能开发；规则配置化、公证账本不可变
- 体彩数据源未获授权前使用固定 fixtures，Sporttery Web Source 默认禁用
- 所有共享 Schema 从 `shared/schemas/roundtable.json` 通过代码生成 Pydantic/Zod 类型，禁止手工双维护
- 全站 WCAG AA 无障碍；数据新鲜度指示器全站统一；全局异常降级（后端不可用/AI不可用/数据过期>24h）

---

## 阶段 0：项目基础设施搭建

### Task 0.1: Monorepo 脚手架与工具链

**Files:**
- Create: `web/package.json`, `web/tsconfig.json`, `web/next.config.ts`, `web/.env.example`
- Create: `api/pyproject.toml`, `api/.python-version`, `api/.env.example`
- Create: `shared/schemas/` (目录)
- Create: `supabase/migrations/` (目录)
- Create: `docker-compose.yml`, `docker-compose.dev.yml`, `nginx.conf`
- Create: `Makefile`, `.env.example`(根目录)
- Create: `.gitignore`

- Create: `web/Dockerfile`, `api/Dockerfile`
- Create: `api/app/main.py`（FastAPI 入口 + `/health` endpoint）
- Create: `web/src/app/api/health/route.ts`（Next.js health route）

**Interfaces:**
- Produces: `make bootstrap/dev/check/test/db-push/bootstrap-admin` 命令，Docker Compose 本地开发环境（含全部 7 个服务）

- [x] **Step 1: 初始化 web/ 目录**

```bash
mkdir -p web/src/{app,components/{ui,marketing,prediction,calculator,charts},lib/{supabase,calculator,api-client},types}
cd web && bun init -y
bun add next@latest react@latest react-dom@latest
bun add -d @types/react @types/react-dom typescript eslint prettier eslint-config-next
bun add @supabase/supabase-js @supabase/ssr @tanstack/react-query zod
bun add tailwindcss @tailwindcss/postcss postcss
```

- [x] **Step 2: 初始化 api/ 目录**

```bash
mkdir -p api/app/{routers,orchestration/phases,prompts,tools,providers,secrets,datasources,calculators,workers}
cd api && uv init --name alea-api --python 3.12
uv add fastapi uvicorn[standard] celery[redis] redis httpx supabase pyjwt cryptography pydantic
uv add -d pytest pytest-asyncio httpx-mock mypy ruff
```

- [ ] **Step 3: 配置完整 Docker Compose（含 7 个服务 + healthcheck）**

`docker-compose.yml`:
```yaml
services:
  nginx:
    image: nginx:1.27.5-alpine
    ports: ["80:80"]
    volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
    depends_on:
      web: { condition: service_healthy }
      api: { condition: service_healthy }

  web:
    build:
      context: ./web
      args:
        - NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
        - NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY}
    environment:
      - INTERNAL_API_URL=http://api:8000
    healthcheck:
      test: ["CMD", "bun", "-e", "fetch('http://localhost:3000/api/health').then(r=>{if(!r.ok)process.exit(1)})"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 20s

  api:
    build: ./api
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SECRET_KEY=${SUPABASE_SECRET_KEY}
      - DATABASE_URL_ALEA_API=${DATABASE_URL_ALEA_API}
      - PROVIDER_KEK_V1=${PROVIDER_KEK_V1}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 20s

  worker:
    build: ./api
    command: uv run --locked celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 -Q long
    environment:
      - DATABASE_URL_ALEA_WORKER=${DATABASE_URL_ALEA_WORKER}
      - PROVIDER_KEK_V1=${PROVIDER_KEK_V1}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis: { condition: service_healthy }

  worker-short:
    build: ./api
    command: uv run celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q default
    environment:
      - DATABASE_URL_ALEA_WORKER=${DATABASE_URL_ALEA_WORKER}
      - PROVIDER_KEK_V1=${PROVIDER_KEK_V1}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis: { condition: service_healthy }

  dispatcher:
    build: ./api
    command: uv run python -m app.workers.dispatcher
    environment:
      - DATABASE_URL_ALEA_DISPATCHER=${DATABASE_URL_ALEA_DISPATCHER}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis: { condition: service_healthy }

  scheduler:
    build: ./api
    command: uv run celery -A app.workers.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL_ALEA_SCHEDULER=${DATABASE_URL_ALEA_SCHEDULER}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis: { condition: service_healthy }

  redis:
    image: redis:7.4.3-alpine
    command: redis-server --appendonly yes --appendfsync everysec
    volumes: ["redis_data:/data"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  redis_data:
```

- [x] **Step 4: 编写完整 Makefile**

```makefile
.PHONY: bootstrap env-init dev dev-down format lint typecheck test check db-push bootstrap-admin

bootstrap:
	cd api && uv lock --check && uv sync --locked
	cd web && bun ci

env-init:
	test -f .env.local || (echo "ERROR: create .env.local first (see .env.example)"; exit 1)
	test -f web/.env.local || cp web/.env.example web/.env.local
	test -f api/.env || cp api/.env.example api/.env
	@echo "supabase CLI must be installed (brew install supabase/tap/supabase or npm i -g supabase)"

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-down:
	docker compose down

format:
	cd api && ruff format --check . && cd ../web && bunx prettier --check src/

format-fix:
	cd api && ruff format . && cd ../web && bunx prettier --write src/

lint:
	cd api && ruff check . && cd ../web && bun lint
	cd supabase/migrations && find . -name '*.sql' -exec echo "lint: {}" \;  # SQL lint placeholder (TECH §9)

lint-sql:
	@echo "SQL lint must be added via squawk or similar in CI"

typecheck:
	cd api && mypy app/ && cd ../web && bun typecheck

test:
	cd api && pytest -v && cd ../web && bun test

db-push:
	@test -n "$(ENV)" || (echo "ERROR: ENV is required (local|staging|production)"; exit 1)
	@case "$(ENV)" in local) f=".env.local";; staging) f=".env.staging";; production) f=".env.production";; *) echo "Invalid ENV: $(ENV)"; exit 1;; esac
	@test -f "$$f" || (echo "ERROR: $$f not found"; exit 1)
	supabase db push --db-url "$$(grep SUPABASE_DB_URL "$$f" | cut -d= -f2-)"

bootstrap-admin:
	cd api && uv run --locked python ../scripts/bootstrap_admin.py --email $(EMAIL) --env $(ENV)

check: format lint typecheck test
```

- [x] **Step 5: 验证工具链**

```bash
make bootstrap && make check
```

- [ ] **Step 6: 提交**

```bash
git add Makefile docker-compose.yml docker-compose.dev.yml nginx.conf .env.example .gitignore web/ api/ shared/ supabase/migrations/ && git commit -m "chore: initialize monorepo scaffold with full Docker Compose and toolchain"
```

---

### Task 0.2: Gate 0 最小数据库迁移

**迁移文件清单（单调递增，无重复编号，一步一个文件）：**
1. `20260720043401_gate0_minimal.sql` — Gate 0 所需表+枚举+RLS+公开投影+不可变触发器（含全部 Gate 验证依赖的表：`profiles`/`user_consents`/`ai_providers`/`provider_connections`/`provider_secrets`/`ai_instances`/`roundtable_jobs`/`roundtable_match_runs`/`roundtable_participants`/`roundtable_phase_runs`/`roundtable_results`/`fact_claims`/`roundtable_events`/`execution_audits`/`outbox_events`/`notarized_predictions`/`prompt_versions`/`score_formula_versions`/`system_setting_versions`/`sporttery_rule_versions`/`admin_role_grants`/`admin_audit_logs` 以及公开投影表）
2. `20260720043411_gate0_seed.sql` — 首版版本记录 seed（Task 0.2b，依赖 Gate 0 最小表均已创建）
3. `20260720043525_realtime_triggers.sql` — Realtime Broadcast trigger（G2 前提；`realtime.messages` 的 owner policy 仍需平台支持流程）
4. **Gate 0 全部通过后（Task 1.7 完成）：**
5. `<timestamp>_business_schema.sql` — 完整业务 ~50 张表（TECH §6.1–6.7 全部）+ 剩余 RLS + GRANT + 专用函数

**Gate 0 执行策略**：
1. Gate 0 迁移已按远端 Supabase 历史对齐为 `20260720041522` 至 `20260720043722` 六个单调递增版本。
2. Supabase 已应用迁移不可修改；后续修复必须追加新时间戳迁移，不得重写上述历史。
3. 迁移推送后执行 Task 1.1–1.7（G1–G6）；Task 1.2/G2 只测试已应用的 Realtime trigger，不修改历史文件。
4. Gate 汇总通过后，Task 0.2c 创建并推送新的 `<timestamp>_business_schema.sql`。

**角色创建**：四个运行时数据库角色（`alea_api`/`alea_worker`/`alea_dispatcher`/`alea_scheduler`）已由 `20260720041522_bootstrap_service_roles.sql` 创建；G1 仍需使用四个独立 DSN 完成真实直连权限矩阵。

**重要**：Gate 0 只创建 TECH §16 列出的最小表集：...同上...、`sporttery_rule_versions`（Gate 0 G5 规则验证依赖）、`schedules` + `schedule_runs`（G1 scheduler 权限矩阵 + G3 Beat 重叠恢复验证依赖，TECH §6.7/§5.7）。Gate 0 验证失败则回滚，不铺开完整业务结构（TECH §15/§16）。

- [x] **Step 1: 编写 Gate 0 最小迁移（时间戳版本）** — 仅以上列表，含 Gate 0 所需的枚举、表、RLS、GRANT、不可变函数和 `notarize_roundtable()` 最小实现

- [ ] **Step 5: Gate 0 通过后运行时间戳正式业务迁移** — TECH §6.2–6.7 的完整表结构（全部约 50 张表，包含：
- `public_execution_audits`（脱敏只读投影）
- `public_notarized_predictions`（停售后开放的公证投影）
- `public_roundtable_events`（对注册用户开放的回放事件投影）
- `history_context_versions`（每桌每实例冻结的统计/近期赛果/校准）
- `lesson_set_versions`（每次圆桌冻结的教训集合）
- `score_formula_versions`（综合分/先验/票权算法版本）
- `sporttery_rule_versions`（算票与结算规则 JSON 版本）
- `system_setting_versions`（模拟盘/风控/同步/历史上下文限额等版本化设置）

关键枚举必须包含方法论评审所需状态：

```sql
CREATE TYPE roundtable_job_state AS ENUM (
    -- 预测任务状态
    'pending', 'select_nominating', 'select_debating', 'select_voting',
    'processing_matches', 'bet_proposing', 'bet_debating', 'bet_voting',
    'notarizing', 'completed',
    -- 方法论评审任务状态（TECH §5.9）
    'independent_reviewing', 'review_debating', 'review_voting',
    'pending_admin_confirmation',
    -- 修改后再审终态（TECH §5.9：提议需修订，当前方法论保持不变）
    'revise_and_review',
    -- 通用终态
    'no_quorum', 'terminated', 'failed'
);
```

- [ ] **Step 2: 提交 Gate 0 最小迁移**

```bash
make db-push ENV=local
```

- [ ] **Step 7: 提交**

---

### Task 0.2c: Gate 0 通过后 — 正式业务迁移

**Files:**
- Create: `supabase/migrations/<timestamp>_business_schema.sql`

**前置条件**：Task 1.7（Gate 0 汇总）已通过。

- [ ] **Step 1: 创建完整业务迁移** — TECH §6.2–6.7 全部约 50 张表（数据源/赛程/赔率/阵容/实体映射/复盘/教训/方法论/关注/通知/调度等）+ 剩余 RLS/GRANT/不可变触发器/专用函数 统一定义

---

### Task 0.2b: 首版版本记录初始化（首个圆桌启动前提）

**Files:**
- Modify: `supabase/migrations/20260720043411_gate0_seed.sql`（已应用历史不可重写；后续变更须追加迁移）

**关键**：缺少以下首版记录时首个圆桌无法确定性启动（TECH §6.7 约束 + 协议 §2.2）。

- [x] **Step 1: seed `prompt_versions`** —
  - `key=identity, version=1`（协议 §2.2 `IDENTITY_PROMPT_SEED`；后台只读，迁移发布）
  - `key=core_methodology, version=1`（协议 §2.2 `CORE_METHODOLOGY_SYSTEM_PROMPT`）
  - 九阶段 `key=phase_select_nominate/debate/vote, score_predict/debate/vote, bet_propose/debate/vote, version=1`（协议 §3.1–3.7）
  - `key=phase_review_prediction, version=1`（协议 §11.2 复盘指令）
  - `key=phase_review_methodology, version=1`（协议 §11.4 方法论评审指令）
  - 九阶段输出 Schema 版本（协议 §3.8 `PHASE_OUTPUT_SCHEMAS`）：`key=output_schema_<phase>, version=1`
  - 工具合同版本：`key=tool_contract_<phase>, version=1`（协议 §8 `TOOL_DEFINITIONS`）
  - 复盘输出 Schema：`key=output_schema_review_prediction, version=1`（协议 §11.2 `REVIEW_AND_LESSONS_SCHEMA`）
  - 方法论评审输出 Schema：`key=output_schema_review_methodology, version=1`（协议 §11.4 `METHODOLOGY_REVIEW_SCHEMA`）
  - 合计 11 个输出 Schema（`PHASE_OUTPUT_SCHEMAS` 的 9 个预测阶段 + 复盘 Schema + 方法论评审 Schema；协议 §3.8 的 `PHASE_OUTPUT_SCHEMAS` 字典只含 9 个预测阶段，复盘和方法论评审是独立合同 §11.2/§11.4；工具合同独立版本化，不纳入输出 Schema 计数）
- [x] **Step 2: seed `score_formula_versions`** — 首版：先验样本数=10、冷启动先验=50、权重维度 40/30/15/15、贝叶斯平滑公式
- [x] **Step 3: seed `system_setting_versions`** — `key=history_context_limits`（recent_match_limit=10, lesson_limit=5）；`key=methodology_trigger`（distinct_match_threshold=3, lesson_count_threshold=5, consecutive_error_threshold=5, lookback_days=null）；`key=risk_limits`（daily=15%, per_match=5%, initial_balance=10000）
- [x] **Step 4: seed `sporttery_rule_versions`** — 首版竞彩规则（从体彩官网获取的过关规则/奖金上限/无效场次处理）

---

### Task 0.3: 共享 Schema 与代码生成

**Files:**
- Create: `shared/schemas/roundtable.json`（组合根，`$ref` 引用下列阶段合同）
- Create: `shared/schemas/prediction_card.json`
- Create: `shared/schemas/selection.json`
- Create: `shared/schemas/debate.json`
- Create: `shared/schemas/bet_plan.json`
- Create: `shared/schemas/review.json`
- Create: `shared/schemas/methodology_review.json`
- Create: `shared/schemas/tools.json`
- Create: `shared/schemas/match.json`
- Create: `scripts/generate_types.py`（从 JSON Schema 生成 Pydantic models）
- Create: `scripts/generate_types.ts`（从 JSON Schema 生成 Zod schemas / TS types）
- Modify: `Makefile`（添加 `make generate-types` target）

**关键规则**：所有 Schema 以 `shared/schemas/` 下的 JSON Schema 为单一事实源。Pydantic 和 Zod/TS 类型通过脚本自动生成，严禁手工维护两份副本。

- [ ] **Step 1: 从上游文档各章节提取完整 Schema**
  - 9 个预测阶段 Schema：协议 §3.8（`PHASE_OUTPUT_SCHEMAS`）
  - 赛后复盘 Schema：协议 §11.2（`REVIEW_AND_LESSONS_SCHEMA`）
  - 方法论评审 Schema：协议 §11.4（`METHODOLOGY_REVIEW_SCHEMA`）
  - 工具合同 Schema：协议 §8（`TOOL_DEFINITIONS`）
  - Provider 公共合同：TECH §5.2（`ProviderRequest`/`ProviderResult`）
- [ ] **Step 2: 编写代码生成脚本**
- [ ] **Step 3: 验证生成结果并提交**

---

## 阶段 1：Gate 0 — 架构验证（开发前必过）

### Task 1.1: G1 — 认证/RLS/角色权限验证

**Files:**
- Create: `api/tests/test_g1_auth_rls.py`
- Create: `scripts/bootstrap_admin.py`（首个管理员引导脚本）
- Create: `docs/evidence/gate-0/g1/README.md`

- [ ] **Step 1: 对 anon、user、admin、alea_api、alea_worker、alea_dispatcher、alea_scheduler 逐项验证权限矩阵**（TECH §10.2）
- [ ] **Step 2: 验证停售前后公开投影**
- [ ] **Step 3: 实现首个管理员引导** — `make bootstrap-admin EMAIL=... ENV=local`（TECH §6.1 约束）
- [ ] **Step 4: 运行并记录证据** — `pytest api/tests/test_g1_auth_rls.py -v`

---

### Task 1.2: G2 — Realtime/补拉验证

**Files:**
- Modify: `supabase/migrations/20260720043525_realtime_triggers.sql`（已应用历史不可重写；后续变更须追加迁移）
- Create: `api/tests/test_g2_realtime.py`
- Create: `docs/evidence/gate-0/g2/README.md`

- [ ] **Step 1: Realtime Broadcast trigger 迁移**
- [ ] **Step 2: 补拉竞态测试** — 验证 TECH §5.1 的顺序：先订阅等待 SUBSCRIBED → 再补拉 → broadcast 按 event_seq 去重。必须覆盖：断网重连后完整恢复、主动制造 event_seq 跳号验证跳号检测与触发补拉
- [ ] **Step 3: 验证未授权订阅拒绝、客户端 Broadcast INSERT 拒绝**
- [ ] **Step 4: 运行并记录**

---

### Task 1.3: G3 — Celery 恢复验证

**Files:**
- Create: `api/tests/test_g3_celery_recovery.py`
- Create: `docs/evidence/gate-0/g3/README.md`

- [ ] **Step 1: Celery app 最小骨架**
- [ ] **Step 2: 完整恢复测试** — 必须覆盖 TECH §16 G3 全部场景：重复投递、Worker graceful stop、kill -9、Redis restart、Dispatcher restart、任务超时、迟到结果、Beat 重叠、毒任务不循环
- [ ] **Step 3: 运行并记录**

---

### Task 1.4: G4 — Provider Contract 测试

**Files:**
- Create: `api/app/providers/contract.py`
- Create: `api/app/providers/fake.py`
- Create: `api/app/providers/capabilities.py`
- Create: `api/tests/test_g4_provider_contract.py`
- Create: `docs/evidence/gate-0/g4/README.md`

- [x] **Step 1: Fake Provider** — 返回合法 Schema 的静态 fixture，覆盖全部 11 个方法（9 个预测阶段 + `review_prediction` + `review_methodology`）
- [x] **Step 2: Contract 测试** — fake server 覆盖超时、限流、无效 JSON、拒绝响应、密钥脱敏、伪造角色标签攻击、"忽略前文"指令注入攻击
- [ ] **Step 3: 真实 vendor/model capability test** — 对计划启用的每个具体 vendor/model，完整运行 11 个业务合同（9 个预测阶段 + `review_prediction` + `review_methodology`），验证结构化输出合规性、usage/request-id 返回、错误分类、角色边界（指令 vs 数据分离）。形成独立 capability report。不合格模型不能启用（TECH §16 G4）
- [ ] **Step 4: Provider 重复调用方差实验** — 对每个启用模型以相同参数重复调用同一预测合同 ≥5 次，记录输出差异与指标波动，确定方法论回测所需的正式 `attempts_per_instance`（下限 2，上限由实验确定）。实验结果写入 `system_setting_versions(key=backtest_execution_config)` 版本化配置（含 `attempts_per_instance`、`sample_size`、`evaluator_version`、`generation_parameter_versions`、`output_schema_version`、`tool_contract_version`），供 Task 7.4 回测正式使用

---

### Task 1.5: G5 — 数据源与规则验证

**Files:**
- Modify: `api/app/calculators/sporttery_calc.py`（最小确定性实现，Gate 0 前提）
- Modify: `web/src/lib/calculator/engine.ts`（最小 TS 实现，Gate 0 前提）
- Create: `api/tests/fixtures/sporttery_sample.json`
- Create: `api/tests/test_g5_data_rules.py`
- Create: `docs/evidence/gate-0/g5/README.md`

**前置条件**：Task 0.3 已创建共享类型；G5 在 Gate 0 阶段创建最小 calculator + 解析器实现（TECH §16 允许的验证脚手架），Task 3.1/3.2 在 Gate 0 后扩展为完整实现。

- [x] **Step 1: 固定 fixtures** — 基于 2026-07-19 人工观察数据（PRD §5.3 约束）
- [x] **Step 2: 最小解析器 + 降级测试** — 200/403/超时/字段缺失/缓存/限频
- [x] **Step 3: 竞彩规则 golden test** — 最小 TS/Python 实现使用权威 golden fixtures 验证，结果严格一致（TECH §13）
- [ ] **Step 4: 数据许可核验** — 逐项验证自动访问许可及生产展示、历史保存、再分发许可记录是否存在且覆盖当前用途；未授权环境不发自动请求（TECH §16 G5）
- [x] **Step 5: 竞彩规则初始数据** — 从体彩官网（https://www.sporttery.cn）和公开规则文档获取五种玩法的过关规则、奖金上限、无效场次处理规则，录入为 `sporttery_rule_versions` 首版，并在 G5 中验证

---

### Task 1.6: G6 — 备份/容量/成本（新增，TECH §16 要求）

**Files:**
- Create: `docs/evidence/gate-0/g6/README.md`

- [ ] **Step 1: 选定生产 Supabase/Redis/运行平台套餐**
- [ ] **Step 2: 估算峰值任务、tokens、事件量、直播并发数**
- [ ] **Step 3: 压测** — 在目标负载下验证 Realtime/Worker/DB 有余量；确认告警阈值
- [ ] **Step 4: 执行一次隔离恢复与 runbook**（TECH §11.2）
- [ ] **Step 5: 产品确认 RPO/RTO/预算**

---

### Task 1.7: Gate 0 汇总报告

**Files:**
- Create: `docs/evidence/gate-0/SUMMARY.md`

汇总 G1–G6 全部结果；任一 Gate 未通过时方案回到 TECH/PRD 修改。

---

## 阶段 2：基础安全骨架

### Task 2.1: Supabase Auth 集成、中间件与 Web 安全

**Files:**
- Create: `web/src/lib/supabase/client.ts`
- Create: `web/src/lib/supabase/server.ts`
- Create: `web/src/lib/supabase/middleware.ts`
- Create: `web/src/middleware.ts`
- Create: `web/src/lib/security.ts` (sanitize, CSP, CSRF helpers)
- Create: `api/app/middleware.py` (JWT验证 + CORS + 限流)
- Create: `api/app/secrets/envelope.py` (AES-256-GCM envelope encryption for Provider 密钥)

- [ ] **Step 1: Supabase 客户端** — browser client + server client (SSR)
- [ ] **Step 2: Next.js middleware** — 游客跳转登录，已登录回跳原地址
- [ ] **Step 3: FastAPI 中间件** —
  - JWT 签名/过期/issuer/audience 校验
  - CORS 白名单（仅允许显式 Web 域名）
  - Origin/CSRF 校验（写操作 Cookie）
  - 高成本接口限流（登录/Provider测试/手动同步/发起推演/图片生成）
- [ ] **Step 4: 安全控制** —
  - HTML/Markdown 白名单净化（外链 `rel="nofollow noopener"` + 协议白名单）
  - Provider/DataSource HTTP 客户端禁止 loopback/link-local/私网/metadata 地址
  - 统一敏感信息脱敏（API key/Cookie/Authorization/上游响应正文不入日志）
- [ ] **Step 5: 提交**

---

### Task 2.2: 认证页面（登录/注册/找回密码）

**Files:**
- Create: `web/src/app/(auth)/login/page.tsx`
- Create: `web/src/app/(auth)/signup/page.tsx`
- Create: `web/src/app/(auth)/forgot/page.tsx`
- Create: `web/src/app/(auth)/layout.tsx`
- Create: `web/src/app/auth/callback/route.ts`

- [ ] **Step 1: 登录页面** — 邮箱+密码；GitHub/Google OAuth 按钮；「忘记密码」
- [ ] **Step 2: 注册页面 + 后端** — 年满 18 岁确认 + 条款确认（两个必选 checkbox，未勾选禁止提交，PRD §7.1）；后端创建 Auth 用户后同步写入 `user_consents`（含条款版本号与同意时间），缺任一项确认则拒绝创建账户
- [ ] **Step 3: OAuth 流程（兼容 Supabase Auth 架构）** — Supabase OAuth code exchange 自动创建 Auth 用户并签发 session（非应用层可控）。实施策略：回调后检查 `user_consents` → 无有效同意则标记 profile 为 `pending_consent` 状态并重定向到独立确认页（两个必选 checkbox + 条款版本号）→ 用户同意后写入 `user_consents` 并清除 `pending_consent` 标记；拒绝则删除 Auth 用户及相关数据。中间件拦截 `pending_consent` 状态用户，禁止访问除确认页外的任何控制台路由。后续 OAuth 登录直接检查 consent 存在后放行。Supabase Auth callback URL 配置为 `http://localhost/auth/callback`，Site URL 配置为 `http://localhost`（TECH §3.3）

---

### Task 2.3: 控制台导航框架 + 每日总览

**Files:**
- Create: `web/src/app/console/layout.tsx`
- Create: `web/src/components/ui/top-nav.tsx`
- Create: `web/src/app/console/page.tsx` (每日总览完整实现，非 placeholder)
- Create: `web/src/components/console/daily-brief.tsx`
- Create: `web/src/components/console/admin-todos.tsx`

- [ ] **Step 1: 控制台布局** — 顶部导航（8 个模块 + 系统管理分隔线，PRD §4.2）
- [ ] **Step 2: 每日总览完整实现**（PRD §7.2）—
  - 今日研究简报（在售场次/已入圆桌/已发布/待停售数，可点击跳转）
  - 今日焦点（最多 3 场，普通用户 vs 管理员展示不同信息）
  - 圆桌与数据状态（最近阶段/Provider 可用数/同步新鲜度）
  - 我的关注（无关注时引导去竞猜赛程）
  - 管理员待办（仅管理员：待发布/待裁定赛果/同步失败/待确认方法论提议）
- [ ] **Step 3: 全局数据新鲜度指示器** — 右上角「已同步 · HH:MM」/「数据可能滞后」（>60min赭金）/「数据过期>24h」（红色）
- [ ] **Step 4: 全局异常降级横幅** — 后端不可用/AI不可用/数据源过期三种全局状态（PRD §5.2）

---

## 阶段 3：数据与规则底座

### Task 3.1: 竞彩方案浏览器端计算引擎

**Files:**
- Create: `web/src/lib/calculator/rules.ts` (版本化规则配置)
- Create: `web/src/lib/calculator/engine.ts` (纯函数计算)
- Create: `web/src/lib/calculator/__tests__/engine.test.ts`
- Create: `api/app/calculators/sporttery_calc.py`
- Create: `api/tests/test_calculator_golden.py`

- [ ] **Step 1: TS 引擎** — validateCombo → calcCombinations → 注数/金额/最高奖金
- [ ] **Step 2: Python 等价实现**（用于 AI 组单校验、模拟盘、发布质检）
- [ ] **Step 3: Golden/property test（TECH §13 强制范围）** — 使用权威预期结果的 fixtures（从体彩官方规则文档推导的手算结果），覆盖：五种玩法基础计算/复式/过关（2串1~8串1）/自由过关/设胆/`M串N`（4串11等）/各玩法动态过关上限/金额舍入规则/单票奖金上限超限提示/无效场次逐组合去除后重新计算（非赔率1.0）/官方更正。TS/Python 两端使用同一 fixtures 且均须匹配权威预期值（仅两端互比不够，防止两端同错但误判通过）

---

### Task 3.2: 数据同步与来源管理

**Files:**
- Create: `api/app/datasources/contract.py`
- Create: `api/app/datasources/admin_import.py`
- Create: `api/app/datasources/evidence.py`
- Create: `api/app/routers/matches.py`

完整 `MatchDataService` + `SourcedFact` + `sync_runs`/`source_records` + 降级链（TECH §5.3）。Gate 0 期间只用 fixtures。

---

## 阶段 4：可恢复圆桌（核心模块）

### Task 4.1: 圆桌状态机与编排器

**Files:**
- Create: `api/app/orchestration/roundtable.py`（两层状态机，含方法论评审状态）
- Create: `api/app/orchestration/phases/select.py`
- Create: `api/app/orchestration/phases/predict.py`
- Create: `api/app/orchestration/phases/debate.py`
- Create: `api/app/orchestration/phases/vote.py`
- Create: `api/app/orchestration/phases/bet_form.py`
- Create: `api/app/orchestration/phases/bet_debate.py`
- Create: `api/app/orchestration/phases/bet_vote.py`
- Create: `api/app/orchestration/voting.py`
- Create: `api/app/orchestration/context.py`

- [ ] **Step 1: 两层状态机** — `RoundtableJobState` 枚举包含 TECH §5.9 的方法论评审专用状态（`independent_reviewing`/`review_debating`/`review_voting`/`pending_admin_confirmation`）+ 预测任务状态 + 通用终态；`MatchRunState` 独立管理。数据库 CHECK 约束按 `job_type` 校验合法状态集合。
- [ ] **Step 2: 加权投票与法定人数校验（PRD §15.1 完整合同）** —
  - 法定人数：有效参与实例 ≥3 且 ≥2 厂商；不足则标记 `no_quorum`
  - 选场入围：加权 yes 票占比严格 `>50%`；恰为 50% 不入围；超上限时按加权 yes 占比 → 投票者方向置信度中位数 → 停售时间 → `match_id` 稳定截断
  - 比分平票：加权票并列时比较各候选投票者的终投方向置信度中位数；仍平则保留全部并列比分，标记「弱共识」
  - 方案平票：并列时比较方案置信度中位数；多个 `bet` 仍平则全部入选；若并列集合含 `no_bet` 与任一 `bet`，按保守规则以 `no_bet` 为平台结果，`bet` 候选仅留审计
  - 零场入围：合法终态，生成「今日休战」公告草稿
- [ ] **Step 3: 匿名辩论** — 代号分配、消息匿名化、shuffle_seed
- [ ] **Step 4: 单元测试** — 状态迁移、投票计算、法定人数、平票降级

---

### Task 4.2: Provider 统一接口（11 个方法）

**Files:**
- Create: `api/app/providers/contract.py`
- Create: `api/app/providers/capabilities.py`
- Create: `api/app/providers/openai.py`
- Create: `api/app/providers/anthropic.py`
- Create: `api/app/providers/google.py`
- Create: `api/app/providers/openai_compat.py`

- [ ] **Step 1: BaseProvider Protocol** — 覆盖 TECH §5.2 全部 11 个方法：

```python
class BaseProvider(Protocol):
    # 选场三阶段
    async def nominate_matches(self, ctx: SelectionContext, req: ProviderRequest) -> ProviderResult[SelectionNomination]: ...
    async def selection_debate(self, ctx: SelectionDebateContext, req: ProviderRequest) -> ProviderResult[SelectionDebate]: ...
    async def vote_matches(self, ctx: SelectionVoteContext, req: ProviderRequest) -> ProviderResult[SelectionVote]: ...
    # 比分三阶段
    async def predict_score(self, ctx: MatchContext, req: ProviderRequest) -> ProviderResult[ScorePrediction]: ...
    async def debate_response(self, ctx: DebateContext, req: ProviderRequest) -> ProviderResult[ScoreDebate]: ...
    async def vote_score(self, ctx: ScoreVoteContext, req: ProviderRequest) -> ProviderResult[ScoreVote]: ...
    # 组单三阶段
    async def form_bet(self, ctx: BetFormContext, req: ProviderRequest) -> ProviderResult[BetProposal]: ...
    async def debate_bet(self, ctx: BetDebateContext, req: ProviderRequest) -> ProviderResult[BetDebate]: ...
    async def vote_bet(self, ctx: BetVoteContext, req: ProviderRequest) -> ProviderResult[BetVote]: ...
    # 赛后复盘与方法评审
    async def review_prediction(self, ctx: PostMatchReviewContext, req: ProviderRequest) -> ProviderResult[ReviewAndLessons]: ...
    async def review_methodology(self, ctx: MethodologyReviewContext, req: ProviderRequest) -> ProviderResult[MethodologyReview]: ...
```

- [ ] **Step 2: 各厂商适配器** — OpenAI/Anthropic/Google 原生 + DeepSeek/Kimi/Qwen 兼容
- [ ] **Step 3: ProviderRequest 统一封装** — 必含字段（TECH §5.2 完整合同）：`request_id`、业务幂等键、`input_snapshot_id`、模型/连接/L1/L2/L6/输出 Schema/工具合同版本、超时与 token 上限。预测类任务额外携带历史上下文/教训集版本；复盘与方法评审任务分别携带 `postmatch_review_context_snapshot_id` / `methodology_review_context_snapshot_id`；不适用字段显式为 `null`（不得省略），确保调用审计和上下文还原

---

### Task 4.3: 分阶段上下文冻结与提示词组装

**Files:**
- Create: `api/app/orchestration/context.py`
- Create: `api/app/prompts/versions.py`
- Create: `api/app/prompts/assembly.py`

- [ ] **Step 1: 版本加载** — 从 `prompt_versions` 表按 key+version 加载
- [ ] **Step 2: 三阶段输入快照构建（协议 §5 + TECH §5.3）** —
  - **选场阶段（L4 selection）：** `build_selection_context(selection_scope_snapshot_id)` — 仅候选池摘要（match_id/赛事/时间/数据完整度/赔率摘要/缺失字段）；选场快照在开桌时创建、首次模型调用前冻结
  - **逐场预测阶段（L4 match）：** `freeze_match_context(job_id, match_id)` — 完整比赛上下文（对阵/赔率/近况/交锋/积分榜/伤停/首发）；在该场独立预测开始前创建、首次模型调用后锁定，所有参与实例使用同一快照
  - **组单阶段（L4 bet）：** `build_bet_context(bet_context_snapshot_id)` — 仅有效终投结论 + 冻结可售选项 + 风控限额；组单提案前创建并锁定
  - **冻结约束**：阶段内首次模型调用后不得刷新或替换快照；后续同步不能改变运行中或历史圆桌的输入上下文（TECH §5.3）
- [ ] **Step 3: 全桌冻结事务** — `create_roundtable()` 在同一事务中完成（协议 §6.4）：
  - 冻结参与者阵容 + 厂商家族 + `S`/`w_raw`/`w_i`（从当前 `score_formula_version` 计算快照）
  - 生成 `codename_seed` + `shuffle_seed` + `codename_map_version_id`
  - 创建选场范围快照 (`selection_scope_snapshot_id`)
  - 为每个实例生成 `history_context_versions`（含统计/校准/近期赛果渲染）和 `lesson_set_versions`
  - 记录冻结的：`provider_connection_version`、`model_id`、`generation_parameter_version`、`identity_prompt_version`、`core_methodology_version`、九阶段 `phase_prompt_versions`、`output_schema_versions`、`tool_contract_versions`、`sporttery_rules_version`、`score_formula_version`、`history_context_limits_version`
- [ ] **Step 4: 运行时组装** — `build_instance_context()` 按 7 层架构拼装 `PromptEnvelope`（L1–L7），严格区分可信指令层与不可信数据层，对不可信文本执行 Unicode 规范化/控制字符过滤/伪造角色标签过滤
- [ ] **Step 5: 方法论评审专用冻结**（TECH §5.9）— 发起方法论评审圆桌时额外冻结 `methodology_review_context_snapshot_id`：提议修订号、证据集合、OLD/NEW 完整文本、回测快照与结果、参与实例/票权、管理员补充材料及各自核验状态

---

### Task 4.4: 工具执行层（Layer 7 运行时实现）

**Files:**
- Create: `api/app/tools/contract.py`
- Create: `api/app/tools/execution.py`

- [ ] **Step 1: 工具实现** — `list_selection_candidates`、`get_match_data`、`get_team_current_season_stats`、`check_weather`、`calculate_ticket`
- [ ] **Step 2: 快照归属校验** — 所有工具调用必须校验快照归属、阶段和目标比赛；AI 不能作为权威参数源
- [ ] **Step 3: 组单前的强制 `calculate_ticket`** — 所有组单方案在进入匿名辩论和终投候选集前必须先通过确定性 `calculate_ticket`（协议 §3.8 跨字段校验约束）

---

### Task 4.5: Provider 结果业务校验器 + 事实声明核验

**Files:**
- Create: `api/app/orchestration/result_validator.py`（确定性跨字段校验，强制在所有结果入库前执行）
- Create: `api/app/orchestration/fact_verifier.py`

- [ ] **Step 1: 业务校验器（协议 §3.8 完整合同）** —
  - 比分推导方向一致性：`full_time_score` 必须推导出声明的 `direction`
  - 备选比分去重：不与首选重复，备选之间不互重复
  - 候选池归属：所有 `match_id` 必须属于冻结候选池
  - 来源/事实引用归属：所有 `source_record_ids`/`verified_fact_claim_ids` 必须属于冻结快照
  - 冻结赔率归属：所有 `offer_option_ids` 必须属于冻结赔率快照
  - 同场单玩法：同一方案内同一比赛只能一种玩法
  - `no_bet` 合同：`decision=no_bet` 时 `plan=null`（Schema 要求，无 `stake_percent` 字段）、`no_bet_reason` 非空；不得校验不存在的字段
  - 组单方案必须已通过 `calculate_ticket` 校验才能进入匿名辩论和终投候选集
  - 半场比分与半全场选择一致性（`half_time_score` ↔ `hafu` selection）
  - 自由文本中任何新事实性陈述必须先提取为 `fact_claim` 并完成核验，否则不得进入最终公开理由
  - 所有校验失败按阶段失败处理，禁止用正则从自由文本中"抢救"投票
- [ ] **Step 2: 事实声明核验状态机** — extracted → verifying → verified/unsupported/unavailable
- [ ] **Step 3: 安全同伴上下文构建** — 只保留已核验声明；未核验声明保留审计状态但不传播

---

### Task 4.6: Celery 任务、Dispatcher 与 Recovery

**Files:**
- Create: `api/app/workers/tasks.py`
- Create: `api/app/workers/dispatcher.py`
- Create: `api/app/workers/recovery.py`

- [ ] **Step 1: Celery 任务 + 执行审计** — 每个圆桌阶段一个任务，业务幂等键 `job_id:match_id:phase:round:instance_id`。
  - **审计创建时机（PRD §15.1 + TECH §5.5 精确合同）**：首份 AI 结果成功返回时在写入结果的事务中原子创建 `execution_audits` 根记录（不可删除）；若整个圆桌无任何 AI 成功返回结果（全部超时/系统故障/启动前终止），在任务进入 FAILED/TERMINATED 终态前补建审计根记录，标记原因「无成功AI结果」，同样不可删除。两条路径均生成终态公开审计投影（PRD 要求所有终态任务公开留痕）
  - **不可变追加**：`execution_audits` 创建后禁止 UPDATE；后续 attempt、超时、失败、跳过和人工终止通过追加 `roundtable_events`（类型化事件）和 `roundtable_phase_runs`（执行尝试记录）保存，不修改审计根记录。审计根记录写入规范化载荷哈希，可检测意外损坏（TECH §5.5 + PRD §17.4）
- [ ] **Step 2: Dispatcher** — 扫描 outbox_events，投递 Celery，更新投递状态（TECH §5.1 transactional outbox）
- [ ] **Step 3: Recovery scanner** — 超时 lease/未完成阶段/未派发 outbox 恢复

---

### Task 4.7: 推演直播与事件流（Realtime）

**Files:**
- Create: `web/src/components/prediction/debate-timeline.tsx`
- Create: `web/src/lib/realtime.ts`
- Create: `api/app/routers/roundtable.py`

- [ ] **Step 1: Realtime 订阅 hook** — 严格遵循 TECH §5.1 顺序：

```typescript
export function useRoundtableEvents(jobId: string) {
  // 1. 记录当前 last_event_seq
  // 2. 先订阅 private Broadcast channel，等待 SUBSCRIBED
  // 3. SUBSCRIBED 之后再补拉 event_seq > last_event_seq
  // 4. Broadcast 到达时按 event_seq 去重，跳号立即再次补拉
}
```

- [ ] **Step 2: 辩论时间线组件** — 聊天室形式，改票特殊样式，来源角标hover，阶段锚点导航
- [ ] **Step 3: 圆桌增益标注** — 回放头部「初稿→终投」变化摘要

---

## 阶段 5：公证、发布与结算

### Task 5.1: 公证账本

**Files:**
- Create: `api/app/orchestration/notarize.py`

- [ ] **Step 1: `notarize_roundtable()` 数据库函数** — 单事务内锁定/校验/写入/预留风险额度
- [ ] **Step 2: 公开投影生成** — `public_execution_audits`/`public_notarized_predictions`/`public_roundtable_events` 的生成函数（TECH §5.5）

---

### Task 5.2: 发布审核管理

**Files:**
- Create: `web/src/app/console/admin/publish/page.tsx`
- Create: `web/src/app/console/admin/roundtable/page.tsx` (发起推演双模式)
- Create: `web/src/app/console/admin/roundtable/[jobId]/page.tsx` (推演直播)
- Create: `api/app/routers/admin.py`（发布审核 API）

**实施步骤：**
- [ ] **Step 1: 发布质检** — 系统自动检查 PRD §15.3 完整清单（未达法定人数禁止、非法玩法组合禁止、距停售 <10min 禁止、同场次重复卡禁止、赔率过期 >60min 警告、无来源事实陈述警告、关键数据暂缺警告）；任一 🔴 项禁止发布
- [ ] **Step 2: 发布流程** — 二次确认：「发布后卡片锁定，仅可撤回下架」；发布后用户端可见 + 消息中心推送
- [ ] **Step 3: 撤回流程** — 已发布卡片可撤回下架，必须填写撤回原因；撤回后历史归档保留「已撤回」占位（含时间与原因，原内容可展开）；排行榜与模拟盘不受撤回影响（公证账本已锁定）
- [ ] **Step 4: 未发布记录自动公开** — 停售后，未发布但已公证的记录生成脱敏投影并对注册用户开放（PRD §15.3）；已发布记录立即开放投影；今日休战公告草稿发布/不发布、进入终态后始终提供审计投影
- [ ] **Step 5: 公证内容不可编辑** — 审核视图内容来自公证账本（比分、投票、方案、赔率快照、仓位），仅可添加管理员备注

---

### Task 5.3: 模拟盘结算引擎（完整状态机）

**Files:**
- Create: `api/app/routers/ledger.py`
- Create: `api/app/orchestration/settlement.py`

- [ ] **Step 1: 完整结算状态机**（PRD §17.11–12 + TECH §5.6）：

```text
waiting
  ├─ 部分场次完赛 → partially_settled
  ├─ 多源赛果冲突 → conflict_frozen（人工裁定前冻结）
  ├─ 体彩判定无效 → 从原过关组合去除该腿后重算（TECH §5.6 规则）
  ├─ 全部进入终态 → settled_hit / settled_miss / settled_refund
  └─ 体彩官方更正 → corrected（追加冲正分录，按原规则版本重算，保留原记录）
```

- [ ] **Step 2: 账户结算规则（PRD §11.1 完整合同）** —
  - 每个 AI 实例账户结算**该 AI 自己的终投方案**（无论是否胜出），反映「这个 AI 自己操盘」水平
  - 圆桌共识账户结算**方案终投胜出的平台最终方案**（共识账户曲线在盈亏页置顶）
  - 多个并列方案入选时：计算名义总投入（共识账户余额 × 目标仓位之和 vs 当日风险敞口剩余额度取小），按各卡终投加权得票比例分配；得票相同时等权分配
  - AI 或平台终投 `no_bet` 时写入零仓位决策记录，不扣款、不计为投入场次，但计入参赛覆盖率
- [ ] **Step 3: 账户分录** — 投入/返还/派奖/冲正分别追加（不可变 `account_entries`）；余额为可重建缓存
- [ ] **Step 4: 风控限额** — 单日 15%、同场 5%、超限按比例缩减（PRD §11.1）
- [ ] **Step 5: 结算幂等** — `(notarized_prediction_id, result_version)` 唯一约束
- [ ] **Step 6: 原子下游事务（TECH §5.6）** — 单次事务完成全部：写结算分录 → 更新余额缓存 → 更新卡片腿状态（已中/未中/待开/无效）→ 投递排行重算/通知/复盘 outbox。任一步失败整体回滚，杜绝资金已结算但卡片/排行/复盘未推进的裂缝

---

### Task 5.4: 预测排行（后端计算 + 前端展示）

**Files:**
- Create: `api/app/orchestration/rankings.py`（排行计算引擎）
- Create: `web/src/app/console/rankings/page.tsx`
- Create: `web/src/app/console/rankings/[aiId]/page.tsx`

**实施步骤：**
- [ ] **Step 1: 排行计算引擎（PRD §10.2 完整合同）** —
  - 只消费公证账本中已结算的逐场命中事实
  - 四维命中判定：比分（全场一致）、胜平负（由预测比分推导方向与赛果一致）、总进球（一致）、半全场（半场+全场方向组合一致）
  - 原始综合分 = 比分×40% + 胜平负×30% + 总进球×15% + 半全场×15%
  - 贝叶斯平滑：`S = (n × raw + C × μ) / (n + C)`，其中：
    - `C`（先验样本数）从当前 `score_formula_version` 加载，禁止硬编码
    - `μ`（全局先验均值）动态计算为同一公式版本下所有已有 ≥1 场已结算预测的实例的原始综合分平均值；仅当平台无任何已结算样本时，从公式版本读取冷启动先验（默认 50）
    - `n=0` 时 `S` 等于当前冻结的 `μ`
    - `M=0`（全体中位数为零）时所有实例 `w_raw = 1.0`（PRD §10.2）
  - 票权：`w_raw = clamp(S / 全体中位数, 0.75, 1.25)`，再经厂商家族归一化
  - 正式排名门槛：已结算 ≥10 场且参赛覆盖率 ≥80%（未达标标记「样本不足」/「覆盖率不足」）
  - 方向置信度校准：按方向置信度分桶（50-60%/60-70%…）对比实际方向命中率，偏差大者在卡片 hover 中提示
  - 历史榜单快照不可覆盖；不同公式版本的综合分不得混合平均
- [ ] **Step 2: 前端综合榜** — 维度切换（综合分/比分命中率/胜平负/总进球/半全场/收益率）、范围筛选（全部/近30天/近7天）、前三奖牌、近10场迷你色条、趋势箭头
- [ ] **Step 3: 前端模型档案** — AI 身份大头像 + 各维度分值徽章 + 模拟盘净值曲线 + 预测历史表 + 教训档案

---

## 阶段 6：前端页面实现

### Task 6.1: 营销首页

**Files:**
- Create: `web/src/app/(marketing)/page.tsx`
- Create: `web/src/components/marketing/hero-animation.tsx`
- Create: `web/src/components/marketing/feature-section.tsx`

参照原型 `index.html` + `alea.html` 实现 §6 全部内容。所有演示数据脱敏，使用 `index.html.artifact.json` 中已有的固定 fixtur，不请求真实 API。

---

### Task 6.2: 太玄问机 —— 产品核心页

**Files:**
- Create: `web/src/app/console/predictions/page.tsx`
- Create: `web/src/app/console/predictions/[id]/page.tsx` (推演详情/辩论回放)
- Create: `web/src/components/prediction/prediction-card.tsx` (四层结构 + 完整生命周期)
- Create: `web/src/components/prediction/vote-bar.tsx`
- Create: `web/src/components/prediction/consensus-ring.tsx`

---

### Task 6.3: 竞猜赛程

**Files:**
- Create: `web/src/app/console/fixtures/page.tsx`
- Create: `web/src/app/console/fixtures/[id]/page.tsx`
- Create: `web/src/components/fixtures/match-row.tsx`

---

### Task 6.4: 竞彩方案页

**Files:**
- Create: `web/src/app/console/calculator/page.tsx`（桌面三栏 + 移动端三步）
- Create: `web/src/components/calculator/match-selector.tsx`
- Create: `web/src/components/calculator/play-config.tsx`
- Create: `web/src/components/calculator/ticket-preview.tsx`
- Create: `web/src/components/calculator/ticket-card-image.tsx`（方案卡渲染 + 复制/下载）

必须覆盖：预算提醒（仅本地 localStorage）、过期赔率禁止出图（>24h）、采纳预测卡预填充、方案卡声明区（"本图非彩票、非投注凭证"）。

---

### Task 6.5: 盈亏账本

**Files:**
- Create: `web/src/app/console/pnl/page.tsx`
- Create: `web/src/components/charts/net-value-chart.tsx`
- Create: `api/app/routers/real_ledger.py`

模拟盘：股票风格净值折线图 + 汇总表。共识账户曲线置顶。

真实台账（仅管理员，PRD §11.2）：
- [ ] 管理员手动录入线下实际购票记录（关联公证卡可选、场次/玩法/倍数/金额、实际中奖金额）
- [ ] 真实盈亏折线图
- [ ] 记录编辑/删除使用冲正分录（不覆盖，保留操作日志）
- [ ] 汇总：总投入/总回收/净盈亏/命中率

---

### Task 6.6: 赛后复盘

**Files:**
- Create: `web/src/app/console/reviews/page.tsx`
- Create: `web/src/app/console/reviews/[id]/page.tsx`

---

### Task 6.7: 赛事资料

**Files:**
- Create: `web/src/app/console/wiki/page.tsx`
- Create: `web/src/app/console/wiki/[type]/[id]/page.tsx`

---

### Task 6.8: 系统管理套件

**Files:**
- Create: `web/src/app/console/admin/layout.tsx`
- Create: `web/src/app/console/admin/lineup/page.tsx` (模型阵容)
- Create: `web/src/app/console/admin/sync/page.tsx` (数据管理)
- Create: `web/src/app/console/admin/settings/page.tsx` (系统设置)
- Create: `web/src/app/console/admin/settings/methodology/page.tsx` (推演方法)
- Create: `web/src/app/console/admin/users/page.tsx` (用户管理)
- Create: `api/app/routers/admin.py`（统一管理 API：系统设置、用户管理、数据同步、赛果裁定、推演控制）

**实施步骤：**
- [ ] **Step 1: 版本化系统设置保存 API** — 五组设置分组保存（评分与规则/模拟盘与风控/数据与自动化/用户管理/提示词与方法论），每组独立保存按钮，覆盖未修改/存在未保存修改/保存中/已保存/保存失败+重试状态；切换分组/离开页面前未保存修改须确认（PRD §15.6）
- [ ] **Step 2: 用户管理 API** — 搜索/筛选/禁用/恢复用户，操作须二次确认并记录操作者与时间（PRD §15.6.4）
- [ ] **Step 3: 数据同步与赛果裁定 API** — 手动触发同步、同步日志查看/重试、赛果冲突列表、管理员裁定（裁定后才触发结算，PRD §15.5）
- [ ] **Step 4: 推演直播控制 API**（PRD §15.2）— 「跳过辩论直接终投」/「终止本场圆桌」受控 RPC：校验管理员身份→冻结已产生内容→写入不可删除审计→记录终止原因；前端不渲染按钮给非管理员
- [ ] **Step 5: 全部管理员操作写入 `admin_audit_logs`**（TECH §10.2）

---

### Task 6.9: 模型阵容安全后端（新增，PRD §15.4 + TECH §5.2）

**Files:**
- Create: `api/app/secrets/envelope.py`
- Create: `api/app/routers/admin.py` (provider/lineup 部分)

- [x] **Step 1: 密钥 envelope encryption** — AES-256-GCM，DEK/nonce 绑定 connection ID + 版本，DEK 由 KEK 包裹；密文入库；密钥读取 API 永不返回明文
- [ ] **Step 2: 模型目录代理** — FastAPI 代理厂商 API，按连接版本短期缓存，标记采集时间
- [ ] **Step 3: 连接测试** — 只验证认证/端点/模型最小能力；返回统一错误码，不暴露上游响应正文
- [x] **Step 4: SSRF 防护** — `api_url` HTTPS 限制 + 厂商域名白名单 + 重定向目标校验
- [ ] **Step 5: 管理员操作日志** — 密钥新增/轮换/停用均写入 `admin_audit_logs`
- [ ] **Step 6: 版本化阵容管理（PRD §15.4 完整合同）** —
  - 厂商 CRUD + 连接 CRUD（base URL/协议/模型/端点/密钥引用/版本号）
  - 实例 CRUD：每厂商 1–3 实例上限校验（服务端强制）、昵称、启用/停用、推理强度、超时/并发/调用策略（受系统上限约束）
  - 实例配置变化时标记该厂商所有依赖它的实例旧连接测试结果为「待重新测试」
  - 停用/不可用厂商的实例禁止被选入新圆桌（阵容冻结时校验）
  - 密钥清除操作 + 保存前校验必填项/上限/模型可用性/密钥状态
  - 所有变更写入 `admin_audit_logs`（操作者/时间/变更内容）

---

### Task 6.10: 消息中心与个人设置

**Files:**
- Create: `web/src/components/ui/notification-center.tsx`
- Create: `web/src/app/console/settings/page.tsx`
- Create: `web/src/app/console/settings/security/page.tsx`
- Create: `api/app/routers/settings.py`（改密码/OAuth绑定解绑/注销）

- [ ] **Step 1: 关注系统 API** — 关注/取消关注比赛和预测卡（「关注 ☆」按钮，唯一服务端用户行为数据）；个人设置中关注列表管理、一键取消关注
- [ ] **Step 2: 消息中心** — 铃铛入口 + 未读红点 + 近 20 条下拉 + 全部已读；三类通知（PRD §16.1）：
  - 全员新预测卡发布（用户可在偏好中关闭）
  - 已关注卡片开奖出结果 / 复盘发布（仅显式关注触发）
  - 管理员待办通知（圆桌完成待审核/同步失败/赛果冲突/草稿临期/方法论提议待审/评审待确认）
  - 串关卡片在所有腿进入终态后统一通知一次
- [ ] **Step 2: 个人设置后端** — 改密码、OAuth 绑定/解绑、注销（TECH §14 完整流程）：删除 Auth 用户 → 删除 profile + 关注 + 通知 + 通知偏好 → 系统审计主体替换为不可逆匿名标识（不保留邮箱/OAuth ID 等可识别信息）

---

## 阶段 7：调度、通知、复盘与方法论闭环

### Task 7.1: Celery Beat 定时任务

**Files:**
- Create: `api/app/workers/scheduler.py`

- [ ] 数据同步周期、定时圆桌（数据库 lease + `schedule_id + business_date` 唯一键）、自动复盘草稿、后台检查、misfire 策略

---

### Task 7.2: 消息通知系统

**Files:**
- Create: `api/app/orchestration/notifications.py`

- [ ] 通知生成/幂等键、已读/未读、用户偏好控制、串关终态统一通知（所有腿完赛后才通知）

---

### Task 7.3: 复盘自动生成与教训注入

**Files:**
- Create: `api/app/orchestration/reviews.py`

- [ ] **Step 1: 复盘上下文隔离** — 复盘调用前冻结 `postmatch_review_context_snapshot_id`（协议 §11.2 完整合同）：
  - 原公证预测记录（比分、投票、赔率快照）
  - 该预测当时的赛前 `input_snapshot`
  - 该预测当时的 `core_methodology_version`（冻结的方法论版本）
  - 该实例当时的 `lesson_set_version_id`（冻结的教训集合）
  - 核验后的 `roundtable_events`（圆桌事件记录）
  - 独立确认的 `result_version`（赛后确认赛果）
  - 赛后关键事件来源（进球时间线等，作为分析上下文）
  - 禁止查询当前方法论、后来新增 lesson、其他比赛赛果来改写"当时为什么这样判断"
- [ ] **Step 2: 复盘生成** — 赛后自动/手动触发 → 各 AI self-review → 汇总 → 管理员审核/发布 → 教训注入 L5
- [ ] **Step 3: 方法论发布单事务合同**（TECH §5.9）— 锁定提议行 → 校验回测通过 + 终投/人工绕过理由 + 管理员身份 + 预期当前方法论版本 → 在单个数据库事务同时：追加 `prompt_versions` 新版本 + 更新提议状态为 published + 写入审计日志。并发确认仅能成功一次。回滚不是把旧行改回当前，而是以目标历史内容追加新版本（含来源版本+差异+原因+管理员）

---

### Task 7.4: 方法论提议与评审闭环（修正版，TECH §5.9 + 协议 §11.4）

**Files:**
- Create: `api/app/orchestration/methodology.py`

- [ ] **Step 1: 提议生成** — 聚合已发布 active lessons，三个触发阈值（≥3 场不同比赛 或 ≥5 条相关 lesson 或 同 AI 连续 ≥5 场同类别犯错）及可选的 `lookback_days`（默认 `null` 即全部有效历史）均来自版本化配置 `system_setting_versions`；重复证据不生成重复提议；去重使用规范化模式哈希
- [ ] **Step 2: 回测（完整合同）** —
  - 样本 ≥20 场，且覆盖提议相关场景
  - OLD/NEW 使用完全相同的：比赛集合、输入快照、历史上下文版本、教训集版本、模型连接版本、参数、输出 Schema、工具快照、评价器版本
  - 每实例/版本 ≥2 次尝试（G4 中新增 Provider 重复调用方差实验以确定正式尝试次数；G4 通过前使用 `attempts=2` 作为安全下限）
  - 记录四维指标（精确比分/胜平负方向/总进球/半全场）+ 无效输出率 + 执行失败率
  - 提供配对差值与 paired bootstrap 95% 区间估计
  - 严禁向 OLD/NEW 任一分支泄露赛果或赛后信息
- [ ] **Step 3: 评审圆桌** — `job_type=methodology_review`，使用独立状态链（`independent_reviewing → review_debating → review_voting → pending_admin_confirmation → completed`），非支持/反对结果进入 `revise_and_review` 终态（当前方法论保持不变）
- [ ] **Step 4: 管理员直播干预**（PRD §15.7.2）—
  - **发表补充观点**：管理员补充内容以「管理员观点」标识注入 AI 下一条消息；事实性陈述仍须绑定来源并核验；可在同一评审继续讨论
  - **要求展开说明**：管理员选择某个 AI 后要求其展开说明某条推理
  - **采纳为提议修改方向**：管理员选择某条评审结论后点击「采纳为下一修订方向」；一旦修改提议正文即立即结束当前 run，保存为新修订并重新回测，通过后另起新的评审圆桌。禁止让旧回测继续支撑新文本
  - **结束辩论直接裁定**：填写理由后直接终止当前评审并进入待管理员确认；理由写入审计
  - **跳过 AI 讨论直接修改方法论**：管理员可以直接编辑方法论并发布新版本，必须填写理由（禁止留空）并写入审计记录
- [ ] **Step 5: 管理员确认** — 支持 ≥60% → 待管理员确认发布；反对 ≥60% → 已驳回归档；其余 → `revise_and_review`（提示管理员补充材料或调整提议，保存为新修订后重新回测）
- [ ] **Step 6: 版本发布与回滚** — 非破坏性追加新版本；回滚以目标历史内容追加新版本（含来源版本、差异、原因和管理员）

---

## 阶段 8：上线运维

### Task 8.1: E2E 测试与质量门禁

**Files:**
- Create: `tests/e2e/playwright.config.ts`
- Create: `tests/e2e/main-flow.spec.ts`
- Create: `tests/e2e/failure-branches.spec.ts`
- Create: `tests/e2e/methodology-flow.spec.ts`
- Modify: `Makefile`（添加 `make test-e2e` target）

- [ ] **Step 1: E2E 依赖与配置** — 安装 Playwright，配置 base URL、viewport（1440×900 + 390×844）
- [ ] **Step 2: P0 主链 — 三个独立 fixture 场景**（PRD §5.3 数据合同 + TECH §13）—
  - **场景 A（当前事实缺失态）**：使用 `待竞彩销售数据确认` 缺失态 fixture。验证：①预测卡正常展示（`西班牙 2:1 阿根廷`/`5/7`/`71%`/`AI 推演数据` 标记/`待赛果确认` 状态）；②竞彩方案中采纳按钮、生成方案卡、复制、下载 PNG 均被禁止（过期/缺失赔率规则，PRD §5.2）；③禁止原因有明确文字提示
  - **场景 B（交互样例 · 非体彩 SP）**：使用独立的 `交互样例 · 非体彩 SP` 标记 + 固定非官方参数 fixture。验证：①管理员发起推演 → 推演直播实时流（阶段进度条/选场提名/辩论消息追加/AI状态徽章/匿名代号）→ 首份 AI 结果触发审计创建 → 「跳过辩论直接终投」→ 公证入账 → 发布审核；②用户端推演卡片 → 采用按钮可用 → 竞彩方案预填充 → 方案卡出图（含声明区 `本图非彩票、非投注凭证` + 复制/下载）；③断线重连（关闭 Realtime 5s→重连→补拉 event_seq 连续无丢失）
  - **场景 C（结算/盖章）**：使用独立的确定性测试赛果 fixture（不与当前事实记录混合）。验证：赛果确认 → 卡片盖章归档（命中 ✓/未中 ✗）→ 模拟盘结算 → 排行榜更新
  - **三个场景共用**：PRD §5.3 的演示数据合同核心值（`西班牙 2:1 阿根廷`/`5/7`/`71%`），但场景 A 使用缺失态标记，场景 B 使用 `交互样例` 标记，场景 C 使用独立测试记录
- [ ] **Step 3: 失败分支** — 零场入围公告、终投前终止、Provider 部分失败、多场部分成功、`no_bet`、未发布公证记录停售后公开、数据冲突、撤回、过期赔率禁止出图
- [ ] **Step 4: 方法论 P1 流程** — 单独 E2E 验收
- [ ] **Step 5: 数据库迁移门禁** — 在空库和上一版本快照上各执行一次迁移并通过 RLS 测试（TECH §13）
- [ ] **Step 6: 密钥安全门禁** — 密文篡改失败、错误 KEK 失败、轮换可回滚、备份中无 KEK 明文（TECH §13 + TECH §5.2）
- [ ] **Step 7: 接入 `make check`** — E2E 作为 `make test-e2e` target，`make check` 包含 format-check + lint + typecheck + unit test + golden test + contract test；CI 执行 `make check` 作为合并准入
- [ ] **Step 8: 视觉与无障碍验收（DESIGN.md §Responsive Acceptance + PRD §5.2 无障碍）** —
  - **全部路由**（P0/P1/P2）在 1440×900 和 390×844 两个视口下的逐页截图对比（视觉回归）；P1/P2 同样执行页面横向滚动零容忍 + 弹层溢出检查
  - 44×44px 触控区覆盖检查（图标按钮最小触控热区）
  - 键盘导航完整性：hover 浮层支持键盘焦点与触屏展开；弹层焦点管理
  - 色彩对比度 WCAG AA（命中/未中须同时有图标；盈/亏同时有文字标识）
  - 动态状态文字描述（倒计时/辩论直播不纯依赖动画）
  - 路由状态矩阵台账（每个路由：加载骨架屏/空数据/同步中/数据过期/部分失败/无权限六种状态）

---

### Task 8.2: 可观测性、备份恢复与部署

**Files:**
- Create: `api/app/observability.py`（结构化日志 + request_id/job_id/provider_request_id 贯穿）
- Create: `docs/deployment.md`
- Create: `scripts/deploy.sh`

- [ ] **Step 1: 生产基础设施**（TECH §12）— TLS 终止（Nginx/负载入口）、正式域名 OAuth Site URL/Cookie domain/CORS/Redirect URL 配置、非 root 用户容器、只读镜像层、最小网络权限
- [ ] **Step 2: Staging promotion** — staging 环境先行部署 → 迁移执行 → `make check` + E2E → Provider smoke (fake) → 审批 → production deploy
- [ ] **Step 3: Production deploy + smoke** — 兼容迁移 → API/Worker/Dispatcher/Scheduler 部署 → Web 部署 → 健康检查 → 登录 → 管理员权限 → 数据同步 → 圆桌最小任务(fake provider) → Realtime 补拉 → 结算 smoke
- [ ] **Step 4: Rollback rehearsal** — 应用版本回滚演练 + 数据库迁移预案（TECH §12）
- [ ] **Step 5: 可观测性** — 结构化日志（`request_id`/`job_id`/`provider_request_id` 贯穿）、核心指标、关键告警
- [ ] **Step 6: 备份恢复** — 每季度隔离恢复演练、每周加密离站逻辑备份、Storage 对象单独备份（manifest/hash 校验）
- [ ] **Step 7: 数据保留与合规** — 日志/Provider 输出保留期；购彩法规/未成年人/隐私/第三方数据许可专项审查（TECH §14 + PRD §19.4）

---

## 实施顺序

```
Task 0.1 → 0.2 → 0.2b → 0.3  (基础设施 + Gate 0 迁移与 seed)
   ↓
Task 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7  (Gate 0，全部通过才继续)
   ↓
Task 0.2c  (正式业务迁移 00004，Gate 0 通过后执行)
   ↓
Task 2.1 → 2.2 → 2.3  (安全骨架)
   ↓
Task 3.1 → 3.2         (数据与规则)
   ↓
Task 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7  (可恢复圆桌，核心)
   ↓
Task 5.1 → 5.2 → 5.3 → 5.4  (公证与清算)
   ↓
Task 6.1–6.10          (前端页面 + 安全后端，可部分并行)
   ↓
Task 7.1 → 7.2 → 7.3 → 7.4  (调度与方法论)
   ↓
Task 8.1 → 8.2         (E2E 与上线，含全部失败分支)
```

Gate 0 依赖 Task 0.1–0.3 的最小迁移、fake provider 和 fixtures；Gate 0 通过前不进行其他业务功能开发（TECH §16）。

---

## 关键技术风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 体彩数据源未获授权 | 无法获取真实赔率/赛果 | Gate 0 使用 fixtures；生产前必须解决授权；支持人工导入降级 |
| Provider 结构化输出不稳定 | AI 返回不符合 Schema | G4 fake provider + 真实 vendor capability test 先行 |
| 多 Provider 并发调用超时 | 圆桌中断 | Celery 超时+重试；缺席标记不阻塞其余；长/短任务分离 queue |
| Supabase Realtime 消息丢失 | 辩论回放不完整 | PG 事件表为事实源；先订阅后补拉顺序；按 event_seq 去重 |
| Celery 任务重复执行 | 重复扣款/重复公证 | 幂等键 + 数据库唯一约束 + 状态版本乐观锁 |
| 冷启动无历史数据 | 票权计算退化 | 贝叶斯平滑 + 冷启动先验 50 |
| 方法论自动修改引入偏差 | AI 自毁预测质量 | 回测 OLD/NEW 同条件 + ≥20 场 + 多次尝试 + 配对区间估计 + 管理员最终确认 |
| Provider 密钥泄露 | 安全事件 | Envelope encryption；KEK 仅 API/Worker；密钥 API 永不返回明文 |

---

## 需要用户提供的密钥与配置（已部分获得）

| # | 项目 | 状态 |
|---|---|---|
| 1 | Supabase 项目凭据 | ✅ 已从 .env 获取 |
| 2 | GitHub OAuth Client ID/Secret | ✅ 已从 .env 获取 |
| 3 | Google OAuth Client ID/Secret | ✅ 已从 .env 获取 |
| 4 | AI Provider API Keys | ✅ DeepSeek 已提供（密钥仅存于 .env）；执行 G4 前需至少再提供 1 个厂商（OpenAI/Anthropic/Kimi） |
| 5 | 数据库角色密码 | 🔧 通过 Supabase 管理面板创建 4 个自定义角色并生成密码，写入 .env |
| 6 | PROVIDER_KEK_V1 | 🔧 需生成：`openssl rand -hex 32`，写入 .env |
| 7 | 竞彩规则初始数据 | 🔧 从 https://www.sporttery.cn 和公开规则文档获取，录入为 `sporttery_rule_versions` 首版 |
