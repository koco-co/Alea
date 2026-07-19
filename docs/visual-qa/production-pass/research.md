# Alea 生产原型研究与决策记录

日期：2026-07-19

## 已确认事实

### 产品与架构

- `docs/产品需求文档.md` 是产品行为与信息架构真源；`DESIGN.md` 是视觉真源。
- 仓库真源 `docs/产品需求文档.md` 当前为 **v1.6（2026-07-19）**；OpenDesign 项目内 `PRD.md` 仍为 **v1.4（2026-07-17）**。所有新实现必须以仓库 v1.6 为准，项目副本必须在后续独立串行任务中同步，不能让旧副本反向覆盖真源。
- 当前仓库没有可运行应用；用户现有 Next.js 文件删除状态不在本任务修复范围。实际高保真交付面是 OpenDesign 项目 `d99abbfa-a8d0-440e-a1aa-2b18b9926643`。
- `docs/技术架构设计文档.md` 明确当前未获得可用于生产再分发的体彩数据授权。原型可以使用固定 fixtures，但不得把虚构体彩编号、赔率、停售、赛果或伤停标成实时业务事实。
- 当前 OpenDesign 后台文件只有圆桌发起、直播、发布和终止片段，缺 AI 阵容、数据同步和系统设置。

### 2026 世界杯决赛

FIFA 官方确认：

- 西班牙与阿根廷进入 2026 世界杯决赛；
- 这是第 104 场比赛；
- 比赛于 2026-07-19 15:00（美国东部时间）在 New York New Jersey Stadium 举行，对应北京时间 2026-07-20 03:00；
- 西班牙是欧洲冠军；阿根廷是卫冕世界冠军和南美冠军。

来源：

- FIFA, “FIFA World Cup 2026 final | All you need to know”
  https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/final-live-watch-teams-tickets
- FIFA, “Spain v Argentina | FIFA World Cup final | Match preview”
  https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/spain-v-argentina-live-stream-team-news-tickets-and-more
- FIFA, “FIFA World Cup 2026 Final”
  https://www.fifa.com/es/tournaments/mens/worldcup/canadamexicousa2026/final

本轮研究时比赛尚未开赛，因此：

- 不把任何比分写成最终赛果；
- 不提前盖“命中/未中”章；
- 不编造官方体彩编号、赔率、停售状态、首发、伤停和裁判；
- 统一使用 `终投预测 2:1 · 半场 1:0 · 5/7 原始票 · 71% 加权共识` 作为明确标注的固定 AI 原型输出。

## 强制开源参考

项目：`nexu-io/open-design`
版本：`6b90486c97967633bfcfb0cd4d3c9b3314bf0caf`
许可：Apache-2.0
本地只读副本：`/tmp/open-design-reference`

已检查：

- `apps/web/src/components/SettingsDialog.tsx`
- `apps/web/src/components/byok/ByokKeyField.tsx`
- `apps/web/src/components/byok/ByokModelField.tsx`
- `apps/web/src/components/byok/ByokConnectionTestControl.tsx`
- `apps/web/tests/components/SettingsDialog.execution.test.tsx`
- `docs/testing/e2e-coverage/settings.md`

可借鉴模式：

- 左侧稳定分区导航 + 右侧任务面；
- Provider/协议/Base URL/密钥/模型之间的联动；
- 密钥显示/隐藏、清理输入、保存尾号、替换/清除；
- 搜索模型目录 + 自定义模型 ID；
- 仅在必填字段合法时允许保存/连接测试；
- 连接测试的 ready/running/success/error/retry 状态及 `status`/`alert` 语义；
- 自动保存的 saving/saved/error 顶部反馈；
- 不同协议 draft 隔离，避免密钥和字段跨 Provider 泄漏；
- 模型目录不支持、加载失败、账户模型已加载等清晰状态。

Alea 改造边界：

- 不复制 OpenDesign 的 Local CLI、BYOK、媒体生成、宠物、记忆等产品语义；
- 用 Alea 的“AI 厂商/连接/实例/提示词版本/运行控制”替换；
- 保留服务端密钥语义：界面只展示安全尾号，不提供明文回读；
- 每厂商 1–3 个实例，并增加昵称、实例角标、启停、推理强度、超时、并发和提示词版本。

## 其他成熟开源参考

### MUI X Data Grid

- 项目与源码：https://github.com/mui/mui-x/tree/master/packages/x-data-grid/src
- 许可边界：Community Data Grid 为 MIT；Pro/Premium 功能为商业许可。本原型只借鉴 Community 层的信息结构，不复制 Pro/Premium 代码。
- 已检查的状态/模式：列标题与排序、过滤模型、分页、空结果、加载、键盘导航、列裁切与响应式约束。
- Alea 改造：用于赛程、排行、同步日志和用户管理表格；筛选变化必须同步空态并避免保留失效分页位置。

### Metabase

