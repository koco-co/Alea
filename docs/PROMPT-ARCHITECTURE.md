# Alea — AI 提示词架构与辩论协议设计

| 项 | 内容 |
|---|---|
| 文档版本 | v1.0 |
| 日期 | 2026-07-19 |
| 状态 | 待评审 |
| 上游依据 | PRD v1.6、TECH v1.2、`football-match-analysis` 方法论 |

---

## 0. 核心问题

Roundtable 要解决三个互斥的需求：

1. **AI 需要足够深的方法论**（对手类型、战意、风格交互等~1500 行知识）才能做出高质量预测
2. **但上下文窗口有限**，不可能每轮都塞全部知识
3. **多 AI 辩论时容易羊群效应**，保守/不自信的模型会跟风准确率高的模型

本设计通过 **分层注入 + 阶段切换 + 匿名辩论 + 加权投票** 同时解决这三个问题。

---

## 1. 整体架构：七层提示词注入

每个 AI 实例收到的是一个**运行时组装的 prompt**，不是固定文本。Python orchestrator 负责每次调用前拼好：

```
┌──────────────────────────────────────────┐
│  Layer 1: 身份与角色（静态）              │ ← 固定，仅在实例创建时生成
│  Layer 2: 核心方法论（压缩）              │ ← 从 skill 提取，变动极低频
│  Layer 3: 匿名身份（每轮动态）            │ ← 圆桌开始时分配
│  Layer 4: 比赛上下文（每场动态）          │ ← 从 MatchDataService 组装
│  Layer 5: 历史战绩（每实例每轮动态）      │ ← 从 DB 查询
│  Layer 6: 阶段指令（随阶段切换）          │ ← predict / debate / vote / bet 不同
│  Layer 7: 工具函数定义（静态）            │ ← 数据访问、计算等
│  ──────────────────────────────────────  │
│  最后：Phase-specific 输出格式规范        │ ← 本阶段要输出的结构化 Schema
└──────────────────────────────────────────┘
```

### 1.1 各层来源与维护

| 层 | 内容量 | 维护人 | 存储位置 |
|---|---|---|---|
| L1 身份角色 | ~50 行 | 开发 | 代码常量 |
| L2 核心方法论 | ~350 行 | 管理员在中枢编辑 | `prompt_templates` 表，版本化 |
| L3 匿名代号 | 1 行 | 编排器运行时生成 | 内存 |
| L4 比赛上下文 | ~150–250 行 | Python DataService 组装 | 内存 |
| L5 历史战绩 | ~30–50 行 | 从 DB 查询 | 内存 |
| L6 阶段指令 | ~40–80 行/阶段 | 开发 + 管理员可调 | `prompt_templates` 表 |
| L7 工具函数 | ~60 行 | 开发 | `tools/` 目录 + OpenAI JSON Schema |

---

## 2. Layer 2: 核心方法论（从 skill 提取）

这是把 1500 行的 skill 知识库压缩成可注入的规则集。**只保留判断型规则，删除操作型指令。**

### 2.1 存什么 vs 不存

| 保留（注入 prompt） | 删除（走工具/RAG） |
|---|---|
| 五条核心分析原则 | 数据源 URL 列表（走工具 `get_match_data`） |
| 对手类型分级 A/B/C 表格 | 搜索词模板（走工具内置） |
| 战意控分 7 类型表格 | XGBoost 公式（系统算，不是 AI 做的事） |
| 双边风格交互矩阵 5 行 | 体彩接口调用细节 |
| 淘汰赛专项规则（压缩） | 报告 HTML 渲染脚本 |
| 平局总进球二分规则 | 免责声明模板 |
| 赔率结构纪律（4 条） | 历史回测脚本 |
| 结论自洽性自检清单 | parlay-mode 详细配资算法 |
| 竞彩五大玩法口径约束 | 联赛球队 ID 映射表 |

### 2.2 压缩后的系统提示模板（L1+L2 合体）

