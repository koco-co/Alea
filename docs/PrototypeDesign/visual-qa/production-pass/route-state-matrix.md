# Alea PRD v1.9 路由 / 状态追踪矩阵

基线日期：2026-07-19

产品真源：`docs/产品需求文档.md` v1.9

视觉真源：`DESIGN.md`（Alea Production Prototype Content 及其后续规则优先）

仓库镜像：`docs/PrototypeDesign/open-design/`

OpenDesign 项目：`c73b3011-35b7-4a7a-a8e9-a22f12257c20`

正式证据：`docs/visual-qa/prd-v1.9-final-20260719/`

最终全量复核：`docs/visual-qa/prd-v1.9-final-20260719/final-production-20260719/`

结果定义：

- `通过`：本轮在 1440×900 与 390×844 均重新渲染，无页面级横向溢出，并有对应的新截图与交互证据。
- `部分通过`：页面与主要路径通过，但仍有明确的外部依赖、资产来源或未覆盖细节。
- `不适用 / 诚实空态`：PRD 路由存在，但由于可信业务数据尚未接入，当前正确结果是可恢复的空态或锁定态。

| PRD | 角色 | 路由 / 文件 | 关键状态与本轮操作 | 桌面 / 移动证据 | 结果 | 剩余边界 |
|---|---|---|---|---|---|---|
| §6 | 游客 | `/` · `index.html` | 入口、CTA、证据叙事、响应式 | `desktop/mobile-01-launcher.png` | 通过 | 无 |
| §6 | 游客 | 营销首页 · `alea.html` | 四阶段首屏、固定决赛身份、5/7 与 71% 一致性 | `desktop/mobile-02-marketing.png` | 通过 | 主视觉为生成资产，见资产台账 |
| §7 | 游客 | `alea-auth.html#login` | 邮箱密码、OAuth、无效凭据、回跳；产品界面隐藏测试填充按钮 | `desktop/mobile-03-auth-login.png` | 通过 | 外部 OAuth 仅原型反馈 |
| §7 | 游客 | `alea-auth.html#signup` | 18 岁与条款门槛、密码一致性、成功态 | `desktop/mobile-04-auth-signup.png` | 通过 | 外部注册服务未连接 |
| §7 | 游客 | `alea-auth.html#forgot` | 邮箱校验、发送成功、重新发送 | `desktop/mobile-05-auth-forgot.png` | 通过 | 邮件服务未连接 |
| §4、§5.3 | 用户 | `alea-console.html#overview` | 赛前简报、赛事事实、数据边界、移动导航 | `desktop/mobile-06-console-overview.png` | 通过 | 实时数据源未连接 |
| §8.1–8.2 | 用户 / 管理员 | `#fixtures` | 日期、状态、赛事、搜索、空态、重置 | `desktop/mobile-07-console-fixtures.png` | 通过 | 当前可信候选仅 Match 104 |
| §8.3 | 用户 / 管理员 | `#detail-final` | 深链、返回、5 个详情 Tab、销售/阵容/赛果锁定态 | `desktop/mobile-08-console-fixture-detail.png` | 通过 | 未接入字段保持空 |
| §9.1–9.3 | 用户 / 管理员 | `alea-predictions.html#today` | 七实例、5/7、5/1/1 票分布、Qwen 证据、五阶段回放 | `desktop/mobile-19-predictions-today.png` | 通过 | AI 内容为冻结原型输出 |
| §9.2、§9.4 | 用户 / 管理员 | `#history`、`#states`、`#settled` | 历史诚实空态、七生命周期组件、未赛赛事不生成结算 | `desktop/mobile-20–22-*.png` | 通过 | 实际历史与结算待公证账本 |
| §10.1–10.3 | 用户 / 管理员 | `#rankings`、`#rankings-claude-1` | 维度、范围、AI 详情、校准、历史/教训空态 | `desktop/mobile-09–10-*.png` | 通过 | 所有数值标明“AI 推演数据 / 非真实战绩” |
| §11.1 | 用户 / 管理员 | `#pnl` | 模拟账户、图例、范围、空态、角色隔离 | `desktop/mobile-11-console-pnl-user.png` | 通过 | 模拟曲线为交互规格演示 |
| §11.2 | 管理员 | `?role=admin#pnl` | 真实盘 Tab、空态、录入校验、新增、编辑入口、删除确认、只追加审计 | `desktop/mobile-12-console-pnl-admin.png` | 通过 | 初始无真实记录，不预填业务数据 |
| §12.1–12.3 | 用户 / 管理员 | `#reviews`、`#reviews-*` | 筛选、赛果未确认空态、无效深链恢复 | `desktop/mobile-13-console-reviews.png` | 不适用 / 诚实空态 | 官方赛果与真实复盘尚未产生 |
| §13 | 用户 / 管理员 | `alea-calculator.html`、`#sample` | 当前事实锁定、P0 样例深链、采用、玩法、预览、复制、PNG 下载 | `desktop/mobile-23–24-calculator-*.png` | 通过 | P0 样例明确非体彩 SP |
| §14.1 | 用户 / 管理员 | `#wiki` | 已确认身份列表；人物、积分、战绩 Tab 禁用并说明来源 | `desktop/mobile-14-console-wiki.png` | 通过 | 扩展资料源未接入 |
| §14.2 | 用户 / 管理员 | `#wiki-team-spain`、`#wiki-team-argentina` | 双队深链、返回、身份来源、名单/教练/战绩缺失卡 | `desktop/mobile-15–16-console-wiki-*.png` | 通过 | 国旗不冒充足协队徽 |
| §15.1 | 管理员 | `alea-admin.html#launch` | 双模式、范围、阵容、轮数、入围、定时、发起 | `desktop/mobile-25-admin-launch.png` | 通过 | 外部数据与任务执行器未连接 |
| §15.2 | 管理员 | `#live`、`#terminated` | 阶段流、七实例、事实核验、终止归档 | `desktop/mobile-26-admin-live.png`、`34-admin-terminated.png` | 通过 | 运行日志为冻结原型状态 |
| §15.3 | 管理员 | `#publish`、`#publish-blocked` | 质检、警告/阻断、只读预测、管理员备注 | `desktop/mobile-27–28-admin-publish*.png` | 通过 | 销售数据缺失时保持阻断 |
| §15.4 | 管理员 | `#lineup` | API 厂商 / CLI 工具双目录、密钥掩码、绝对路径、版本/认证、模型目录、连接测试、1–3 实例、真实保存/删除 | 待生成 Next.js `1440×900` / `390×844` 新鲜证据 | 待验证 | 旧截图只覆盖 API 厂商原型，不能作为双目录验收证据 |
| §15.5 | 管理员 | `#sync` | 今日/日期/比赛手动同步、部分失败、重试、只追加日志、冲突空态 | `desktop/mobile-30-admin-sync.png` | 通过 | 销售与阵容来源未连接 |
| §15.6 | 管理员 | `#settings`、`#users` | 5 分组、18 控件、搜索、校验、版本保存、状态筛选、停用二次确认与审计 | `desktop/mobile-31-admin-settings.png`、`33-admin-users.png` | 通过 | 后端持久化未连接 |
| §15.7 | 管理员 | `#methodology` | 真实提议空态、阈值、OLD/NEW 回测演示、演示发布不改生产版本 | `desktop/mobile-32-admin-methodology.png` | 通过 | 尚无已发布复盘生成真实提议 |
| §16 | 用户 / 管理员 | `#messages`、`#account`、顶栏弹层、移动抽屉 | 消息筛选/已读/空态；通知偏好、关注、密码、OAuth、删除；头像默认/上传/失败/无头像；角色入口隔离、Escape 焦点返回 | `desktop/mobile-17–18-*.png`、`35–50-*.png` | 通过 | 外部消息、密码、OAuth 与注销服务未连接，页面明确为本地原型反馈 |
| §5.2、§18 | 全角色 | 全局状态 | loading、empty、partial、error、permission、disabled、retry、焦点与 44px 触控 | `desktop/mobile-01–34-*.png`、`a11y-control-audit.json` | 通过 | 不代表真实读屏器组合或完整 WCAG 合规 |

