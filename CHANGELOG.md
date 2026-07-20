# Changelog

本文件遵循 Keep a Changelog 的组织方式；项目尚未发布稳定版本。

## Unreleased

### Added

- Codex CLI 隔离 runner、11 阶段 Provider adapter 与本地/生产启动配置。
- CLI/API Provider 执行模式和管理员模型阵容交互。
- Supabase 服务角色迁移、环境校验、Python/Bun 锁文件。
- 竞彩官方规则证据台账与 Python/TypeScript `half_even` golden tests。

### Changed

- uv 容器固定到 0.11.28，Bun 容器和项目声明固定到 1.3.10。
- Supabase 浏览器/API 变量显式映射自根 `.env`。

### Security

- 根 `.env` 要求 `0600`；Provider 密钥继续使用 AES-256-GCM envelope encryption。
