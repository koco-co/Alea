# Alea OpenDesign 生产审计

审计日期：2026-07-19
审计状态：逐路由修复与验收中
证据规则：只接受本轮在 OpenDesign 实际渲染中截取并检查过的图片；旧 `qa/` 与 `.tmp/shots/` 仅作历史参考。

## 总体判断

现有原型有统一的暖纸画布、陶土强调和较完整的控制台骨架，但产品语境与完成度不满足 Goal：

- 首页、赛程、预测、复盘、算票和百科大量使用“海湾超级联赛 / 澜城竞技 / 赤湾联”等玩具式虚构数据，直接触发用户本轮否定。
- `/console/admin/sync`、`/console/admin/settings` 在当前后台文件中没有对应完整页面，是 P0 缺页；`/console/admin/lineup` 已补齐页面与核心交互，但厂商资产 provenance 仍阻断最终通过。
- 多个页面把“演示开关/填充演示资料/模拟过期”等测试能力直接暴露为产品控件，削弱真实感。
- 页面仍大量采用单文件 hash 视图；必须逐项证明入口、激活态、返回状态和角色边界，而不能用一个长页代替完整路由验收。
- OpenDesign 任务必须严格串行：`#lineup` 任务在发送前后均确认队列为 0；首次解锁后读取到该任务已停止在仓库重大改动确认门，界面显示“剩余 1 个任务：提交实施范围、风险与验收标准并等待确认”，并非仍在执行。

## P0 阻断

1. **演示数据语境与用户要求冲突**
   - 位置：`alea.html`、`alea-console.html`、`alea-predictions.html`、`alea-calculator.html`、`alea-admin.html`。
   - 证据：本轮 OpenDesign 画面仍显示“海湾超级联赛 · 澜城竞技 vs 赤湾联”。
   - 静态清单：按虚构联赛/球队、周序号、停售、旧公证/审计编号等关键词计数，`alea.html` 9、`alea-console.html` 89、`alea-predictions.html` 60、`alea-calculator.html` 67、`alea-admin.html` 25；该计数只用于定位，不替代逐处语义核验。
   - 影响：用户一眼识别为虚假玩具数据，核心价值叙事失真。
   - 修复：统一以“2026 世界杯决赛 · 西班牙 vs 阿根廷”为本轮核心演示赛事；未来/未核验内容标“原型演示快照/待官方确认”，不得伪装官方实时数据。

2. **AI 阵容页功能与视觉已补齐，资产 provenance 仍阻断最终通过**
   - 位置：`/console/admin/lineup` · `alea-admin.html#lineup`。
   - 已完成证据：桌面 1440×900、移动 390×844、失败/脏数据功能态和移动实际滚动截图；真实点击覆盖 Provider 切换、连接测试、密钥掩码、自定义模型、实例上限、退役确认、未保存 Stay/Leave。
   - 独立复核：最终文件 SHA-256 `e7ec9865f2327ac3143e9daa9d381be44a1dd837641815fb7b8f45e8bc938182`；内联脚本 1 个、语法失败 0、静态 ID 104 个且重复 0、静态 `data-od-id` 26 个且重复 0、本地资源引用 37 个且缺失 0、真实密钥模式命中 0、临时 QA/本地服务器引用命中 0，命令退出码 0。
   - 仍余阻断：AI 厂商标识的官方来源、许可和同视口光学比对尚未全部完成，详见资产台账；在此之前本路由不能标“通过”或“生产可交付”。

3. **系统设置页缺失**
   - 位置：期望 `/console/admin/settings`。
   - 证据：`alea-admin.html` 未发现设置页面或九类配置入口。
   - 影响：PRD §15.6 全部系统治理能力不可交接。
   - 修复：补齐分组导航、搜索/定位、版本历史、保存/错误/脏数据保护和权限状态。

4. **数据同步页缺失**
   - 位置：期望 `/console/admin/sync`。
   - 证据：`alea-admin.html` 未发现同步页。
   - 影响：自动策略、手动触发、日志、部分失败和冲突裁定无法验收。

