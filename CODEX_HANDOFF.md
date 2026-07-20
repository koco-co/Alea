# Alea 项目 — Codex 执行交接文档

## 项目概述

Alea 是一个面向中国体彩竞彩足球的多 AI 协作预测平台。多个 AI 模型独立预测、匿名辩论、投票收敛，产出可追溯、可复盘的预测卡片。

- **仓库**: https://github.com/koco-co/Alea
- **工作目录**: /Users/aa/WorkSpace/Projects/Alea
- **技术栈**: Next.js 16 (Bun) + FastAPI/Celery (uv) + Supabase PostgreSQL + Redis + Docker Compose
- **上游文档**: docs/产品需求文档.md (PRD v1.9), docs/技术架构设计文档.md (TECH v1.5), docs/提示词架构与辩论协议.md (v1.2), DESIGN.md
- **实施计划**: docs/superpowers/plans/2026-07-19-alea-full-implementation.md

## 当前完成状态

### 已生成代码（201 文件，~23,000 行）
- 完整的 Python 后端（FastAPI + Celery + Provider 适配器 + 编排引擎）
- 完整的 TypeScript/React 前端（Next.js App Router + 全部页面组件）
- Gate 0 数据库迁移（4 个 SQL 文件）
- 9 个共享 JSON Schema + 代码生成脚本
- Docker Compose 8 服务配置
- E2E 测试框架（Playwright）

### 已知 P0 问题（对抗性审查发现）
1. 缺少 `web/src/app/console/admin/roundtable/page.tsx` 和 `[jobId]/page.tsx`（发起推演页面）
2. 缺少 `web/src/app/console/admin/publish/page.tsx`（发布审核页面）
3. `web/src/app/console/predictions/[id]/page.tsx` 使用硬编码 events，需改为真实 API 调用
4. `api/app/main.py` 需要注入业务 gateway（Database/Datasource/ProviderFactory）
5. TypeScript 编译通过（0 错误），但 `make test` 因缺少锁文件无法运行

## 环境配置

### .env 文件中已有的配置
```
# Supabase
PROJECT_URL=https://qevyqgociclrqhglhqux.supabase.co
PUBLISHABLE_KEY=sb_publishable_...
SECRET_KEY=sb_secret_...
SUPABASE_DB_URL=postgresql://...

# 数据库角色（已创建）
DATABASE_URL_ALEA_API=postgresql://...
DATABASE_URL_ALEA_WORKER=postgresql://...
DATABASE_URL_ALEA_DISPATCHER=postgresql://...
DATABASE_URL_ALEA_SCHEDULER=postgresql://...

# AI Provider (目前仅 DeepSeek)
DEEPSEEK_API_KEY=sk-...

# OAuth
GITHUB_CLIENT_ID=... / GITHUB_CLIENT_SECRETS=...
GOOGLE_CLIENT_ID=... / GOOGLE_CLIENT_SECRETS=...
```

### 待补充的配置
- `PROVIDER_KEK_V1`: 运行 `openssl rand -hex 32` 生成
- 额外 Provider 密钥：OpenAI API Key, Anthropic API Key（用于 G4 contract test）
- 竞彩规则数据：从 https://www.sporttery.cn 获取五种玩法规则

## 立即执行的步骤

### Step 1: 启动 Docker 服务
```bash
cd /Users/aa/WorkSpace/Projects/Alea
docker compose up -d --build
```
等待所有 8 个服务健康检查通过（nginx, web, api, worker, worker-short, dispatcher, scheduler, redis）

### Step 2: 安装 Supabase CLI 并运行迁移
```bash
brew install supabase/tap/supabase
supabase login
supabase link --project-ref qevyqgociclrqhglhqux
make db-push ENV=local
```

### Step 3: 生成锁文件
```bash
cd api && uv lock && uv sync --locked
cd ../web && bun install
```

### Step 4: 验证服务
```bash
# 健康检查
curl http://localhost:3000/api/health
curl http://localhost:8000/health

# TypeScript 编译
cd web && bun tsc --noEmit
```

## P0 修复任务（按优先级）

### 修复 1: 创建发起推演页面
```bash
# 创建文件
web/src/app/console/admin/roundtable/page.tsx  # 双模式：自主推演(默认) + 指定选场
web/src/app/console/admin/roundtable/[jobId]/page.tsx  # 推演直播：阶段进度条 + 流式消息 + 熔断控制
```
参考 PRD §15.1-15.2 和原型 `docs/PrototypeDesign/open-design/alea-admin.html`