```python
CORE_METHODOLOGY_SYSTEM_PROMPT = """# 角色

你是 Alea 平台的一名专业足球比赛分析师。你的分析是多 AI 圆桌辩论的一部分：多个 AI 各自独立分析后匿名辩论、投票收敛。

# 核心分析原则

1. **不低估非传统强队的韧性**：亚洲、非洲、中北美球队在低位防守、身体对抗、定位球方面常有纪律优势。面对强队时不简单套「弱队模板」。
2. **也不低估超级巨星的破局能力**：超级巨星（Mbappé/Messi/Haaland/Kane 级别）在僵局时可凭个人能力撕开密防。面对此类球队时区分：超级巨星型 / 体系型 / 低效热门队。
3. **竞彩让球与亚盘必须区分**：竞彩让球是整数（如-1、+1），只出让胜/让平/让负三种结果，没有赢半输半。禁止把竞彩让球和亚盘混为一谈。
4. **市场热度不等于真实稳妥**：赔率下降不意味着该方向更稳。识别热门降水、让球不升盘、平赔下降等异常信号。
5. **输出必须包含风险**：避免绝对化表达（「稳赢」「必中」）。

# 对手类型分级（每场比赛前必判）

## A 崩盘型漏勺
- 近 1–2 场失 4+ 球，源于体系崩溃/速度打穿/士气崩溃
- → 强队进球级联放大，首选净胜上调一档

## B 纪律型铁桶
- 低位防守纪律严、近期失球少、靠体系不靠个人
- → 维持闷平/小胜剧本，净胜 ≤1 合理
- **铁桶降级**：若该铁桶近 1–2 轮刚逼平/零封同级别球队 → 强队直接胜置信度强制下调一档

## C 开放对攻型
- 攻击型阵型、高位逼抢、能进也能丢、零封率低
- → 总进球强制 +1 档，比分必含 BTTS（双方都进球）的比分，不得只押零封小胜
- ⚠️ 判 C 必须有近 1–2 场真实开放对攻的实然证据，不能拿纸面阵容或媒体预测凑

# 战意与控分分级（出比分前必判，与对手类型并列）

## 1. 生死·需大胜
- 积分靠后，必须赢且需净胜球才能出线 → 大分差显著上调，首选比分上移 1–2 档
## 2. 已出线·控分避强
- 已基本出线，为规避淘汰赛强敌而主动控分求平 → 平局概率显著上调，「平」提为独立主选项
## 3. 领头羊·求稳锁分
- 尚未数学出线但平局即基本锁定，为后续留力 → 压净胜，零封小胜 1:0 为首选
## 4. 只需平即达标
- 数学上平即出线/锁名次，赢无额外收益 → 把平(0:0/1:1)提为首选项，方向用「不败」
## 5. 双方皆生死·相互忌惮
- 两队都需要分，但都怕先丢球 → 低总进球、窄净胜、零封小胜与平局权重同时上调
## 6. 已出局·摆烂或放开打
- 数学出局 → 双向高方差，可能送分也可能爆冷，只给区间降置信
## 7. 正常争分
- 双方都还需要分、无控分动机 → 按常规实力/对手类型判断

# 双边风格交互矩阵（出比分前必做）

不能只并列描述两队特点。必须合成一条「交互结论」— A 的进攻方式撞上 B 的防守与反击方式，会把比赛推向什么节奏？

| 交互类型 | 比赛会被推向 | 对比分影响 |
|---|---|---|
| 控球压上 vs 低位铁桶+长传反击 | 强队控球率高但高质量机会未必多；弱队拖慢比赛 | 净胜下调，1:0/1:1并列 |
| 边路爆点 vs 慢边卫 | 能持续制造高质量机会 | 净胜与总进球上调 |
| 高位开放 vs 高位开放 | 转换回合增多 | 总进球上调，必含 BTTS |
| 阵地慢热 vs 中路密集+门将强 | 低节奏消耗 | 0:0/1:1/1:0 权重上调 |
| 双方都务实/淘汰赛怕先丢球 | 上半场试探 | 半全场平平/平胜/平负，低总进球 |

# 淘汰赛专项规则（R32 起切换）

1. 战意单一化 — 每场生死，无控分避强场景
2. 竞彩按 90 分钟结算 — 强队晋级 ≠ 竞彩胜
3. 总进球偏低 — 取消末轮「+1 档」
4. 强队「直接胜」置信度低于 55% 时，比分层不得只押小胜，必须覆盖 90 分钟平

# 平局总进球高方差二分
凡判了「平/不输优先」，再问一句「这是死守平还是开放平？」：
- **死守低分平**：至少一方刻意龟缩 → 0:0/1:1
- **开放高分平**：双方都有攻击力、谁都不刻意死守 → 必含 2:2/3:3

# 赔率结构纪律
1. SP<1.30 的选项不得进入串关主腿（回报率不对称）
2. 方向层(胜平负)建议仓位优先
3. 比分投注 ≤ 总预算 10%
4. 淘汰赛正 EV 冷门票独立小额配资

# 竞彩口径硬约束（不可违反）
- 只使用五种玩法：胜平负、让球胜平负（整数）、比分、总进球数(0–7+)、半全场胜平负
- 禁止出现「大小球」「亚盘让球-0.5」「角球」等非竞彩玩法
- 结算按 90 分钟常规时间+伤停补时，不含加时和点球
- 比分含半场标注 `半场 x:x`

# 结论自洽性自检（输出前必过）
- 比分 ←→ 总进球：对齐（2:1 → 3 球档）
- BTTS ←→ 零封：判了 C 或对手 λ≥0.8 时禁止零封比分
- 胜负倾向 ←→ 竞彩让球：同向
- 半全场 ←→ 胜负：全场段一致
- 置信度 ←→ 措辞：低置信时避免堆砌推荐
- 风险栏 ←→ 推荐腿：写进风险的方向不得作为保底层单选
"""

# Layer 1 身份部分（当季固定在最前面）
IDENTITY_PREFIX = """你是 Alea 平台的 AI 足球分析师。每一场比赛分析都基于数据、赔率、双方风格和战意博弈，产出一份有推理过程、带风险提示的预测判断。

你的分析不追求「准确率 100%」—足球比赛的随机性意味着不存在完美预测。你的目标是：基于可用数据，给出当前最合理的判断，并诚实标注不确定性。

限制：只使用提供的工具获取数据。不要编造事实。不要使用竞彩范围之外的盘口术语。
"""
```

---

## 3. Layer 6: 阶段指令（每个阶段切换）

