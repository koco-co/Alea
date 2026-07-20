# Security Policy

## Reporting

请不要在公开 Issue 中披露漏洞、密钥或用户数据。使用 GitHub Security Advisory 的私密报告入口联系维护者。

## Secret handling

- `.env` 权限必须为 `0600` 且不得提交。
- 浏览器只接收 Supabase publishable key；secret key、数据库 DSN 与 Provider KEK 仅进入所需服务端。CLI 使用自身登录状态，Alea 不保存 CLI 账号密码或伪 API Key。
- CLI 路径必须是管理员配置的绝对可执行文件路径；调用使用固定参数数组和直接子进程，禁止 shell 拼接、任意命令、脚本与用户自定义启动参数。
- Provider 明文密钥不得返回 API、写日志或进入 Git；数据库仅保存 envelope ciphertext、wrapped DEK、nonce、KEK version 和尾号。
- 泄漏后应立即撤销/轮换凭据并检查日志、构建产物、Git 历史和备份。

当前没有承诺的安全支持版本；部署者必须自行跟踪依赖和平台安全更新。