- 项目：https://github.com/metabase/metabase
- 许可边界：开源部分 AGPL，另含商业许可文件；只做结构研究，不复制代码。
- 已检查的状态/模式：交互式仪表板、筛选、自动刷新、权限、版本化内容和管理日志。
- Alea 改造：盈亏/同步状态强调数据时间戳、来源、范围、失败与恢复；图表和控件全部按 Alea 视觉系统重绘。

### Keycloak Admin UI

- 项目与源码：https://github.com/keycloak/keycloak/tree/main/js/apps/admin-ui/src
- 许可：Apache-2.0。
- 已检查的状态/模式：稳定的管理侧栏、用户列表与详情、权限边界、保存反馈、错误恢复。
- Alea 改造：用于系统设置和用户管理的信息架构；不复制身份域、Realm 或客户端等 Keycloak 产品语义。

### Qwen 厂商身份与标识边界

- 官方组织：https://github.com/QwenLM
- 官方组织说明：Alibaba Cloud 的通用 AI 模型团队；组织主页链接到 `https://qwen.ai/`。
- 官方组织头像候选：https://avatars.githubusercontent.com/u/141221163?s=200&v=4
- 当前原型问题：`assets/vendors/qwen.svg` 缺少来源元数据，不能仅因图形相似就认定为官方可复用标识；`alibaba-cloud.svg` 也不能直接改名为 Qwen。
- Alea 改造边界：厂商语义可确认是 Qwen，但在商标复用许可或官方品牌包未确认前，资产台账保持未通过；产品页使用明确中性缺失态，不以文字首字母或阿里云图标冒充。

### Anthropic 官方品牌来源

- 官方 Newsroom：https://www.anthropic.com/news
- 官方媒体资产入口：Newsroom 的 `Download press kit`。
- 官方品牌指南源码：https://github.com/anthropics/skills/blob/main/skills/brand-guidelines/SKILL.md
- 已确认视觉 token：Dark `#141413`、Light `#faf9f5`、Mid Gray `#b0aea5`、Light Gray `#e8e6dc`、Orange `#d97757`、Blue `#6a9bcc`、Green `#788c5d`。
- 当前原型问题：`assets/vendors/anthropic.svg` 虽使用 `#d97757`，但没有来源元数据；颜色相同不能证明文件是官方 press kit 资产，仍需下载并逐图比对符号/字标、留白、基线和背景适配。

本轮未直接复用以上项目代码，因此没有新增第三方运行时依赖或归属文件。

## 假设

- 用户要求的“用西班牙 vs 阿根廷作为 mock 数据”解释为：所有核心叙事和默认路由围绕本场决赛；串关、历史归档和生命周期规范仍须保留 PRD 功能，可使用有来源的真实世界杯淘汰赛记录或独立状态样例，不能删除。
- 未取得足协队徽授权前，国家旗帜可作为明确标注的国家身份资产，但不能冒充国家队徽。
- 原型可以展示固定 AI 推演数字，但不能把它们计入真实排行或真实历史战绩。

## 风险

1. 官方赛果、首发和竞彩市场会在本任务期间变化；每次最终视觉回归前需重新核验。
2. 国家队/球员/教练/裁判照片和厂商商标存在许可与商标使用边界；无清晰来源时宁可显示规范缺失态。
3. 用单场决赛覆盖全部页面会与串关、多比赛筛选和历史统计语义冲突；必须把核心赛事与支持性样例分层。
4. OpenDesign 项目位于仓库外；如 OpenDesign 两次未准确落实同一修复，直接编辑其文件需要额外文件写入权限。
5. OpenDesign 会话会把执行中的追加消息放入队列，容易造成范围混叠和后续任务覆盖；本轮实行单任务门槛：每次发送前确认无活动任务和空队列，任务结束后核对文件哈希、实际渲染与截图，再发送下一条。

## 决策

- 采用“研究账页”而非“市场终端”或“比赛档案”作为赛程成熟化方向：信息密度高，但避免博彩终端感。
- 用 FIFA 已确认赛事事实作为页面真实骨架，用固定 AI fixture 表达预测过程，用“暂缺/待确认”表达未授权或未核验数据。
- 保留暖纸画布、衬线论点和陶土主行动；压缩列表圆角、卡片层叠和巨型宣言标题。
- P0 顺序：统一决赛语境 → 补 AI 阵容 → 补系统设置 → 补数据同步 → 核心链路与资产 → 全局状态与移动回归。

## 验收标准

- 首页、赛程、比赛详情、预测、辩论、算票、后台发起/直播/发布默认使用同一决赛 fixture 和同一组 AI 推演数值。
- 未授权的体彩字段、未确认的首发/伤停/裁判/赛果不出现伪造值。
- AI 阵容、数据同步、系统设置满足 Goal 的全部交互清单。
- 所有 PRD 路由/状态有本轮 1440×900 与 390×844 新截图，且关键控件实际操作通过。
- 静态语法与资源检查 exit 0；最终报告列出准确通过/失败/跳过数和未验证项。