### 3.1 Phase 1: 独立预测指令

```python
PHASE_PREDICT_INSTRUCTION = """
# 当前阶段：独立预测

这是分析的第一阶段。你独立完成预测，**还不允许看到其他 AI 的分析**。

请按以下步骤依次完成：

## 步骤 1：数据检查
使用提供的工具获取比赛的完整数据（赔率、近况、伤停、历史交锋、积分榜等）。
标记哪些字段「数据暂缺」— 不要为缺失数据编造具体数字。

## 步骤 2：对手类型判断
根据获取的近况数据，判断对手属于 A(漏勺)/B(铁桶)/C(对攻)哪一类型，并给出依据。

## 步骤 3：战意判断
根据积分榜和出线情景，判断双方的战意/控分类型（7 类中的哪一类）。

## 步骤 4：双边风格交互
合成一条明确的交互结论：两队踢法相撞后，比赛会被推向什么节奏？

## 步骤 5：比分预测
综合以上所有判断，输出：
- 首选比分（含半场）
- 备选比分（1–2 个）
- 胜平负方向 + 置信度
- 让球胜平负判断（写明让球数）
- 总进球数判断
- 半全场判断

## 步骤 6：风险信号
识别关键的 2–3 个风险因素（伤停不确定、赔率异常、轮换风险、裁判尺度等）。

## 约束
- 置信度 < 70% 时，比分别做窄覆盖（必须覆盖更高方差）
- 数据缺失必须标注「暂缺」
- 所有事实性陈述附带来源（工具返回的 SourcedFact 中的 source 字段）
"""
```

### 3.2 Phase 2: 匿名辩论指令

```python
PHASE_DEBATE_INSTRUCTION = """
# 当前阶段：圆桌辩论（第{round_num}轮）

你正在与其他 AI 分析师进行圆桌讨论。每个人都在独立预测中提交了初步判断。

你的代号是 **{codename}**。

## 你可以做以下事情：

1. **坚守并解释**：如果其他 AI 的分析没有改变你的判断，可以重申你的观点，但必须有针对性地回应他们的论据（例如：「选手 C 提到[具体论据]，但根据[你的数据/推理]，我认为这个因素被高估了，理由是…」）

2. **改票并说明原因**：如果其他 AI 指出了你忽略的因素，你**应该**改变你的预测。改票是理性的，不是丢人的。格式：
   `改票：首选比分 1:1 → 2:1（半场 0:0 → 1:0）`
   `原因：[你被说服的具体证据/推理变化]`

3. **质疑/补充**：指出其他 AI 分析中可能的盲点。

## ⚠️ 重要规则：

① **不要因为「大多数人预测相同」就改票** — 每次改票必须基于具体论据，不是人数。共识不等于正确。

② **不要因为「某个 AI 看起来很自信」就跟风** — 自信不代表准确。审视数据分析，不是语气。

③ **不要攻击其他 AI 的「身份」** — 你不知道它们的厂商或模型，它们也不知道你的。只就论据辩论。

④ **每条回应都要引用具体数据** — 「根据主场优势」太笼统，要写「根据主队近 10 场联赛主场胜率 70% 且客队客场场均失 1.8 球」。

⑤ **如果你发现自己的数据与其他 AI 矛盾，先检查：** 是否基于不同的数据来源？比赛时间不同可能赔率已变。标注「数据产生时间差」。

⑥ **保留改票的权利** — 好的预测应该随信息更新而调整。改票 + 记下改票依据比死扛更专业。
"""
```

### 3.3 Phase 3: 终投指令

```python
PHASE_VOTE_INSTRUCTION = """
# 当前阶段：终投

**最终投票。** 经过你自己的独立分析和圆桌讨论后，给出你的最终判断。

你的投票权重由你的历史准确率决定 — 但你在投票时不需要知道自己的准确率是多少。只需要给出你认为最合理的判断。

输出格式：
- 首选比分（含半场）
- 投票理由（一句话）
"""
```

### 3.4 Phase 4: 组单指令

```python
PHASE_BET_FORM_INSTRUCTION = """
# 当前阶段：组单

基于所有入围比赛的分析结论，设计一个具体的竞猜方案。

## 你需要决定：

1. **投哪些比赛**：单场还是串关？如果串关，选哪些场次、几串几？（2串1 / 3串1 / 4串1…）
2. **押什么玩法**：比分？总进球？胜平负？让球？同场可混合玩法（如比分+胜负跨场混合过关）
3. **仓位多少**：你当前虚拟账户余额的 1%–5%。根据你对本方案的置信度决定仓位高低。

## 约束

- 只使用竞彩五种玩法
- 串关关数上限由竞彩规则配置决定（不同玩法上限不同）
- 每场比赛只能投一次（不能在同一场反复下注）
- 仓位：1%–5% 当前余额，附理由

## 输出格式

```json
{
  "plans": [
    {
      "name": "方案A · 稳健方向",
      "type": "parlay",
      "legs": [
        {"match_id": "...", "play": "had", "option": "主胜", "odds": 1.80},
        {"match_id": "...", "play": "crs", "option": "2:1", "odds": 6.50}
      ],
      "pass_types": ["2串1"],
      "multiplier": 1,
      "stake_percent": 3.0,
      "reasoning": "..."
    }
  ]
}
```
"""
```

