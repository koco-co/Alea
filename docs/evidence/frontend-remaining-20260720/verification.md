# Alea 剩余前端页面实现验证

日期：2026-07-20

## 本次路由

- `/console/pnl`
- `/console/reviews`
- `/console/reviews/:id`
- `/console/wiki`
- `/console/wiki/:type/:id`
- `/console/admin/lineup`
- `/console/admin/sync`
- `/console/admin/settings`
- `/console/admin/settings/methodology`
- `/console/admin/users`
- `/console/settings`
- `/console/settings/security`

顶栏同时接入消息中心、全部已读和通知直达，并将头像入口连接到个人设置。

## 可执行检查

| 检查 | 命令 | 退出码 | 结果 |
|---|---|---:|---|
| TypeScript | `node node_modules/typescript/bin/tsc --noEmit` | 0 | 通过 |
| 单元测试 | `TMPDIR=/tmp bun test` | 0 | 25 passed / 0 failed |
| Next 生产构建 | `ALEA_DEMO_ROLE=admin node node_modules/next/dist/bin/next build --webpack` | 0 | 23 / 23 路由生成成功 |
| ESLint | `node node_modules/eslint/bin/eslint.js src` | 1 | 跳过：当前 `node_modules` 缺少 ESLint 可执行模块 |

默认 Turbopack 构建在受限环境内尝试绑定内部端口并返回 `EPERM`；切换到 Next 官方 webpack 构建器后完整构建通过。

## 视觉与交互验证

未完成，不得视为视觉通过：

- `1440 × 900`：12 个路由均未获得新截图。
- `390 × 844`：12 个路由均未获得新截图。
- 本地 Next server 因沙箱禁止端口监听而返回 `listen EPERM 127.0.0.1:3100`。
- 浏览器安全策略禁止直接打开 `file://` 构建产物，因此没有用静态代码检查替代渲染证据。
- 消息中心开合、曲线显隐、筛选、保存状态、同步重试、用户二次确认和移动端重排尚待可运行浏览器环境逐项操作。

## 静态覆盖结果

- 12 个路由文件均进入 Next 路由清单。
- 动态详情路由使用 Next 16 异步 `params`。
- 管理员布局对非管理员回退到 `/console`。
- 赛事资料缺失源使用“暂缺/待同步”状态，没有生成虚构人物、头像或统计。
- API 密钥只显示掩码与尾号，没有前端明文状态。
