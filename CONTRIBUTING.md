# Contributing

1. 先阅读 `AGENTS.md`、PRD、技术架构和 `DESIGN.md`。
2. 新行为必须同步 PRD；共享视觉规则同步 `DESIGN.md`；原型变更更新 route/state matrix。
3. 不提交 `.env`、数据库 DSN、Provider 密钥、token、生产数据或未授权体彩数据。
4. 安装必须使用锁文件；提交前运行 `make check` 和受影响的生产构建/浏览器验证。
5. Pull Request 说明执行范围、命令、exit code、passed/failed/skipped 数和未验证项。

提交应聚焦、可回滚，并保留用户已有的未相关改动。
