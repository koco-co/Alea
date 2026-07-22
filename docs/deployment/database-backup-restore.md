# Alea 数据库迁移、备份与恢复

本手册描述可迁移、可校验的操作，不规定额外保留周期。生产环境的 PITR 能力与可用窗口以所选 Supabase 套餐为准。

## 1. 应用数据库迁移

```bash
make db-push ENV=local
make db-push ENV=staging
```

生产执行前必须确认目标项目引用、备份可用性和变更窗口。任何环境都不得复用另一环境的数据库角色 DSN 或密钥。

## 2. 生成离站逻辑备份

1. 使用受控的只读/备份角色执行 `pg_dump --format=custom --no-owner --no-acl`，输出文件不得放入 Git 工作树。
2. 记录当前 `supabase_migrations.schema_migrations` 版本清单。
3. 单独导出 Supabase Storage 对象；数据库备份只包含对象元数据，不包含对象内容。
4. 为数据库归档、Storage 对象和 manifest 生成 SHA-256 校验值。
5. manifest 至少记录：导出时间、源环境、Postgres 版本、migration 版本、数据库归档文件、Storage 对象键/大小/哈希、工具版本和操作者。
6. 备份与解密材料不得位于同一信任域；日志不得包含数据库密码、JWT、Provider 密钥或 Storage 凭据。

## 3. 恢复到干净环境

1. 创建全新 Supabase/Postgres 目标，不连接现有生产业务。
2. 先应用仓库中的全部版本化 migration。
3. 使用 `pg_restore --clean --if-exists --no-owner --no-acl` 恢复业务数据；不得覆盖目标环境的密钥。Supabase 的 `auth` 管理表和迁移种子不能作为普通业务表盲目回灌：恢复时按 manifest/TOC 分层处理 `auth.users`、`auth.identities`、`profiles`、数据源及其业务记录，清除目标端对应的 Gate 0 种子后再恢复来源数据。
4. 按 manifest 恢复 Storage 对象并逐项校验大小与 SHA-256。
5. 重新注入自定义数据库角色密码、Provider KEK、OAuth 与运行时密钥。
6. 执行下列验证：
   - migration 版本一致；
   - 核心表行数与导出 manifest 一致；
   - 原始来源内容哈希、公证载荷哈希与 Storage 哈希一致；
   - `alea_api`、`alea_worker`、`alea_dispatcher`、`alea_scheduler` 权限和 RLS 越权测试通过；
   - 登录、数据 fixture 导入、Provider mock、最小圆桌、发布、公证、模拟账本与结算主链通过。

## 4. 恢复演练证据

上线前至少完成一次从离站备份恢复到干净环境的演练。证据记录：

- 源/目标环境标识（不含密钥）；
- 每条命令、开始/结束时间与退出码；
- 数据库、Storage、权限/RLS 和业务 smoke 的通过/失败/跳过数；
- 校验 manifest 与哈希结果；
- 未验证项、失败原因和修复动作。

演练失败时不得把“备份文件已生成”视为可恢复证明。

## 5. 2026-07-22 本地恢复演练

本次演练使用本地 Supabase 干净环境，只包含人工 Gate 0 fixture，不包含真实体彩销售数据或 Provider 明文密钥。

- 先通过全部 14 个版本化 migration 重建数据库，最高版本为 `20260722030000`（含排行榜真实结算空投影）。
- 逻辑归档为 custom format、`--data-only --no-owner --no-acl`，归档 SHA-256 为 `1b51c32c1c30b1c87f1cc06a41c42c5b6beef12f60a47928bb375e415da98bad`。
- 恢复没有直接回灌 Supabase Auth 审计表或迁移种子；按 TOC 分层恢复 `auth.users`/`auth.identities`，清除目标端自动创建的 Profile 与 Gate 0 数据源后恢复 `profiles`、数据源、同步批次、来源记录、比赛和赔率。
- 恢复后的核心数据与源库一致：`auth.users=2`、`profiles=2`、`matches=1`、`source_records=1`、`match_odds_snapshots=1`、`match_results=0`、有效管理员 Profile `1`。
- Storage 对象数为 0，因此对象导出与对象哈希校验记为“不适用（空桶）”，不是跳过非空对象。
- 恢复库执行 G1/G2 真实数据库验证：17 项通过、0 项失败、0 项跳过；迁移版本验证通过。

归档生成在 Git 工作树外的临时目录，未提交测试账户、密码、DSN、JWT、Provider 密钥或 KEK。生产演练仍须增加非空 Storage 对象的逐项导出与恢复校验。