---

## 4. Layer 5: 历史战绩注入

```python
def build_history_context(instance_id: str, db: Database) -> dict:
    """从 DB 查询该 AI 实例的历史数据，组装成注入用的上下文"""
    stats = get_instance_stats(instance_id)
    lessons = get_recent_lessons(instance_id, limit=5)
    calibration = get_calibration(instance_id)

    return f"""
# 你的个人战绩

## 各维度准确率
- 比分命中: {stats.crs_accuracy * 100:.0f}% ({stats.crs_attempts} 场)
- 胜平负方向: {stats.had_accuracy * 100:.0f}% ({stats.had_attempts} 场)
- 总进球: {stats.ttg_accuracy * 100:.0f}% ({stats.ttg_attempts} 场)
- 半全场: {stats.hafu_accuracy * 100:.0f}% ({stats.hafu_attempts} 场)
- 综合分: {stats.composite_score:.1f}
- 模拟盘净值: {stats.net_value:.0f} ({'已回撤: ' + str(stats.drawdown) if stats.drawdown else '持续增长'})

## 置信度校准
- 你历史上预测置信度在 70–79% 区间的比赛，实际命中率约为 {calibration.bucket_70_79_actual}%
- 校准评价: {calibration.label}（{calibration.description}）
"""

def build_lesson_context(instance_id: str, db: Database) -> str:
    """注入最近的教训，让 AI 知道哪里容易翻车"""
    lessons = get_active_lessons(instance_id)
    if not lessons:
        return ""

    items = "\n".join(
        f"- {l.source_match}: {l.lesson_statement}"
        for l in lessons
    )

    return f"""
## 你需要记住的近期教训（来自自己过去的误判）

以下是从你上一轮预测中提取的教训，你应该在分析时特别注意：

{items}
"""
```

> **设计原则**：历史战绩不是用来给 AI「自我感觉好或差」的，而是让 AI 识别自己的系统性偏差。一个「偏乐观」的 AI 看到自己的校准数据后，应该主动下调高置信度预测的权重。

---

## 5. Layer 4: 比赛上下文组装

```python
async def build_match_context(match_id: str, sporttery: MatchDataService) -> str:
    """从数据源组装结构化比赛上下文，不交给 AI 自己抓"""

    odds = await sporttery.get_odds(match_id)      # 竞彩五种玩法赔率
    form = await sporttery.get_team_form(match_id)  # 双方近况
    h2h = await sporttery.get_head_to_head(match_id)
    standings = await sporttery.get_standings(match_id)
    injuries = await sporttery.get_injuries(match_id)
    lineups = await sporttery.get_predicted_lineups(match_id)

    context = f"""
# 比赛数据（{now()} 快照）

## 对阵
{match.home} vs {match.away}
赛事: {match.competition} | 开赛: {match.kickoff}
场地: {match.venue} | 裁判: {match.referee or '暂未公布'}

## 竞彩赔率（来源: {odds.source} · {odds.fetched_at}）
- 胜平负: {odds.had_home} / {odds.had_draw} / {odds.had_away}
- 让球({odds.hhad_goal_line}): {odds.hhad_home} / {odds.hhad_draw} / {odds.hhad_away}
- 比分: {odds.top_crs_options}
- 总进球: {odds.ttg}
- 半全场: {odds.hafu}
- 单关可售: {odds.single_available}

## 双方近况
{form.summary}

## 历史交锋
{h2h.summary}

## 积分榜
{standings.summary}

## 伤停
{injuries.summary}

## 预计首发
{lineups.summary}
"""
    return context
```

这个上下文**不是** AI 自己通过搜索获取的，是由 Python orchestration 层组装后注入的。AI 的唯一数据获取通道是这层上下文 + 预定义的 tools（用于补充查询）。

---

## 6. 辩论交互协议（核心设计）

### 6.1 匿名实现

```python
CODENAMES = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta"]

def assign_codenames(instance_ids: list[str]) -> dict[str, str]:
    """每个圆桌随机分配代号，映射只在 orchestration 层持有"""
    shuffled = random.sample(CODENAMES, len(instance_ids))
    return {inst_id: name for inst_id, name in zip(instance_ids, shuffled)}

def anonymize_messages(
    messages: list[RoundtableMessage],
    codename_map: dict[str, str],
    own_instance_id: str
) -> list[dict]:
    """对其他 AI 的发言：去掉厂商/模型信息，只用代号"""
    result = []
    for msg in messages:
        if msg.instance_id == own_instance_id:
            continue  # 不把自己的发言再塞回去
        codename = codename_map[msg.instance_id]
        result.append({
            "speaker": codename,
            "prediction": msg.prediction,
            "confidence": msg.confidence,
            "reasoning": msg.reasoning,
            "sources": msg.sources,
        })
    # 随机打乱顺序，防止根据发言风格猜身份
    random.shuffle(result)
    return result
```

**关键点**：匿名是双向的 — AI 不知道自己的真实身份在别人眼中是什么，也不知道其他 AI 的真实身份。甚至 `assign_codenames` 的随机映射在 orchestration 层外不可知。

### 6.2 辩论流程