5. **资产与身份不合格**
   - 位置：赛事、百科、AI 身份、账户头像。
   - 证据：虚构队徽、W/D/L 文本圆片、部分 AI 文字头像降级、Qwen/阿里云身份映射未确认。
   - 影响：真实感和身份一致性不足；违反项目资产规则。
   - 已修复子项：Alea 共享锁定图原 1774×887 画布中可见内容仅 1218×432+287+202，固定高度下缩成不可读小点；现以相同可见 RGBA 字节原子替换为 1242×456、四边 12px 透明光学留白。随后修复管理员/控制台 390px 页头约束，8/8 个加载/路由状态均 `scrollWidth=clientWidth`、`scrollX=0`，通知/账户按钮和弹层右边界均在 380px 内。该修复不消除 AI 厂商、人物和账户头像的其余 provenance 阻断。

6. **OpenDesign 内 PRD 副本滞后**
   - 位置：OpenDesign 项目 `PRD.md`。
   - 证据：仓库真源 `docs/产品需求文档.md` 为 v1.6（2026-07-19），OpenDesign 副本仍为 v1.4（2026-07-17）。
   - 影响：OpenDesign 可能依据旧需求阻断或误改新增页面。
   - 修复：所有实现以仓库 v1.6 为准；在无活动任务且队列为 0 时，用独立单任务同步项目副本并复核版本头与关键 §15.4–15.7。

## P1 主要问题

1. 认证页暴露“填入演示账户/演示：填入有效资料”，应改为内部可复现 URL 状态或隐藏测试入口。
2. 算票页暴露“模拟数据过期”控件；真实产品应由数据状态驱动，测试状态不应占据用户界面。
3. 百科只有卡片网格，未发现球队/国家队/球员/教练/裁判完整详情。
4. 管理员真实盘、账户设置、通知偏好、关注列表和注销流程未形成完整可验证面。
5. 排行、盈亏、历史、复盘数值缺少清晰的演示数据 provenance 和一致的赛事时间线。
6. 现有旧截图多为超长整页导出，不能替代 1440×900 与 390×844 同视口状态证据。

## P2 视觉与无障碍风险

1. 桌面/移动断点虽有静态断言，尚未逐页真实操作验证。
2. 多个交互控件需要检查 focus、pressed、selected、disabled、loading、saving、saved、error。
3. W/D/L 和 ✓/✗ 等状态应同时提供中文文本，不能只靠字母或颜色。
4. 长页导出中的 sticky 顶栏拼接现象不能作为“真实页面无重复”的充分证据，需在 OpenDesign 视口内复核。
5. 动态倒计时、直播阶段和图表仍需读屏文字状态与 reduced-motion 验证。

## 已确认的产品边界

- `docs/技术架构设计文档.md` 明确：当前没有获授权的体彩数据源，原型只能使用固定 fixtures 或明确有权使用的数据；不得把示例赔率、赛果或同步状态标成实时体彩事实。
- 用户指定的“2026 世界杯决赛：西班牙 vs 阿根廷”可作为统一演示语境；比赛事实、官方竞彩赔率、首发、伤停、裁判和赛果必须依当前可核验来源决定，未知项显示“待官方确认/暂缺”。
- 串关、历史归档和多赛事筛选仍是 PRD 要求，不能因为主叙事聚焦一场决赛而删除；它们应使用明确标注的历史/状态演示数据，不与决赛实时事实混淆。

## OpenDesign 串行执行证据

