# Alea PRD v1.9 最终生产回归证据

日期：2026-07-19

验收视口：桌面 `1440×900`；移动 `390×844`

## 路由证据

每个编号均有一张 `desktop-<编号>-<名称>.png` 与一张 `mobile-<编号>-<名称>.png`。

| 编号 | 路由 / 状态 |
|---|---|
| 01 | 启动器 `/` |
| 02 | 营销首页 |
| 03–05 | 登录、注册、找回密码 |
| 06–08 | 每日总览、竞猜赛程、赛事详情 |
| 09–10 | AI 排行、AI 实例主页 |
| 11–12 | 用户模拟盈亏、管理员真实盘 |
| 13–16 | 复盘、赛事资料、西班牙身份、阿根廷身份 |
| 17–18 | 消息中心、账户设置 |
| 19–22 | 今日推演、历史推演、生命周期、已结算 |
| 23–24 | 竞彩方案事实态、P0 交互样例 |
| 25–34 | 发起、直播、发布、发布阻断、阵容、同步、设置、方法论、用户管理、已终止 |

结果：

- 桌面：34/34 无页面级横向溢出、broken image、空白、加载卡死或错误焦点。
- 移动：34/34 无页面级横向溢出、broken image、空白、加载卡死、错误滚动或错误焦点。
- `desktop-metrics.json`、`mobile-metrics.json` 保存每个路由的 URL、标题、视口、滚动尺寸、图片与焦点结果。
- `desktop-contact-1.png` 至 `desktop-contact-5.png`、`mobile-contact-1.png` 至 `mobile-contact-5.png` 已逐张打开检查。

## 交互证据

| 文件 | 动作与观察 |
|---|---|
| `35-messages-unread-filter-1440x900.png` | 未读筛选只显示 2 条未读消息 |
| `36-messages-empty-1440x900.png` | 全部标为已读后显示消息空态，通知按钮同步为无未读 |
| `37-account-avatar-failure-1440x900.png` | 模拟头像加载失败并显示 Lucide 回退 |
| `38-account-no-avatar-1440x900.png` | 移除头像后显示无头像状态 |
| `39-account-upload-success-1440x900.png` | 通过真实文件选择器上传 512×512 本地头像成功 |
| `40-account-password-invalid-1440x900.png` | 密码表单错误反馈与 `aria-invalid` |
| `41-account-oauth-follow-empty-1440x900.png` | GitHub 本地绑定反馈；取消最后一个关注后显示空态 |
| `42-account-delete-invalid-1440x900.png` | 删除确认输入不匹配时阻止继续 |
| `43-account-delete-valid-1440x900.png` | 有效确认只产生本地原型反馈，不冒充服务端删除 |
| `44-console-notification-popover-1440x900.png` | 通知弹层、消息中心深链、Escape 焦点返回 |
| `45-predictions-account-popover-1440x900.png` | 预测页账户菜单连接账户设置与退出 |
| `46-admin-account-popover-1440x900.png` | 管理壳账户菜单保留 `role=admin` |
| `47-console-mobile-drawer-390x844.png` | 移动抽屉无横向溢出，Escape 返回触发按钮 |
| `48-messages-empty-390x844.png` | 移动消息空态完整可见 |
| `49-account-avatar-failure-390x844.png` | 移动头像失败状态与回退 |
| `50-account-delete-dialog-390x844.png` | 删除对话框完整位于 390×844 视口内 |

结构化结果见 `interaction-results-desktop.json`、`interaction-results-cross-mobile.json`。交互联系表 `interaction-contact-desktop.png`、`interaction-contact-mobile.png` 已打开检查。

## 可访问性与触控

- `a11y-control-audit.json`：34 个路由 × 2 个视口。
- 当前可见无名按钮：0。
- 当前可见无标签输入、选择框或文本域：0。
- 小于 44×44px 的当前可见按钮：0。
- `affected-touch-desktop.png`、`affected-touch-mobile.png` 覆盖阶段标签、赛事筛选、详情标签、投票头像、关注和阵容模型选项的修正后视觉结果。

## 边界

- 未执行真实读屏器组合测试，不声明完整 WCAG 合规。
- OAuth、邮件、厂商 API、赛事 / 竞彩 / 阵容数据源、任务执行器、服务端持久化、系统分享最终发送与外部通知未连接；原型只给出明确的本地反馈、空态、失败态或禁用原因。
- 厂商标识的商业商标授权仍需产品方确认，不能据此声明可直接商业发布。