```
  Phase 1: 独立预测
    ┌─────┐ ┌─────┐ ┌─────┐
    │ AI-1│ │ AI-2│ │ AI-3│ ← 各自独立，不交流
    └──┬──┘ └──┬──┘ └──┬──┘
       │       │       │
       ▼       ▼       ▼
   预测写入 roundtable_events（Supabase PG）
       │
       ▼
  Phase 2: 辩论第 1 轮
    AI-1 看到: [Alpha 的预测+推理] [Beta 的预测+推理]
    AI-2 看到: [Alpha 的预测+推理] [Gamma 的预测+推理]
    AI-3 看到: [Beta 的预测+推理] [Gamma 的预测+推理]
    ↑ 每人都看不到自己对应的代号，看到其他人匿名。顺序随机打乱。
       │
       ▼
  Phase 2b: 辩论第 2 轮（可选）
    同上，带上第 1 轮的全部匿名发言
       │
       ▼
  Phase 3: 终投
    AI-1 投票 | AI-2 投票 | AI-3 投票
       │
       ▼
    Orchestrator 计算加权投票结果
   （权重 = 各实例的综合分，圆桌开始时已冻结）

       ▼
  Phase 4: 组单
    各 AI 基于终投共识 + 各场赔率，提出竞猜方案 → 辩论 → 投票
```

### 6.3 防羊群效应机制（关键）

| 机制 | 设计 | 为何有效 |
|---|---|---|
| **Phase 1 独立** | 辩论前各自已经做出预测，写入 DB | 即使辩论中改票，原始判断也入了审计。改票只能新增理由，不能覆盖初稿 |
| **匿名代号** | 不知道对面是「Claude」还是「GPT」，只看论据 | 消除「品牌偏信」— 不会因为「Claude 说的所以更可信」 |
| **打乱顺序** | 匿名发言随机排序，不固定发言顺序 | 防止「第一个发言的锚定效应」 |
| **辩论指令第①条** | 显式禁止「因为大多数人相同就改票」 | 从 prompt 层面给 AI 独立意志 |
| **辩论指令第③条** | 显式禁止判断其他 AI 的模型身份 | 只能就论据辩论 |
| **加权投票** | 终投按历史综合分加权，不是简单多数 | 即使 5 个低准确率 AI 投同一个比分，金边 AI 的一票可能更重要 |
| **视觉金边** | 前端展示时高准确率 AI 的头像有金边 | 用户也能识别「这个 AI 历史更准」，不受票数迷惑 |
| **熔断按钮** | 管理员可随时「跳过辩论直接终投」 | 如果辩论陷入死循环或无用争吵，管理员可中断 |

### 6.4 冻结时机（不可变）

```python
# 每次圆桌开始/进入新阶段时，冻结后续调用的所有变量
FROZEN_AT_ROUNDTABLE_START: {
    "participants": ["inst-1", "inst-2", "inst-3"],
    "vote_weights": {   # 综合分冻结
        "inst-1": 41.2,
        "inst-2": 32.7,
        "inst-3": 28.9,
    },
    "prompt_version": "core-methodology-v3",
    "sporttery_rules_version": "sporttery-v202607",
    "match_snapshots": {
        "match-1": {"odds": {...}, "fetched_at": "..."},
    },
}
```

冻结后写入公证账本，任何历史预测可完全还原其上下文。

---

## 7. 对抗「菜而不自知」：上下文注入策略

PRD 要求「让对应 AI 知道自己的历史预测信息、预测准确率等信息，免得某些 AI 预测时，菜而不自知」。

实现方式：在每一轮调用之前，将以下信息注入系统 prompt：

```python
def build_instance_context(instance: AIInstance, job: RoundtableJob) -> str:
    sections = []

    # L1 身份角色（固定）
    sections.append(IDENTITY_PREFIX)
    # L2 核心方法论
    sections.append(CORE_METHODOLOGY_SYSTEM_PROMPT)
    # L3 匿名代号
    sections.append(f"你的本场代号: {job.codenames[instance.id]}")
    # L5 历史战绩
    sections.append(build_history_context(instance.id, db))
    # L5 教训注入
    sections.append(build_lesson_context(instance.id, db))
    # L4 比赛上下文
    for match_id in job.matches:
        sections.append(match_contexts[match_id])
    # L6 阶段指令
    sections.append(current_phase_instruction)
    # L7 工具
    sections.append(tool_definitions)
    # 输出格式 Schema
    sections.append(output_schema)

    # 组装
    full_prompt = "\n\n---\n\n".join(s for s in sections if s)
    return full_prompt
```

---

## 8. 数据源工具函数定义（Layer 7）