## 本轮汇总

- 正式路由 / 页面：34 个（补入消息中心、账户设置与阿根廷身份详情）。
- OpenDesign 最终任务：`dc3a58ed-6778-462d-833b-bd9987f91c03`；自然结束，耗时 17 分 27 秒；结束后无活动任务、无排队消息。
- 双端新鲜路由截图：68 张（34 个路由 × 1440×900 / 390×844）；另有 16 张消息、账户、弹层、抽屉与焦点交互证据。
- 34/34 桌面与 34/34 移动页面级横向溢出：0。
- 34/34 桌面与 34/34 移动空白 / 加载卡死 / broken image：0。
- 当前可见表单缺失标签：0；当前可见无名按钮：0；小于 44×44px 的当前可见按钮：0。
- 冷启动路由标题错误聚焦：0；认证页与控制台的主动导航后标题聚焦均通过。
- 5 张桌面联系表、5 张移动联系表与 2 张触控修正检查表已逐张人工打开检查。
- 静态验证：仓库镜像为 `PASS 106 / FAIL 0`、退出码 `0`；OpenDesign 项目同步后的同值见最终审计。
- 关键一致性：发起推演显示 `7 个配置实例 · 7 个已启用`，不存在 `6 个已启用` 残留；预测页分列展示 `原始票 5/7` 与 `加权共识 71%`。
- 保存栏：模型阵容与系统设置在移动端均为文档流 `position: static`，不覆盖目录、表单或错误提示。