- 用户截图 `references/opendesign-queue-mistake.png` 明确显示当时已有 1 个任务执行且 3 条消息排队；该状态不允许继续发送。
- 发现后已删除全部排队项并停止错误活动任务；再次读取界面树确认活动任务结束、输入框为空、排队项为 0。
- 当前固定门禁已同步到 `AGENTS.md` 和 `docs/PROTOTYPE_PRODUCTION_GOAL.md`：任何时刻最多 1 个 OpenDesign 任务；发送前后均刷新界面树并核对任务文本、执行状态和队列。
- 当前赛事详情任务发送前证据为 `running=false`、排队项 0、输入框为空；发送后目标全文成为当前用户消息、输入框清空、出现“停止”控件、排队项仍为 0。任务执行期间不再追加消息。
- 当前 `#lineup` 任务同样在队列为 0 且无其他活动任务时发送；随后 Mac 进入锁定状态。首次解锁后的 OpenDesign 界面确认没有“停止”按钮、没有排队区、输入框为空且发送按钮禁用；任务停在上述确认门。期间两次自动/程序草稿均在发送前清除，未进入队列。静态复核 `alea-admin.html` SHA-256 仍为 `f2dc6d051dd41bbc91ab1c1eb0a082f11b0f355c51ba2dfce9aa3c09863ad182`，`alea-console.html` 仍为 `d45a351436daa200f06b01a46df001233ed0f8c3a67b2e4e96b93bdedf9f0995`，说明目标文件未写入且未误改用户控制台。
- OpenDesign 的产出卡虽然列出 `alea-admin.html` 与 `PRD.md`，但权威文件检查不支持“已写入”的表面提示：`alea-admin.html` 的哈希与修改时间未变，项目内 `PRD.md` 仍为 2026-07-17 的旧副本，仓库 `docs/产品需求文档.md` 也未被本次任务改写。不得把产出卡当作实现证据。

## 本轮截图

1. `screenshots/001-baseline-opendesign-home.jpeg`
   - 操作：读取 OpenDesign 当前窗口，未主动导航或改动。
   - 观察：营销首页渲染稳定；核心赛事仍为“海湾超级联赛 · 澜城竞技 vs 赤湾联”；左侧对话仍在执行上一轮修改。
   - 结果：接受为修改前基线；不能作为任何路由通过证据。
2. `screenshots/002-console-overview-before.jpeg`
   - 操作：等待 OpenDesign 素材研究任务结束且队列清空后，读取 `alea-console.html#overview` 实际预览。
   - 尺寸：1337×768；不是验收视口，只作为修改前问题证据。
   - 观察：总览仍显示虚构联赛、虚构球队和队徽、虚构竞彩编号、已公证/已结算语义、无来源账户收益和排行数据。
   - 结果：失败；必须改为未开赛的西班牙 vs 阿根廷决赛研究简报，并在 1440×900 与 390×844 重新验收。
3. `screenshots/003-console-overview-desktop-header-fixed.png`
   - 操作：在上一条 OpenDesign 任务完成且队列为 0 后，检查其最终 `alea-console.html#overview` 桌面导出。
   - 尺寸：1440×900。
   - 观察：顶部导航、完整标题、决赛主视觉、已核对赛事字段、固定 AI 原型输出和诚实空态均可见；未发现横向溢出或顶部裁切。
   - 结果：桌面首屏视觉通过；仍需在后续修正后复测，防止移动端布局修复造成回归。
4. `screenshots/004-console-overview-mobile-bottom-nav-overlap-failed.png`
   - 操作：检查同一轮输出的 `alea-console.html#overview` 移动导出。
   - 尺寸：390×844。
   - 观察：顶部标题与主视觉完整，但固定底部导航覆盖比赛元数据，截图底部文字落在导航层后方。
   - 结果：失败；已在确认 OpenDesign 空闲且队列为 0 后，仅发送一条针对移动端底栏安全区和内容净空的修正。
5. `screenshots/005-console-overview-mobile-end-opendesign.jpeg`
   - 操作：在 OpenDesign 实际切换到 390×844 移动预览后，将 `#overview` 主滚动区滚到末尾，再使用 OpenDesign 截图控件取证。
   - 尺寸：1337×768 的 OpenDesign 工作区截图；中央预览为 390×844 缩放显示。
   - 观察：最后一张“阅读说明”卡片完整结束，卡片与独立底部导航之间保留可见净空；导航未覆盖文字、按钮或卡片。
   - 结果：通过，作为滚动末尾实际 OpenDesign 渲染证据。