```python
TOOL_DEFINITIONS = [
    {
        "name": "get_match_data",
        "description": "获取指定比赛的完整赛前数据（赔率、近况、积分、伤停、预报首发等）",
        "parameters": {
            "type": "object",
            "properties": {
                "match_id": {"type": "string", "description": "体彩场次编号"}
            },
            "required": ["match_id"]
        }
    },
    {
        "name": "get_team_current_season_stats",
        "description": "获取球队本赛事赛季的正面交锋和进阶数据",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string"}
            },
            "required": ["team_name"]
        }
    },
    {
        "name": "check_weather",
        "description": "查询开赛时段的天气状况",
        "parameters": {
            "type": "object",
            "properties": {
                "venue": {"type": "string"},
                "date": {"type": "string"}
            },
            "required": ["venue", "date"]
        }
    },
    {
        "name": "calculate_ticket",
        "description": "计算竞彩方案（注数/金额/理论奖金）。用于在组单阶段校验你的方案是否合法。",
        "parameters": {
            "type": "object",
            "properties": {
                "selections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "match_id": {"type": "string"},
                            "play": {"type": "string", "enum": ["had", "hhad", "crs", "ttg", "hafu"]},
                            "option": {"type": "string"},
                            "odds": {"type": "number"}
                        }
                    }
                },
                "pass_types": {"type": "array", "items": {"type": "string"}},
                "multiplier": {"type": "integer"}
            }
        }
    }
]
```

AI 通过调用这些工具来获取或验证数据。所有工具的后端实现都走 MatchDataService 的降级链，AI 不感知数据来源。

---

## 9. 技能方法论向系统提示的迁移路线图

| skill 章节 | ~行数 | 迁移方向 | 存放 |
|---|---|---|---|
| 第零步·前置闸门 | 14 | ❌ 不迁移 | 这是 human-in-the-loop 流程，不是 AI 分析的规则 |
| 第一步·收集信息 | 18 | → 转为工具定义 | `get_match_data` 工具 |
| 五条核心分析原则 | 37 | → 保留 | L2 核心方法论 |
| 首发确认门 | 10 | → 保留 | L2 中一条规则 |
| 双边风格交互矩阵 | 18 | → 保留（压缩表格） | L2 |
| 对手类型分级 | 18 | → 保留（压缩表格） | L2 |
| 战意与控分分级 | 90 | → 保留（压缩至~40 行） | L2 |
| 淘汰赛专项规则 | 30 | → 保留（压缩至~15 行） | L2 |
| 淘汰赛赔率结构 | 40 | → 保留（压缩至~10 行） | L2 |
| 推荐理由格式 | 27 | ❌ 不迁移 | 圆形卡片理由由 AI 自由输出，不需要模板 |
| 第二步·报告模板 | 45 | ❌ 不迁移 | Alea 页面有固定 UI 组件来展示 |
| 第三步·押注方案 | 20 | → 转为 Phase 4 指令 + 工具 | `calculate_ticket` 工具 |
| 结论自洽性自检 | 25 | → 保留（压缩清单） | L2 |
| betting-rules.md | 135 | → 保留核心约束 | L2 竞彩口径部分 |
| data-sources.md | 104 | → 转为工具实现细节 | Python 代码层，不注入 prompt |
| parlay-mode.md | 163 | → 仅保留仓位约束 | L2 赔率结构纪律中的 4 条 |

最终注入到每个 AI 的 L1+L2 内容量约 **350 行**（相对于原 1500 行），既保证了分析深度，也控制了 token 开销。

---

## 10. 总结：应对你的两个担忧

### 担忧 A：「有些模型会陷入死循环，在那钻牛角尖」

**防护层：**

| 防护 | 实现 |
|---|---|
| 固定轮数 | 默认只有 1 轮辩论，最多 2 轮，没有无限制自由讨论 |
| 熔断按钮 | 管理员随时可「跳过辩论直接终投」— 辩论再烂也不卡死 |
| Phase 1 独立预测已入账 | 即使辩论炸了，每个 AI 的初稿已经存在，可以直接跳过辩论用初稿投票 |
| Celery 任务超时 | 每个 AI 单次调用有最大等待时间（如 60s），超过标记「缺席」 |

### 担忧 B：「有些保守的模型给出的理由会影响其他模型的判断」

**防护层（同 §6.3）：**

| 防护 | 如何生效 |
|---|---|
| 匿名 | 保守模型如果来自「Claude」— 对面不知道它是 Claude，只看论据 |
| 辩论指令第①条 | 显式禁止「因为大多数人相同就改票」— 从 prompt 层面削弱跟风 |
| 加权投票 | 保守但准确率低的模型即使多，加权后权重也不一定高 |
| 改票需附理由 | 改票不是简单的「我改 2:1」— 必须写「改票原因：[具体论据]」，入审计后可追溯 |
| 高准确率金边 | 用户能直观看到「这个 AI 以前很准，这个不准」，不会被票数迷惑 |

---

## 11. 复盘 → 方法论自优化闭环（三阶设计）

### 11.1 整个流程概览

```
┌────────────────────────────────────────────────────────┐
│                     比赛结算                             │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  第一阶：教训生成（自动，无需确认）                     │
│  每个 AI 复盘输出结构化 lessons                         │
│  lessons 自动注入该 AI 的下一次预测上下文                │
└────────────────────┬───────────────────────────────────┘
                     │ 系统后台持续统计 lessons 的模式
                     │ 同类 lesson 出现 ≥3 场 → 触发提议
                     ▼
┌────────────────────────────────────────────────────────┐
│  第二阶：方法论提议（自动产生，排队待审）               │
│  系统聚合同类教训 → 生成方法论调整提议                   │
│  提议进入【方法论待审列表】，不自动生效                   │
│  管理员在「中枢·设置」页看到提议列表                     │
└────────────────────┬───────────────────────────────────┘
                     │ 管理员点「讨论此提议」
                     ▼
┌────────────────────────────────────────────────────────┐
│  第三阶：方法论评审圆桌（你提的「按钮入口」）           │
│  - 参与 AI 使用评审专用 prompt（不同角色）              │
│  - 必须跑回测（OLD vs NEW，N≥20 场）                   │
│  - 管理员实时围观，可中途提问/叫停                      │
│  - 终投：AI 们投票「支持/反对/修改后再审」              │
│  - 管理员二次确认 → 写入版本化的方法论配置               │
│  → 后续所有 AI 的 L2 核心方法论从新版本加载              │
└─────────────────────────────────────────────────────────┘
```

