# Alea

Alea 是竞彩足球多 AI 协作预测与复盘平台。它把赛前数据快照、多个 Provider 的独立判断、匿名辩论、终投、公证、模拟盘结算和赛后复盘串成可追溯流程。

> 本项目只用于研究与娱乐展示，不构成投注建议；未取得授权的体彩销售数据、赔率和赛果必须显示“暂缺/待官方确认”。

## 本地开发

要求：Python 3.12、uv、Bun 1.3.10、Docker、Supabase CLI 2.109.1。只有验证本地 CLI 连接时才需要安装对应 CLI；Alea 不扫描 `PATH`。

```bash
chmod 600 .env
make env-check
make bootstrap
make dev
```

根 `.env` 使用 `PROJECT_URL`、`PUBLISHABLE_KEY`、`SECRET_KEY`、`PROVIDER_KEK_V1`，以及数据库迁移和四个最小权限服务角色的 DSN。不要把密钥复制进 Web 配置或提交到 Git。

常用检查：

```bash
make check
make db-push ENV=local
make db-push ENV=staging
```

产品行为以 `docs/产品需求文档.md` 为准，架构以 `docs/技术架构设计文档.md` 为准，视觉规则以 `DESIGN.md` 为准。

## 当前边界

- 有且仅有一个真实 Provider 时，圆桌必须进入 `no_quorum`。
- 模型阵容同时管理 API 厂商与管理员指定绝对路径的 CLI 工具；不部署独立 runner daemon。
- 未确认许可前 Sporttery Web Source 保持禁用，历史数据验证只使用明确标注的竞彩足球 fixture。
- 数据库与 Storage 的迁移、离站备份及干净环境恢复见[备份恢复手册](docs/deployment/database-backup-restore.md)。
- 仓库默认不附加 LICENSE；第三方参考见 `docs/THIRD_PARTY_REFERENCES.md`。