6. `screenshots/006-console-overview-mobile-final.png`
   - 操作：检查修正后 `#overview` 的正式移动导出。
   - 尺寸：390×844。
   - 观察：品牌头部、标题、赛前状态、主视觉与当前可见比赛元数据完整；内容在独立滚动区内，固定导航占据预留底部槽位。
   - 结果：移动首屏通过；滚动末尾另由截图 005 证明。
7. `screenshots/007-console-overview-desktop-final.png`
   - 操作：检查同一最终文件的桌面回归导出。
   - 尺寸：1440×900。
   - 观察：完整顶部导航、标题、主视觉、已核对赛事字段、固定 AI 原型输出和诚实空态均可见；无顶部裁切或横向溢出。
   - 结果：桌面回归通过。
8. `screenshots/008-console-fixtures-mobile-before.jpeg`
   - 操作：在 OpenDesign 切换到 390×844 后，通过移动底部导航进入 `#fixtures`，读取实际渲染。
   - 尺寸：1337×768 的 OpenDesign 工作区截图；中央预览为 390×844。
   - 观察：页面显示“海湾超级联赛、澜城竞技、赤湾联、周六017”、无来源赔率、停售倒计时和“在售/已停售”等伪实时语义。
   - 结果：失败，作为赛程修改前移动基线。
9. `screenshots/009-console-fixtures-desktop-before.jpeg`
   - 操作：保持 `#fixtures`，切换到 OpenDesign 全宽桌面预览并读取实际渲染。
   - 尺寸：1337×768；作为修改前工作区证据，不替代 1440×900 正式验收图。
   - 观察：虚构联赛和俱乐部、无来源赔率、虚构编号、倒计时与已停售语义在桌面更完整暴露。
   - 结果：失败；当前唯一 OpenDesign 任务正在将该路由改为西班牙 vs 阿根廷决赛的赛前来源诚实态。
10. `screenshots/010-console-fixtures-desktop-final.png`
    - 操作：从清理后的正式 `alea-console.html#fixtures` 重新导出并检查桌面首屏。
    - 尺寸：1440×900。
    - 观察：完整桌面导航、日期/状态/赛事/搜索控件、Match 104 主行、两国国旗、两地时间、固定 AI 原型输出和来源未连接状态均清晰；无横向溢出或裁切。
    - 结果：赛程列表桌面视觉通过。
11. `screenshots/011-console-fixtures-mobile-final.png`
    - 操作：从同一正式文件重新导出移动首屏。
    - 尺寸：390×844。
    - 观察：筛选控件单列重排，比赛卡信息完整，底部导航占独立槽位，主要操作未被遮挡。
    - 结果：赛程列表移动视觉通过。
12. `screenshots/012-console-fixtures-functional-15-of-15.png`
    - 操作：运行临时验收壳，覆盖日期、状态、赛事、搜索、空态、重置、Escape、管理员选场、草稿发起、键盘进入和返回；完成后从正式产品文件删除验收代码。
    - 观察：15/15 项全部显示 PASS。
    - 结果：赛程列表与筛选/恢复交互通过；该验收只覆盖 `#fixtures` 列表及简版研究边界，不代表 PRD §8.3 全详情已完成。
13. `screenshots/013-console-fixture-detail-desktop-before.jpeg`
    - 操作：在 OpenDesign 队列为 0 且没有执行中任务时，从 `#fixtures` 点击“查看研究边界”，读取当前详情桌面渲染。
    - 尺寸：1337×768 的 OpenDesign 工作区截图；中央预览为全宽桌面。
    - 观察：对阵横幅、两地时间和来源边界已诚实呈现，但 PRD §8.3 要求的竞彩、情报、预测、赛果、复盘 Tab 全部缺失。
    - 结果：失败；详情仍是简化边界壳，不能作为比赛详情验收通过证据。
14. `screenshots/014-console-fixture-detail-mobile-before.jpeg`
    - 操作：保持同一详情状态，将 OpenDesign 切换到 390×844 移动预览后读取实际渲染。
    - 尺寸：1337×768 的 OpenDesign 工作区截图；中央预览为 390×844。
    - 观察：现有两张卡片在移动端无明显横向溢出，但页面仍缺少全部详情 Tab；底部导航占位正常。
    - 结果：失败；仅作为 PRD §8.3 修复前移动基线。
