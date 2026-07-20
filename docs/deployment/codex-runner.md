# Codex runner 生产部署

本手册只描述 Alea runner 的生产配置。未在目标 Linux 主机完成 systemd smoke
前，不得把配置文件存在表述为生产验证通过。

## 专用账户与目录

```bash
sudo useradd --system --create-home --home-dir /var/lib/alea-codex \
  --shell /usr/sbin/nologin alea-codex
sudo install -d -o alea-codex -g alea-codex -m 0700 \
  /var/lib/alea-codex/.codex /etc/alea
```

将项目发布到 `/opt/alea/current`。`/etc/alea/codex-runner.env` 权限必须为
`0600`，至少包含随机生成的 `ALEA_RUNNER_TOKEN`、固定模型白名单
`CODEX_MODELS` 与独立的 `CODEX_HOME=/var/lib/alea-codex/.codex`。不要把
Supabase secret key、Provider API key 或业务数据库 DSN 写入 runner 环境。

## 无头登录

临时把专用账户 shell 调整为允许运维登录的 shell，在受控终端执行：

```bash
sudo -u alea-codex env CODEX_HOME=/var/lib/alea-codex/.codex \
  codex login --device-auth
sudo -u alea-codex env CODEX_HOME=/var/lib/alea-codex/.codex codex login status
```

完成后恢复 `/usr/sbin/nologin`。认证文件必须归 `alea-codex` 所有且不可被
其他账户读取；不要复制个人开发机的 `CODEX_HOME`。

## systemd

安装并检查仓库提供的单元：

```bash
sudo install -o root -g root -m 0644 \
  deploy/systemd/alea-codex-runner.service \
  /etc/systemd/system/alea-codex-runner.service
sudo systemctl daemon-reload
sudo systemctl enable --now alea-codex-runner
sudo systemctl status alea-codex-runner --no-pager
```

API 只能通过受控网络访问 runner，且每次请求都携带
`Authorization: Bearer <ALEA_RUNNER_TOKEN>`。防火墙不得向公网暴露 runner
端口。

## Smoke 与回滚

在目标主机执行并保存脱敏输出：

1. `GET /health` 返回 `status=ok` 且 `codex_available=true`。
2. 带 token 的 `GET /models` 只返回配置白名单内模型；无 token 返回 401。
3. 调用一次固定 Schema 的 `POST /internal/v1/execute`，确认结构化输出、
   token 统计和无工具事件。
4. 非法模型、前导 `-`、坏 Schema 与超时请求均被拒绝。
5. `journalctl -u alea-codex-runner` 不含 prompt、认证材料或模型正文。

回滚时恢复上一版本 `/opt/alea/current` 并重启单元。认证状态与
`ALEA_RUNNER_TOKEN` 不随代码回滚；疑似泄漏时必须单独轮换 token 并重新登录。