## 未验证或外部阻断

1. 真实 OAuth、邮件、厂商 API、赛事 / 竞彩 / 阵容数据源、任务执行器、服务端持久化、系统分享最终发送和外部通知服务未连接；原型保持明确空态、失败态或本地反馈。
2. AI 厂商标识的官方来源 / 商标使用边界尚未全部确认，详见 `asset-ledger.md`；因此不作“对外资产合规完成”或“可直接商业发布”声明。
3. 本轮完成了可见名称、标签、焦点、键盘路径与双视口检查，但没有执行真实读屏器组合测试，也不宣称完整 WCAG 合规。

## Next.js 前端实现增量（2026-07-20）

下表只记录 `web/` 实现状态；OpenDesign 既有截图不冒充 Next.js 实现截图。`docs/evidence/frontend-visual-20260720/` 为服务器静态渲染 HTML，仅用于结构检查，不构成浏览器视觉验收。

| PRD | 路由 / 入口文件 | 关键状态与交互 | 参考 | 本轮验证 | 剩余缺口 |
|---|---|---|---|---|---|
| §6 | `/` · `web/src/app/(marketing)/page.tsx` | 首屏动画、四段滚动叙事、CTA、页脚与风险文案 | `alea.html` | TypeScript、单测、生产构建、静态渲染通过 | 1440×900 与 390×844 新鲜截图及动画 / 锚点浏览器检查被本地端口权限阻断 |
| §9 | `/console/predictions`、`/console/predictions/[id]` | 四层推演卡、原始票与加权共识分列、七实例投票、五阶段辩论回放 | `alea-predictions.html` | TypeScript、单测、生产构建、静态渲染通过 | 双视口、hover / focus、详情导航与时间线浏览器检查待补 |
| §8 | `/console/fixtures`、`/console/fixtures/[id]` | 日期 / 状态 / 赛事 / 搜索筛选、重置、诚实空态、详情五 Tab | `alea-console.html` | TypeScript、单测、生产构建、静态渲染通过 | 双视口、筛选组合、5 Tab 与恢复路径浏览器检查待补 |
| §13 | `/console/calculator` | 事实态锁定、P0 非官方样例、三栏桌面、三步移动、复制、PNG 下载、声明区 | `alea-calculator.html` | TypeScript、单测、生产构建、静态渲染通过 | 双视口、移动三步、复制 / 下载与 Canvas 成图浏览器检查待补 |