15. `screenshots/015-console-fixture-detail-desktop-final.png`
    - 操作：从清除临时验收脚本后的正式 `alea-console.html#detail-final` 导出桌面首屏。
    - 尺寸：1440×900。
    - 观察：Match 104 对阵横幅、两地时间、五个 Tab、竞彩五玩法诚实空态均完整；顶部导航、卡片边界和文字无裁切。
    - 结果：桌面视觉通过。
16. `screenshots/016-console-fixture-detail-mobile-final.png`
    - 操作：从同一正式文件导出 390×844 详情首屏。
    - 尺寸：390×844。
    - 观察：对阵信息、五个 Tab 和首个竞彩空态完整；内容滚动视口在固定底部导航上方结束，卡片、文字、状态角标均未进入导航层。
    - 结果：移动首屏视觉通过。
17. `screenshots/017-console-fixture-detail-mobile-end-final.png`
    - 操作：将同一移动详情滚动区滚到末尾后导出；底部 180px 另行放大检查固定导航和最后卡片间隔。
    - 尺寸：390×844。
    - 观察：最后一个“半全场”空态完整结束，滚动条止于导航上方，四项底部导航完整可见且保留清晰净空。
    - 结果：移动末屏视觉通过。

比赛详情补充检查：OpenDesign 交互/结构验收最终 `25/25` 通过；本地复核内联脚本 `1` 个、语法退出码 `0`，重复 ID `0`，临时 `fixtureDetailClearanceQa`、`detailQa`、`detailEnd` 和验收壳引用命中 `0`。该结论只覆盖 `#detail-final` 及其五个 Tab，不覆盖其他控制台路由。
18. `screenshots/018-admin-launch-desktop-before.jpeg`
    - 操作：在 OpenDesign 全宽桌面预览打开正式 `alea-admin.html#launch`。
    - 尺寸：1337×768 的 OpenDesign 工作区截图；中央为全宽桌面预览。
    - 观察：页面只有发起、直播、质检、发布和终止工作流；“AI 阵容”仅是只读 7 实例卡，侧栏没有 PRD §15.4 的独立阵容配置入口。
    - 结果：失败；Provider、端点/协议、密钥、模型、连接测试、实例管理和保存状态全部缺失。
19. `screenshots/019-admin-launch-mobile-before.jpeg`
    - 操作：将同一后台正式文件切换为 OpenDesign 390×844 移动预览。
    - 尺寸：1337×768 的 OpenDesign 工作区截图；中央为 390×844 移动预览。
    - 观察：现有圆桌发起面可重排，但仍无 AI 阵容独立路由或配置控件。
    - 结果：失败；作为 `#lineup` 修复前移动基线。
20. `screenshots/020-admin-lineup-desktop-final.png`
    - 操作：从最终 `alea-admin.html#lineup` 导出桌面首屏并逐项检查。
    - 尺寸：1440×900。
    - 观察：后台导航、世界杯决赛执行上下文、6 个厂商目录、端点/协议、密钥尾号、模型目录和固定保存条完整；无顶部裁切、横向溢出或死区。
    - 结果：桌面视觉通过；厂商资产 provenance 仍按资产台账阻断整条路由最终通过。
21. `screenshots/021-admin-lineup-mobile-final.png`
    - 操作：从同一最终文件导出移动首屏。
    - 尺寸：390×844。
    - 观察：标题、世界杯决赛上下文、厂商横向条带和固定保存条完整，页面级无横向滚动；内容可继续向下滚动进入编辑区。
    - 结果：移动首屏视觉通过；编辑区实际滚动另由截图 023 证明。
22. `screenshots/022-admin-lineup-functional-failure-dirty.png`
    - 操作：选中 Anthropic，保留连接失败/重试与未保存修改状态后导出。
    - 尺寸：1440×900。
    - 观察：失败状态、重试入口、密钥尾号、模型目录、脏数据保存条同时可见，未以成功态掩盖错误。
    - 结果：失败/恢复视觉状态通过。