### 修复 2: 创建发布审核页面
```bash
web/src/app/console/admin/publish/page.tsx  # 草稿列表 + 质检清单 + 发布/撤回 + 今日休战
```
参考 PRD §15.3

### 修复 3: 修复推演详情页
`web/src/app/console/predictions/[id]/page.tsx`:
- 删除硬编码的 `events` 数组
- 改为 `fetch(/api/roundtable/${id}/events)` 调用
- 使用 `useRoundtableEvents` hook（已存在于 `web/src/lib/realtime.ts`）

### 修复 4: API Gateway 注入
`api/app/main.py`:
- 创建 `DatabaseGateway`（Supabase client + 数据库角色连接池）
- 创建 `ProviderFactory`（从 `ai_instances` 表读取配置，实例化对应 Provider）
- 注入到所有路由的 `app.state`

## 验证清单

### Gate 0 验证
```bash
# G1: 认证/RLS
pytest api/tests/test_g1_auth_rls.py -v

# G2: Realtime
pytest api/tests/test_g2_realtime.py -v

# G3: Celery 恢复
pytest api/tests/test_g3_celery_recovery.py -v

# G4: Provider Contract（需要真实 API key）
pytest api/tests/test_g4_provider_contract.py -v

# G5: 数据源与规则
pytest api/tests/test_g5_data_rules.py -v
```

### 前端视觉验证
```bash
cd web && bun dev
# 打开 Chrome，逐一检查:
# http://localhost:3000/                    营销首页
# http://localhost:3000/login               登录
# http://localhost:3000/signup              注册
# http://localhost:3000/console             每日总览
# http://localhost:3000/console/predictions 太玄问机
# http://localhost:3000/console/fixtures    竞猜赛程
# http://localhost:3000/console/calculator  竞彩方案
# http://localhost:3000/console/admin/lineup 模型阵容
```

### E2E 测试
```bash
cd tests/e2e
npx playwright install
npx playwright test
```

## 项目结构速览

```
Alea/
├── api/                          # Python 后端
│   ├── app/
│   │   ├── main.py               # FastAPI 入口（需注入 gateway）
│   │   ├── middleware.py          # JWT + CORS + 限流
│   │   ├── orchestration/        # 核心编排
│   │   │   ├── roundtable.py     # 两层状态机
│   │   │   ├── voting.py         # 加权投票
│   │   │   ├── settlement.py     # 结算引擎
│   │   │   ├── rankings.py       # 排行引擎
│   │   │   ├── notarize.py       # 公证入账
│   │   │   ├── methodology.py    # 方法论闭环
│   │   │   ├── reviews.py        # 复盘+教训
│   │   │   ├── notifications.py  # 通知系统
│   │   │   ├── result_validator.py # 跨字段校验
│   │   │   ├── fact_verifier.py  # 事实核验
│   │   │   ├── context.py        # 上下文冻结
│   │   │   └── phases/           # 7个阶段实现
│   │   ├── providers/            # AI 厂商适配器
│   │   ├── routers/              # API 路由
│   │   ├── workers/              # Celery 任务
│   │   ├── prompts/              # 提示词组装
│   │   ├── tools/                # 工具执行层
│   │   └── datasources/          # 数据源
│   └── tests/                    # 测试文件
├── web/                          # TypeScript 前端
│   └── src/
│       ├── app/                  # App Router 页面
│       │   ├── (marketing)/      # 营销首页
│       │   ├── (auth)/           # 登录/注册
│       │   ├── console/          # 控制台全部页面
│       │   └── api/              # Next.js API routes
│       ├── components/           # React 组件
│       ├── lib/                  # 工具库
│       │   ├── supabase/         # Auth 客户端
│       │   ├── calculator/       # 竞彩计算引擎
│       │   └── realtime.ts       # Realtime hook
│       └── generated/            # 从 Schema 生成的类型
├── shared/schemas/               # 前后端共享 JSON Schema
├── supabase/migrations/          # 数据库迁移
├── tests/e2e/                    # E2E 测试
├── docker-compose.yml            # 8 服务编排
└── Makefile                      # 统一命令入口
```

## 关键命令

```bash
make bootstrap          # 安装依赖 + 锁文件检查
make dev                # 启动全部服务
make dev-down           # 停止服务
make db-push ENV=local  # 推送数据库迁移
make test               # 运行单元测试
make test-e2e           # 运行 E2E 测试
make check              # format + lint + typecheck + test
```