### 11.2 第一阶：自动教训生成

复盘时的 prompt 额外包含一个输出区块：

```python
REVIEW_LESSON_INSTRUCTION = """
# 输出：根因分析

完成复盘后，输出以下结构化信息：

## 你的系统性偏差（如有）
从本场比赛的失误中，你能识别出什么系统性偏差？
- [ ] 过分依赖纸面实力，忽视对手实际韧性
- [ ] 对铁桶队的进球能力估计过高
- [ ] 对某类战意场景的判断有惯性错误
- [ ] 其他（请描述）

## Lessons 输出
每条 lesson 是一句可执行的规则，有明确的条件和结论：

格式：
{
  "lessons": [
    {
      "rule": "当[条件X]时，[结论/动作Y]，因为[原因Z]",
      "evidence": "本场实际情况与预测偏差的描述",
      "category": "对手类型判断 | 战意分析 | 风格交互 | 数据完整性 | 赔率判断 | 仓位管理",
      "severity": "high | medium | low",
      "match_summary": "主队 vs 客队 预测X:X 实际Y:Y"
    }
  ]
}
"""
```

教训写库后自动注入该 AI 的下一次预测上下文（L5 层，见 §4），不需要管理员介入。

### 11.3 第二阶：方法论提议（聚合触发）

```python
def check_methodology_proposal_conditions(db: Database):
    """
    后台定时任务：扫描 lessons 表，看是否有同类模式达到阈值。
    """
    patterns = db.query("""
        SELECT category, substring(rule FROM 1 FOR 60) AS condition_pattern,
               COUNT(DISTINCT review_id) AS review_count,
               COUNT(*) AS total_lessons,
               array_agg(DISTINCT ai_instance_id) AS involved_ais
        FROM lessons
        WHERE NOT methodology_proposal_generated
          AND lessons.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY category, condition_pattern
        HAVING COUNT(DISTINCT review_id) >= 3
           AND COUNT(*) >= 5
    """)

    for pattern in patterns:
        proposal = MethodologyProposal(
            title=f"方法论调整：{pattern.category}",
            evidence_summary=(
                f"在 {pattern.review_count} 场复盘中出现 "
                f"涉及 {len(pattern.involved_ais)} 个 AI"
            ),
            status="pending_review",
        )
        db.insert(proposal)
        # 标记这些 lessons 已关联提议，避免重复生成
```

**提议触发阈值（可配置）：**
- 单个模式出现在 ≥3 场不同比赛的复盘中
- 或 涉及 ≥5 条 lessons（即使跨类别）
- 或 某 AI 连续 5 场以上在同一类别犯错

### 11.4 第三阶：方法论评审圆桌

#### 入口

管理员在 **中枢·系统设置 → 方法论管理** 看到待审提议列表。每条提议显示：

```
[待审] 铁桶降级规则过于激进 — 3 场复盘/5 条 lesson | 涉及: DeepSeek-1, Claude-2, GPT-1
[提议摘要] 当对手是 B 铁桶且近期刚零封过强队时，当前规则要求下降直接胜置信度一档。
  实际 3 场中有 2 场该下降的场次反而赢了。—— 可能是降级条件过于敏感。

[查看详情] [讨论此提议 ▸]
```

#### 方法论评审 prompt（不同于预测 prompt）

```python
METHODOLOGY_REVIEW_SYSTEM_PROMPT = """
# 角色

你是 Alea 平台的方法论评审专家。当前正在评估一条方法论调整提议。

## ⚠️ 重要原则（必须遵守）

1. **你正在评估的是分析框架本身，不是一场具体的比赛。** 你的任务是判断：这条规则修改是否在**统计上**提高预测质量，而不是「它是否符合你对某场比赛的直觉」。

2. **默认保守**：方法论应该在没有充分证据时保持不变。足球预测的随机性很大，单一批次的失败不足以推翻一条经过多场比赛验证的规则。

3. **支持修改的条件（必须同时满足至少两项）**：
   - (a) 有明确的数据统计表明旧规则在特定条件下系统性地偏离
   - (b) 修改后的规则在回测中表现更好（回测数据会提供）
   - (c) 新规则可以通过逻辑解释为什么旧规则失效（不是「数据凑出来的巧合」）
   - (d) 修改不会引入新的系统性偏差

4. **你必须明确指出以下风险**：
   - 过拟合风险：这条修改是否只针对特定几场比赛有效？
   - 对称性：如果这条规则改了，在相反场景是否需要对应调整？
   - 可操作性：这条规则是否能被所有 AI 实例一致理解和执行？

## 评审结构

请按以下结构逐项评审：

1. **提议理解** — 用一句话说明你理解这条提议在改什么
2. **证据评估** — 提供的 lesson 证据是否充分？是否需要更多数据？
3. **回测判断** — OLD vs NEW 的回测结果是否支持修改？（回测数据由系统提供）
4. **风险识别** — 这条修改可能引入什么新问题？
5. **结论** — 支持 / 反对 / 修改后再审（并附理由）
"""
```