23. `screenshots/023-admin-lineup-mobile-scrolled-opendesign.jpeg`
    - 操作：在 OpenDesign 390×844 实际预览进入 `#lineup`，将页面滚动到端点与模型编辑区，再读取工作区截图。
    - 尺寸：1337×768 的 OpenDesign 工作区截图；中央预览为 390×844。
    - 观察：协议、Base URL、掩码密钥、替换/清除、模型搜索与固定保存条可见；保存条未覆盖当前控件。
    - 结果：移动实际滚动通过。
24. `screenshots/024-admin-launch-desktop-final.png`
    - 操作：在最终 `alea-admin.html#launch` 的默认 AI 自主模式导出 1440×900。
    - 观察：Match 104、西班牙 vs 阿根廷、双时区、场馆、FIFA 事实来源、未连接竞彩/阵容/伤停/裁判/赛果边界、双模式和赛前队列同时可见。
    - 结果：内容与桌面布局通过；该图导出时品牌资产透明留白仍异常，后续截图 033 已替代页头证据。
25. `screenshots/025-admin-launch-mobile-final.png`
    - 操作：从同一最终路由导出 390×844 默认态。
    - 观察：赛事事实、双队旗帜、主标题与来源边界完整；长页可继续向下滚动。
    - 结果：主体内容通过；该图导出时品牌资产仍缩成不可读小点，后续截图 034 已替代页头证据。
26. `screenshots/026-admin-launch-functional-final.png`
    - 操作：切换指定选场模式、2 轮、排程 02:00 后导出 1440×900。
    - 观察：模式卡、执行范围、轮数、禁用入围上限、排程与队列文案同步。
    - 结果：功能态视觉通过。
27. `screenshots/027-brand-lockup-admin-launch-desktop.png`
    - 操作：无损裁切共享品牌 PNG 后重新渲染后台桌面页头。
    - 观察：完整 Alea 图形标和字标恢复；桌面导航与动作区未变化。
    - 结果：品牌锁定图桌面通过。
28. `screenshots/028-brand-lockup-admin-launch-mobile-layout-failed.png`
    - 操作：同一资产修复后的后台 390×844 首轮证据。
    - 观察：品牌已完整，但页头仍沿用桌面间距，账户头像被右边界裁切。
    - 结果：失败；直接触发共享移动页头修复。
29–32. `screenshots/029-brand-lockup-console-overview-desktop.png`、`screenshots/030-brand-lockup-console-overview-mobile.png`、`screenshots/031-brand-lockup-home-desktop.png`、`screenshots/032-brand-lockup-home-mobile.png`
    - 操作：分别在控制台总览和营销首页的桌面/移动视口复核同一共享品牌资产。
    - 尺寸：桌面 1440×900，移动 390×844。
    - 观察：营销首页双端完整；控制台移动证据促成进一步的页头宽度/滚动约束检查。
    - 结果：共享资产本身 4/4 可读；布局问题由后续截图 035–036 收敛。
33–36. `screenshots/033-admin-header-desktop-final.png`、`screenshots/034-admin-header-mobile-final.png`、`screenshots/035-console-header-desktop-final.png`、`screenshots/036-console-header-mobile-final.png`
    - 操作：修复共享管理员顶栏和控制台内联移动页头规则后，分别在 1440×900 与 390×844 导出。
    - 观察：完整品牌、数据源状态、通知、账户按钮均未裁切；移动通知/账户弹层打开与关闭均实测，右边界 380px。
    - 结果：8/8 个加载/路由状态 `scrollWidth=clientWidth`、`scrollX=0`；桌面行为保持，静态检查 12/12。

