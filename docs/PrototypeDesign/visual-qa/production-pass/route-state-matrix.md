# Alea OpenDesign 生产验收路由/状态矩阵

基线日期：2026-07-19
产品真源：`docs/产品需求文档.md` v1.7
视觉真源：`DESIGN.md`
原型项目：`d99abbfa-a8d0-440e-a1aa-2b18b9926643`

状态说明：

- `未验收`：尚无本轮同视口、同状态的新截图和交互证据。
- `失败`：已确认缺页、空壳、死控件、错误语义或视觉问题。
- `通过`：本轮在 1440×900 与 390×844 均完成渲染、交互和截图检查。
- 当前表同时记录本轮修改前基线和已完成的正式验收；不复用 OpenDesign 项目中的旧 `qa/` 或 `.tmp/shots/` 截图作为本轮证据。

| PRD | 角色 | 路由/原型文件 | 入口 | 关键状态与交互 | 参考 | 本轮截图 | 结果 | 修改前剩余问题 |
|---|---|---|---|---|---|---|---|---|
| §6 | 游客 | `/` · `alea.html` | 直接访问 | 首屏动画四阶段、CTA、证据叙事、reduced motion | PRD §6、DESIGN | `screenshots/001-baseline-opendesign-home.jpeg` | 失败 | 全站仍使用“澜城竞技 vs 赤湾联”等玩具式赛事；与用户指定世界杯决赛语境不符 |
| §7 | 游客 | `/login` · `alea-auth.html#login` | 首页登录 | OAuth、邮箱密码、错误、回跳来源 | PRD §7 | 待截 | 未验收 | 暴露“填入演示账户”产品控件；需验证错误、加载和键盘路径 |
| §7 | 游客 | `/signup` · `alea-auth.html#signup` | 首页注册 | OAuth、18 岁、条款、校验、成功 | PRD §7 | 待截 | 未验收 | 暴露“演示：填入有效资料”；需验证双确认门槛 |
| §7 | 游客 | `/forgot` · `alea-auth.html#forgot` | 登录页 | 邮箱校验、发送中、成功、错误 | PRD §7 | 待截 | 未验收 | 未有本轮视觉证据 |
| §4、§16 | 用户/管理员 | 控制台框架 · `alea-console.html` | 登录回跳 | 九项一级导航、8 个 hover 副标题、默认落地、路由标题、消息中心、头像菜单、个人设置、角色差异 | PRD §3–4、§16 | `docs/PrototypeDesign/open-design/qa/shell-user-after-desktop.png`；`docs/PrototypeDesign/open-design/qa/shell-admin-after-desktop.png`；`docs/PrototypeDesign/open-design/qa/shell-navigation-functional.png`；`docs/PrototypeDesign/open-design/qa/shell-user-after-mobile.png`（旧移动证据） | 未验收 | 新增桌面用户/管理员壳层 1440×900 对比证据；聚焦报告图片显示其生成器范围 112/112，但本轮没有可重跑脚本，不能据此代表全站 E2E。管理员移动证据仍需重截，个人设置与完整角色外壳仍需逐项核验 |
| §4、§5.3 | 用户/管理员 | `/console` · `alea-console.html#overview` | 控制台默认入口/主导航“每日总览” | 赛前简报、赛事事实、固定 AI 原型输出、来源未连接、样本不足、桌面/移动导航、移动滚动末尾 | PRD §4、§5.3、DESIGN | `screenshots/007-console-overview-desktop-final.png`；`screenshots/006-console-overview-mobile-final.png`；`screenshots/005-console-overview-mobile-end-opendesign.jpeg` | 未验收 | 已有内容证据；导航改名后需重新截取桌面与移动证据 |
| §8.1–8.2 | 用户/管理员 | `/console/fixtures` · `alea-console.html#fixtures` | 主导航“竞猜赛程” | 日期、状态、赛事、搜索、空态、重置、Escape、管理员多选、键盘进入/返回 | PRD §8 | `screenshots/010-console-fixtures-desktop-final.png`；`screenshots/011-console-fixtures-mobile-final.png`；`screenshots/012-console-fixtures-functional-15-of-15.png` | 未验收 | 列表与筛选闭环已通过 15/15；导航改名后需重新截取桌面与移动证据 |
| §8.3 | 用户/管理员 | `/console/fixtures/:id` · `alea-console.html#detail-final` | 比赛行 | 竞彩、情报、预测、赛果、复盘 Tab；键盘左右/Home/End；返回/深链；移动首屏/末屏 | PRD §8.3 | `screenshots/015-console-fixture-detail-desktop-final.png`；`screenshots/016-console-fixture-detail-mobile-final.png`；`screenshots/017-console-fixture-detail-mobile-end-final.png` | 通过 | 五个 Tab、诚实数据空态、固定原型预测、赛果/复盘锁定态、桌面与移动净空已通过；不代表其他控制台路由通过 |
| §9.1–9.2 | 用户/管理员 | `/console/predictions` · `alea-predictions.html#today` | 主导航“太玄问机” | 今日推演、单场推演、关注、采用、停售 | PRD §9 | `screenshots/037-predictions-worldcup-mobile-final.png` | 未验收 | 已改为 Match 104 西班牙 vs 阿根廷，固定输出 2:1/半场 1:0/5–7/71%，全部标注 AI 推演数据；关注真实切换为 `Value: 1`，采纳/配置因销售数据缺失保持禁用。390×844 视觉与交互通过；精确 1440×900 仍待重截 |
| §9.3 | 用户/管理员 | `/console/predictions/:id` · `alea-predictions.html#debateReplay` | 展开辩论 | 选场、独立预测、匿名辩论、事实来源、终投、组单 | PRD §9.3 | `screenshots/037-predictions-worldcup-mobile-final.png` | 未验收 | OpenDesign 真实点击已展开五阶段回放；FIFA 事实与 AI 判断分层，首发/伤停/裁判/技术统计均排除并显示待官方确认，组单阶段因竞彩销售数据缺失不生成方案。精确桌面证据待补 |
| §9.4 | 用户/管理员 | 串关卡 · `alea-predictions.html` | 今日预测 | 待开/部分结算/命中/未中/无效 | PRD §9.4 | `screenshots/037-predictions-worldcup-mobile-final.png` | 未验收 | 今日页明确显示“暂无可核验的串关组合”，没有为单场决赛伪造第二场、赔率或串关；独立生命周期组件仍需桌面证据 |
| §9.2 | 用户/管理员 | 预测七生命周期 · `alea-predictions.html` | 历史归档 | 已发布、未发布、已撤回、已终止、失败、未达法定人数、结算态 | PRD §9、§17 | `screenshots/037-predictions-worldcup-mobile-final.png` | 未验收 | OpenDesign 已真实点击“历史推演/生命周期状态/已结算记录”；历史与结算均为诚实空态，生命周期明确为“组件状态样例 · 非当前赛况”，最终赛果显示待确认。尚缺各状态独立截图与精确桌面证据 |
| §10.1 | 用户/管理员 | `/console/rankings` · `alea-console.html#rankings` | 主导航“预测排行” | 维度、时间、赛事筛选、准入标记 | PRD §10 | 待截 | 失败 | 排名和战绩数据无 provenance，部分文案仍称“情景演示” |
| §10.3 | 用户/管理员 | `/console/rankings/:aiId` · `alea-console.html#rankings-*` | 排行行 | 校准图、盈亏、历史、教训 | PRD §10.3 | 待截 | 失败 | AI 头像存在文字降级逻辑；历史数据为虚构球队 |
| §11.1 | 用户/管理员 | `/console/pnl` · `alea-console.html#pnl` | 主导航“盈亏账本” | 圆桌账户、模型曲线、范围、图例、空态 | PRD §11.1 | 待截 | 未验收 | 模拟盈亏数据无明确原型标签和来源边界 |
| §11.2 | 管理员 | `/console/pnl?tab=real` | 盈亏页管理员 Tab | 录入、编辑、删除、日志、空态 | PRD §11.2 | 待截 | 失败 | 当前原型未发现完整真实盘交互面 |
| §12.1 | 用户/管理员 | `/console/reviews` · `alea-console.html#reviews` | 主导航“赛后复盘” | 筛选、命中/未中、空态 | PRD §12 | 待截 | 失败 | 复盘比赛与原因均为虚构演示数据 |
| §12.2–12.3 | 用户/管理员 | `/console/reviews/:id` · `alea-console.html#reviews-*` | 复盘卡 | 推演对照、模型复盘、共性偏差、改进要点、关联证据 | PRD §12 | 待截 | 未验收 | 管理员审核/发布流程尚未定位为完整交互 |
| §13.1–13.5 | 用户/管理员 | `/console/calculator` · `alea-calculator.html` | 主导航“竞彩方案”/采用 | 比赛身份、销售数据边界、玩法/出图禁用、紧凑复制/下载 | PRD §13、DESIGN `button-icon-compact` | `screenshots/038-calculator-worldcup-mobile-final.png` | 未验收 | 已移除 3 场虚构联赛、场次号、赔率、规则版本、注数/金额与理论回报；唯一比赛为 Match 104 西班牙 vs 阿根廷。复制/下载保持 44×44 紧凑图标且因销售数据未确认禁用。390×844 视觉通过，精确 1440×900 待补 |
| §13.6 | 用户/管理员 | `/console/calculator` 移动 · `alea-calculator.html#step-*` | 移动导航 | 核对比赛→配置锁定→预览锁定 | PRD §13.6 | `screenshots/038-calculator-worldcup-mobile-final.png` | 未验收 | OpenDesign 390×844 真实点击三步：步骤 1 显示比赛事实；步骤 2 四类配置控件均 disabled 且有原因；步骤 3 明确“不展示伪造票面”并提示出图禁用。尚缺步骤 2/3 独立图片证据 |
| §14.1 | 用户/管理员 | `/console/wiki` · `alea-console.html#wiki` | 主导航“赛事资料” | 四 Tab、搜索、筛选、空态 | PRD §14 | 待截 | 失败 | 使用虚构球队和 W/D/L 字母圆片；无人物资产 |
| §14.2 | 用户/管理员 | `/console/wiki/:type/:id` | 资料卡 | 球队/国家队/球员/教练/裁判详情 | PRD §14.2 | 待截 | 失败 | 未发现完整资料详情路由与页面 |
| §15.1 | 管理员 | `/console/admin/roundtable` · `alea-admin.html#launch` | 系统管理“发起推演” | 双模式、范围、阵容、参数、定时、发起、禁用 | PRD §5.3、§15.1、DESIGN 赛事身份规范 | `screenshots/024-admin-launch-desktop-final.png`；`screenshots/025-admin-launch-mobile-final.png`；`screenshots/026-admin-launch-functional-final.png`；`screenshots/033-admin-header-desktop-final.png`；`screenshots/034-admin-header-mobile-final.png` | 失败 | Match 104、西班牙 vs 阿根廷、FIFA 已确认事实/固定原型配置/未连接数据三层边界和全部核心输入已完成双端渲染与真实交互；独立复核捕获“正在创建执行…”禁用态并确认 1.4 秒后到达 `#live`。Alea 共享锁定图和 390px 页头溢出已修复。该页仍展示 AI 厂商标识，相关官方来源/许可未全部完成，故资产台账 P0 仍阻断整行“通过” |
| §15.2 | 管理员 | `/console/admin/roundtable/:jobId` · `alea-admin.html#live` | 发起推演后 | 阶段、消息、事实核验、缺席、跳过、终止原因 | PRD §15.2 | 待截 | 未验收 | 需逐状态实际操作和截图 |
| §15.3 | 管理员 | `/console/admin/publish` · `alea-admin.html#publish*` | 推演完成 | 质检、阻断、备注、确认、撤回 | PRD §15.3 | 待截 | 未验收 | 需验证红/黄项、发布锁定和撤回原因 |
| §15.4 | 管理员 | `/console/admin/lineup` · `alea-admin.html#lineup` | 系统管理“模型阵容” | Provider、端点/协议、密钥四态、模型目录失败/重试/自定义 ID、连接测试、1–3 实例、退役确认、保存/失败/重试、未保存离开确认 | PRD §15.4、Open Design `SettingsDialog` 参考 | `screenshots/020-admin-lineup-desktop-final.png`；`screenshots/021-admin-lineup-mobile-final.png`；`screenshots/022-admin-lineup-functional-failure-dirty.png`；`screenshots/023-admin-lineup-mobile-scrolled-opendesign.jpeg` | 未验收 | 页面、双端布局与核心交互已实测；模块改名后需重新截取视觉证据。资产台账 P0 阻断仍存在：Anthropic、DeepSeek、Gemini、Kimi、Qwen 等当前展示文件的官方来源/许可与光学比对未全部完成，因此不得标“通过” |
| §15.5 | 管理员 | `/console/admin/sync` | 系统管理导航 | 手动同步、日志、部分失败、重试、冲突 | PRD §15.5 | 待截 | 失败 | 当前 `alea-admin.html` 未发现数据管理页面 |
| §15.6 | 管理员 | `/console/admin/settings` | 系统管理导航 | 九类设置、版本、搜索、脏数据、保存、权限 | PRD §15.6 | 待截 | 失败 | 当前 `alea-admin.html` 未发现系统设置页面；P0 阻断 |
| §16.1 | 用户/管理员 | 消息中心 | 顶栏铃铛 | 20 条、已读、关注触发、串关终态 | PRD §16.1 | 待截 | 未验收 | 需核对消息类型与直达链接 |
| §16.2 | 用户/管理员 | 个人设置 | 头像菜单 | 消息偏好、关注、密码、OAuth、注销 | PRD §16.2 | 待截 | 失败 | 当前面板未确认覆盖完整个人设置 |
| §5.2、§18 #17 | 全角色 | 全局状态规范 · `alea-design-system.html` | 设计系统 | loading/empty/stale/partial/error/permission/后端/AI 不可用 | PRD §5.2 | 待截 | 未验收 | 需验证产品页面实际复用而非只存在于规范页 |

## 本轮验收记录格式

每次将一行改为“通过”时，必须同时记录：

1. 精确入口或操作；
2. 观察结果；
3. 1440×900 截图；
4. 390×844 截图；
5. 键盘、状态保持、错误恢复等非截图证据；
6. 未验证余项（如有则不能标“通过”）。