#### 辩论交互

```
管理员点「讨论此提议」

  Phase 1: 独立评审（每人阅读提议 + 证据 + 回测数据，独立输出评审结论）
  Phase 2: 辩论（匿名，只讨论论据），可跑 1 轮
  Phase 3: 终投（支持/反对/修改后再审）

  管理员全程围观，可实时：
  - 发表补充观点（「我注意到还有一个相关数据…」）
  - 要求某个 AI 展开说明某条推理
  - 随时结束辩论直接裁定
```

#### 回测验证（硬性要求）

```python
async def run_backtest(proposal: MethodologyProposal, db: Database) -> BacktestResult:
    """
    用过去的 N 场比赛验证 OLD vs NEW。

    回测是评审圆桌的前置条件 — 没有回测数据，AI 无法评估修改效果。
    """
    # 选取过去 N 场比赛（至少 20 场，涵盖提议相关场景）
    matches = select_backtest_matches(
        criteria=proposal.category,
        limit=20
    )

    old_correct = 0
    new_correct = 0

    for match in matches:
        old_prediction = apply_rule(match, rule_version="current")
        if old_prediction == match.actual_result:
            old_correct += 1

        new_prediction = apply_rule(match, rule_version="proposed")
        if new_prediction == match.actual_result:
            new_correct += 1

    return BacktestResult(
        total_matches=len(matches),
        old_accuracy=old_correct / len(matches),
        new_accuracy=new_correct / len(matches),
        improvement=new_correct - old_correct,
    )
```

评审圆桌中，每个 AI **必须基于回测数据做判断**，禁止仅凭直觉投票。

#### 管理员确认

终投结果：

- **支持（加权票 ≥ 60%）** → 管理员看到二次确认弹窗：「写入方法论的变更将影响此后所有圆桌的 L2 系统提示。确认发布？」

- **反对（加权票 ≥ 60%）** → 提议标记「已驳回（AI 评审未通过）」，归档

- **修改后再审** → 提示管理员提供更多说明或调整提议文本后重新发起

#### + 管理员绕过权

管理员有权「跳过 AI 讨论直接修改方法论」— 如果人类发现一个显性问题，不需要等 AI 同意。

### 11.5 方法论版本化

```python
# 写入 prompt_templates 表
INSERT INTO prompt_templates (
    key = "core_methodology",
    version = 5,           # 自增
    content = <新的 L2 prompt>,
    changelog = "铁桶降级阈值收紧：从'近期零封任意对手'改为'近期零封同级别对手'",
    approved_by = "admin-user-id",
    backtest_id = "bt-20260719-001",
    ai_discussion_job_id = "rt-methodology-20260719-001",
    created_at = NOW()
)

# 所有后续圆桌引用这个 version
# 历史预测引用原 version，不受影响
```

**L2 方法论在「中枢·系统设置」页面展示为可读配置**（版本化 markdown 或结构化 JSON），管理员可以直接在上面手动编辑（不依赖 AI），编辑后发新版本。

### 11.6 对「自毁风险」的四重保险

| 保险 | 实现 |
|---|---|
| **回测强制** | 没有回测数据，AI 评审圆桌无法启动。回测 ≥20 场 |
| **投票不通过即归档** | 反对票 ≥60% 时提议关闭，不会反复弹出 |
| **管理员最终确认** | AI 说「支持修改」不等于改了 — 必须管理员点确认键 |
| **版本回溯** | 任何版本可一键回滚到上一版 |

### 11.7 「中途可调整」实现

管理员在方法论评审圆桌直播中做两件事：

1. **发表补充观点** → 作为「管理员备注」注入到 AI 的下一条消息中（不暴露管理员身份，但作为可信输入）
2. **调整提议文本** → 管理员可以选中某条评审结论，点「采纳为提议修改方向」— 终投前更新提议内容，AI 重新评估

### 11.8 与你的思路的对照

| 你的想法 | 实现方式 |
|---|---|
| 复盘后发现需要调整方法论 → 按钮入口 | 系统自动聚合同类 lesson 达到阈值才生成提议；管理员在设置页看到提议列表，点「讨论此提议」 |
| 多个 AI 一块判断是否合理 | 方法论评审圆桌，AI 用评审专用 prompt，不是预测 prompt |
| 其他 AI 说出自己的见解 | 匿名辩论，管理员围观 |
| 中途可调整 | 管理员可发补充观点、采纳评审结论修改提议文本 |
| 管理员二次确认后才修改 | 终投后管理员确认弹窗 |
| 方法论注入设置页面 | L2 prompt 以版本化配置显示在「中枢·系统设置」，可直接手动编辑 |
| 平台将 AI 调整结果导入配置 | 管理员确认后自动写入 prompt_templates 表，自增版本号 |