AI 阵容补充交互证据：真实 OpenDesign 点击确认连接测试经历“正在测试→失败/重试”；安全文本栏输入测试值后可访问性树仅显示圆点掩码，明文命中 `false`；自定义模型 ID 使旧连接测试立即失效；Anthropic 可从 1 个实例增加到 3 个且上限后不再出现新增入口；退役弹层可取消。未保存导航最终实测 `Stay=true`、`Leave=true`：弹层打开与留在此页时宿主地址和内容均保持 `#lineup`、草稿保留；不保存离开后只导航一次到 `#launch`，再次返回 `#lineup` 时昵称恢复到保存快照且保存按钮禁用。Computer Use 的 Escape 键名在当前服务端返回 `keyNotFound`，因此 Escape 的真实按键路径只由源代码映射与 OpenDesign 聚焦检查覆盖，未算作本轮真实键盘点击证据。

发起推演补充交互证据：OpenDesign 任务内聚焦验收覆盖默认态、两种模式、执行范围双向同步、轮数、入围上限、排程开关与时间、队列联动和启动过场；静态断言 36/36。独立 Computer Use 复核点击“指定选场模式”后读到自主模式 `Value: 0`、指定模式 `Value: 1`、范围为“指定比赛 · Match 104”，帮助文案明确“不使用入围上限”；点击发起后捕获按钮禁用及“正在创建执行…”状态，1.4 秒后宿主地址变为 `about:srcdoc#live`。这只证明 `#launch` 启动路径；到达后的 `#live` 仍含旧虚构数据，尚未验收。

## PRD v1.7 命名同步快照（未验收）

- 2026-07-19 对 `alea-console.html`、`alea-predictions.html`、`alea-admin.html`、`alea-calculator.html`、`alea-auth.html`、`alea-design-system.html` 执行了一次限定文件范围的命名同步；`shasum -a 256` 退出码 0，6/6 个指定 HTML 的 hash 改变，`alea.css` hash 保持 `0f9a821ad709688a320cb9ea55694029ccf70b51fffaa63182f6895b9453d720`。
- 已写入的一级名称为：每日总览、竞猜赛程、太玄问机、预测排行、盈亏账本、赛后复盘、竞彩方案、赛事资料、系统管理；用户移动导航只保留每日总览、竞猜赛程、太玄问机、竞彩方案四个核心入口，未暴露系统管理。
- 本轮不能验收：桌面 hover 副标题只有每日总览“今日简报”正确，其余 7 项仍错误地复用了页面名；`alea-console.html` 的路由切换未同步 `document.title`，默认无 hash 入口仍未按 PRD §4.2 落到太玄问机；可见页面仍有“预测 · 今日流”“排行 · 可验证表现”“盈亏 · 模拟盘”“复盘 · 教训档案”“算票 · 桌面三栏工作台”“百科 · 实体档案”等旧模块词。
- 管理员侧目前只有发起推演、推演直播、发布审核、模型阵容四个完整模块；数据管理、系统设置、推演方法、方法评审、用户管理、数据日志、赛果确认、定时推演仍缺页。“质检阻断”“终止归档”是工作流状态，不得计作新增模块或冒充上述缺页。
- `qa/shell-user-after-mobile.png` 的 390×844 首屏已人工检查，品牌、四项移动导航和用户权限边界可见；`qa/shell-admin-after-mobile.png` 因继承旧滚动位置导致标题顶部裁切，判定失败，不能进入正式截图台账。
- OpenDesign 验收阶段把临时 HTTP 服务以前台命令启动，任务计时继续但 45 秒无新输出；终止该服务后任务仍未恢复，随后终止卡死的 OpenDesign 进程。当时临时 `qa-shell-navigation-check.html` 尚未清理。因此本节只记录已写入快照与失败项，不构成命名同步通过证据。
- 卡死任务终止后，按 OpenDesign 失败回退规则直接修复 `alea-console.html`：8/8 一级名称与 8/8 hover 副标题现已匹配 PRD §4.2；空 hash 默认落到太玄问机；8 个一级路由和比赛详情、模型档案、模型复盘均写入精确动态标题；6 个旧模块前缀命中已清零；移动核心导航保持 4 项。修复后 hash 为 `e19921ac9c1da41b4dba8fd070789b4e40573e190ba018d9ba482898e7b6a410`。
- 同一文件静态检查退出码 0：可执行内联脚本 1、语法失败 0、静态 ID 116/重复 0、本地引用 32/缺失 0；临时 `qa-shell-navigation-check.html` 已删除。Mac 锁屏仍阻塞新的 OpenDesign 交互与正式双端截图，所以这些静态结果不得升级为视觉通过。

## 紧凑复制/下载控件快照（未验收）

- `alea-console.html#calculator` 与 `alea-calculator.html` 已将可见的“复制图片/下载 PNG”大文字按钮替换为 Lucide 官方 `copy` / `download` 图标；两个界面均为 36×36 可见按钮、44×44 触控热区、18×18 图标，并保留 `aria-label`、`title`、焦点环与禁用原因关联。
- 两个 Lucide 文件来自官方仓库 `main` HEAD `658573b0171e693bc965c167592cc0b92d002a3e`，ISC License；原始文件 hash、用途与降级边界已写入 `asset-ledger.md`。
- 静态合同检查退出码 0：2 个界面各有复制/下载图标按钮 2/2、`aria-label` 2/2、`title` 2/2、`aria-describedby` 2/2、可见大文字命中 0；可执行脚本语法失败 0；`alea-console.html` 静态 ID 117/重复 0、本地引用 34/缺失 0，`alea-calculator.html` 静态 ID 36/重复 0、本地引用 9/缺失 0。
- 当前 hash：`alea-console.html` 为 `197c9f295927aa59b3f5d3ff71389e1944857ceefdd30a86c0e7a40ae1daba93`，`alea-calculator.html` 为 `dd637c2209205ce542efd3568e7d9bf8588f12a774c4dd84348a22f0d33b51ee`。Mac 锁屏仍阻塞 OpenDesign 的桌面/移动渲染、悬浮提示、焦点、禁用态和复制/下载真实点击，因此本节不得标“通过”。

## 阶段性静态检查

- 6 个正式 HTML 文件本地资产引用共 99 处、16 个唯一目标，缺失引用 0；命令退出码 0。
- 跳过 `application/ld+json` 等非可执行脚本后，6 个文件的可执行内联脚本语法失败 0、重复 ID 0；命令退出码 0。
- 去玩具化定位清单仍命中：`海湾超级联赛`、`北方冠军联赛`、`澜城竞技`、`赤湾联`、`北境工业`、`海岬城`、`周六017/021/026`、`N8C4-02`、`情景演示`、`模拟盘` 以及直接暴露的演示账户。该清单是后续逐路由修复入口，不允许做无语义审查的全局字符串替换。
- 上述只是当前快照的静态证据；完成剩余修复后必须重新运行，不能替代逐路由视觉与交互验收。

## 未验证范围

- 除当前首页外，尚未完成本轮逐路由截图。
- `#detail-final` 比赛详情已完成本轮视觉验收；`#overview` 与 `#fixtures` 在模块改名后仍需重截。后台 `#launch` 与 `#lineup` 的页面、双端布局和核心交互已完成实测，但厂商资产 provenance 仍阻断矩阵“通过”；`#live`、发布/终止、预测、排行、盈亏、复盘、算票、百科及其他后台路由仍未完成。
- 尚未完成任何完整用户链路或管理员链路点击时序。
- FIFA 赛事事实、设置参考与国旗许可已核验；人物、足协队徽、部分 AI 厂商身份和账户头像仍未完成许可/来源核验。
- 已执行 `alea-admin.html#lineup` 与 `#launch`、`alea-console.html` 共享页头的语法、静态 ID、`data-od-id`、资源、密钥与临时验收引用检查；最新独立快照为：`alea-admin.html` 内联脚本 1、语法失败 0、静态 ID 113/重复 0、`data-od-id` 27/重复 0、本地引用 39/缺失 0；`alea-console.html` 内联脚本 1、语法失败 0、静态 ID 171/重复 0、`data-od-id` 55/重复 0、本地引用 32/缺失 0；`alea.css` 花括号 475/475。全站最终语法、资源、可访问性和交互回归仍未执行。
