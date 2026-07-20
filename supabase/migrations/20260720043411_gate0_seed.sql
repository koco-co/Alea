-- Alea Gate 0 deterministic version seeds.

with prompt_seed(key, version, content) as (
  values
    (
      'identity',
      1,
      jsonb_build_object(
        'prompt',
        $identity$你是 Alea 平台的 AI 足球分析师。每一场比赛分析都基于数据、赔率、双方风格和战意博弈，产出一份有推理过程、带风险提示的预测判断。

你的分析不追求「准确率 100%」—足球比赛的随机性意味着不存在完美预测。你的目标是：基于可用数据，给出当前最合理的判断，并诚实标注不确定性。

限制：只使用提供的工具获取数据。不要编造事实。不要使用竞彩范围之外的盘口术语。$identity$,
        'source', 'docs/提示词架构与辩论协议.md §2.2',
        'mutable_in_admin', false
      )
    ),
    (
      'core_methodology',
      1,
      jsonb_build_object(
        'prompt',
        $methodology$# 角色

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

## U 暂不可判
- 近况、阵容或比赛阶段数据不足，无法可靠归入 A/B/C
- → 明确输出缺失项，降低方向置信度；不得为了满足分类格式编造依据

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
## U. 战意暂不可判
- 积分规则、轮次、晋级形势或两回合信息不足 → 明确缺失项，不得强行归入 1–7；下调方向置信度

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

# 跨赛事阶段补充
1. 两回合淘汰赛必须读取 leg_number、首回合比分与当前 aggregate_score；领先方守和、落后方追分的动机按 90 分钟比分单独判断。
2. 中立场不得套用普通主场优势；venue_neutral=true 时取消未经数据支持的主场加成。
3. 联赛争冠、欧战资格、保级与无欲无求场景必须由积分差、剩余轮次和数学条件支持；无法取得条件时标记未知。

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
- 风险栏 ←→ 推荐腿：写进风险的方向不得作为保底层单选$methodology$,
        'source', 'docs/提示词架构与辩论协议.md §2.2',
        'methodology_version', 'core-methodology-v1.1'
      )
    ),
    ('phase_select_nominate', 1, jsonb_build_object(
      'prompt', '从冻结的在售场次摘要独立选择 0-N 场。每个提名引用 match_id、理由、方向置信度和关键缺失项；零提名合法；禁止推测未提供数据。',
      'source', 'docs/提示词架构与辩论协议.md §3.1')),
    ('phase_select_debate', 1, jsonb_build_object(
      'prompt', '匿名互阅已核验的提名，只评价是否值得深入推演；不得猜测身份；新事实必须提交 fact_claim，核验前不广播。',
      'source', 'docs/提示词架构与辩论协议.md §3.1')),
    ('phase_select_vote', 1, jsonb_build_object(
      'prompt', '对冻结候选范围内每场独立投 yes/no，并给出只引用已核验事实或纯推理的理由；不得跟随票数。',
      'source', 'docs/提示词架构与辩论协议.md §3.1')),
    ('phase_score_predict', 1, jsonb_build_object(
      'prompt', '独立完成数据检查、对手类型、战意、双边交互、首选与备选比分、方向置信度及风险信号。不可见他人分析；事实引用冻结 source_record_ids；缺失数据标记暂缺。',
      'source', 'docs/提示词架构与辩论协议.md §3.2')),
    ('phase_score_debate', 1, jsonb_build_object(
      'prompt', '匿名回应具体论据，可坚守、改票、质疑或补充。改票必须基于已核验证据或更好推理，不得因多数、自信语气或厂商身份跟随。',
      'source', 'docs/提示词架构与辩论协议.md §3.3')),
    ('phase_score_vote', 1, jsonb_build_object(
      'prompt', '输出最终首选全场和半场比分、由比分推导的方向、0-100 方向置信度与一句已核验理由。',
      'source', 'docs/提示词架构与辩论协议.md §3.4')),
    ('phase_bet_propose', 1, jsonb_build_object(
      'prompt', '基于有效终投、冻结赔率和规则提交具体竞猜方案或 no_bet。同场只选一种玩法但玩法内可复式；非空仓仓位为余额 1%-5%；所有方案先通过 calculate_ticket。',
      'source', 'docs/提示词架构与辩论协议.md §3.5')),
    ('phase_bet_debate', 1, jsonb_build_object(
      'prompt', '匿名检查已通过规则引擎的候选方案或 no_bet 的玩法、选项、串关、奖金快照、仓位和风险。修改必须有具体依据，no_bet 时 plan 必须为 null。',
      'source', 'docs/提示词架构与辩论协议.md §3.6')),
    ('phase_bet_vote', 1, jsonb_build_object(
      'prompt', '只在已校验候选中选择 candidate_id，输出 bet/no_bet、0-100 决策强度与理由；不得创造新方案。',
      'source', 'docs/提示词架构与辩论协议.md §3.7')),
    ('phase_review_prediction', 1, jsonb_build_object(
      'prompt', '仅使用冻结的原公证预测、当时输入/方法论/教训集、核验事件、独立赛果版本与赛后来源，分析根因并提出可执行 lesson 候选；不得查询后来信息改写当时判断。',
      'source', 'docs/提示词架构与辩论协议.md §11.2')),
    ('phase_review_methodology', 1, jsonb_build_object(
      'prompt', '评估分析框架而非单场直觉。默认保守，逐项输出提议理解、证据、OLD/NEW 回测、过拟合/对称性/可操作性风险及支持、反对或修改后再审结论。',
      'source', 'docs/提示词架构与辩论协议.md §11.4')),
    ('output_schema_select_nominate', 1, '{"$ref":"shared/schemas/selection.json#/$defs/selection_nomination","document_sha256":"f97d0aadd5ed9b80dabcc71eeef9d54e63745c67f7bb2d9b78f1a0a06863d8b1"}'::jsonb),
    ('output_schema_select_debate', 1, '{"$ref":"shared/schemas/selection.json#/$defs/selection_debate","document_sha256":"f97d0aadd5ed9b80dabcc71eeef9d54e63745c67f7bb2d9b78f1a0a06863d8b1"}'::jsonb),
    ('output_schema_select_vote', 1, '{"$ref":"shared/schemas/selection.json#/$defs/selection_vote","document_sha256":"f97d0aadd5ed9b80dabcc71eeef9d54e63745c67f7bb2d9b78f1a0a06863d8b1"}'::jsonb),
    ('output_schema_score_predict', 1, '{"$ref":"shared/schemas/prediction_card.json","document_sha256":"0df83bd08d739979ef2c6e8f28ec19ed4838ec3d819469366cf0023b775a89a5"}'::jsonb),
    ('output_schema_score_debate', 1, '{"$ref":"shared/schemas/debate.json#/$defs/score_debate","document_sha256":"97bb9d11e8527d6236b9d77f324af8de231bf5576534fa50a3e7eda186fa17e1"}'::jsonb),
    ('output_schema_score_vote', 1, '{"$ref":"shared/schemas/debate.json#/$defs/score_vote","document_sha256":"97bb9d11e8527d6236b9d77f324af8de231bf5576534fa50a3e7eda186fa17e1"}'::jsonb),
    ('output_schema_bet_propose', 1, '{"$ref":"shared/schemas/bet_plan.json#/$defs/bet_proposal","document_sha256":"af74d878600afe7140336ed32300436af4f19684f9c82a4194e9c275af0f6c57"}'::jsonb),
    ('output_schema_bet_debate', 1, '{"$ref":"shared/schemas/bet_plan.json#/$defs/bet_debate","document_sha256":"af74d878600afe7140336ed32300436af4f19684f9c82a4194e9c275af0f6c57"}'::jsonb),
    ('output_schema_bet_vote', 1, '{"$ref":"shared/schemas/bet_plan.json#/$defs/bet_vote","document_sha256":"af74d878600afe7140336ed32300436af4f19684f9c82a4194e9c275af0f6c57"}'::jsonb),
    ('output_schema_review_prediction', 1, '{"$ref":"shared/schemas/review.json","document_sha256":"90fd1526765adb946168fe7740389408d815ed859f76fb1b286a658266d1755b"}'::jsonb),
    ('output_schema_review_methodology', 1, '{"$ref":"shared/schemas/methodology_review.json","document_sha256":"328379fdee186bc57ec6665b980b1c44a457222f3d93d6f39dd780c0a2e31bd1"}'::jsonb),
    ('tool_contract_select_nominate', 1, '{"$ref":"shared/schemas/tools.json#/$defs/selection_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_select_debate', 1, '{"$ref":"shared/schemas/tools.json#/$defs/selection_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_select_vote', 1, '{"$ref":"shared/schemas/tools.json#/$defs/no_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_score_predict', 1, '{"$ref":"shared/schemas/tools.json#/$defs/match_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_score_debate', 1, '{"$ref":"shared/schemas/tools.json#/$defs/no_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_score_vote', 1, '{"$ref":"shared/schemas/tools.json#/$defs/no_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_bet_propose', 1, '{"$ref":"shared/schemas/tools.json#/$defs/bet_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_bet_debate', 1, '{"$ref":"shared/schemas/tools.json#/$defs/bet_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_bet_vote', 1, '{"$ref":"shared/schemas/tools.json#/$defs/no_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_review_prediction', 1, '{"$ref":"shared/schemas/tools.json#/$defs/no_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb),
    ('tool_contract_review_methodology', 1, '{"$ref":"shared/schemas/tools.json#/$defs/no_tools","document_sha256":"4b7dcc6348e60dc4468c739851be2a380d1b3316f58be8ecf606fb56c0a3e477"}'::jsonb)
)
insert into prompt_versions (key, version, content, content_hash)
select
  key,
  version,
  content,
  encode(extensions.digest(convert_to(content::text, 'utf8'), 'sha256'), 'hex')
from prompt_seed;

insert into score_formula_versions (version, config, effective_at)
values (
  1,
  jsonb_build_object(
    'prior_sample_count', 10,
    'cold_start_prior', 50,
    'dimensions', jsonb_build_object(
      'exact_score', 0.40,
      'direction', 0.30,
      'total_goals', 0.15,
      'half_full', 0.15
    ),
    'bayesian_formula', '(n * raw + C * mu) / (n + C)',
    'weight_formula', 'clamp(S / median(S), 0.75, 1.25)',
    'provider_family_normalization', true
  ),
  '2026-07-20 00:00:00+08'
);

insert into system_setting_versions (key, version, value, effective_at)
values
  (
    'history_context_limits',
    1,
    '{"recent_match_limit":10,"lesson_limit":5}'::jsonb,
    '2026-07-20 00:00:00+08'
  ),
  (
    'methodology_trigger',
    1,
    '{"distinct_match_threshold":3,"lesson_count_threshold":5,"consecutive_error_threshold":5,"lookback_days":null}'::jsonb,
    '2026-07-20 00:00:00+08'
  ),
  (
    'risk_limits',
    1,
    '{"daily_percent":15,"per_match_percent":5,"initial_balance":10000,"currency":"CNY"}'::jsonb,
    '2026-07-20 00:00:00+08'
  );

with rule_seed as (
  select jsonb_build_object(
    'schema_version', 1,
    'currency', 'CNY',
    'stake_per_bet', 2,
    'max_multiplier', 50,
    'settlement_period', 'regulation_90_minutes_plus_stoppage_time',
    'plays', jsonb_build_object(
      'had', jsonb_build_object('name', '胜平负', 'max_pass_legs', 8),
      'hhad', jsonb_build_object('name', '让球胜平负', 'max_pass_legs', 8),
      'crs', jsonb_build_object('name', '比分', 'max_pass_legs', 4),
      'ttg', jsonb_build_object('name', '总进球数', 'max_pass_legs', 6),
      'hafu', jsonb_build_object('name', '半全场胜平负', 'max_pass_legs', 4)
    ),
    'pass_rules', jsonb_build_object(
      'simple', jsonb_build_array('2串1', '3串1', '4串1', '5串1', '6串1', '7串1', '8串1'),
      'free_pass', jsonb_build_object(
        'enabled', true,
        'minimum_legs', 2,
        'maximum_legs', 8,
        'dan_supported', false
      ),
      'm_by_n', jsonb_build_object(
        'enabled', true,
        'definition_source', 'https://www.sporttery.cn/help/60328.html'
      ),
      'mixed_pass', jsonb_build_object(
        'enabled', true,
        'same_match_cross_play_allowed', false,
        'max_legs', 'minimum max_pass_legs among selected plays'
      )
    ),
    'payout_caps', jsonb_build_array(
      jsonb_build_object('minimum_legs', 1, 'maximum_legs', 1, 'cap', 100000),
      jsonb_build_object('minimum_legs', 2, 'maximum_legs', 3, 'cap', 200000),
      jsonb_build_object('minimum_legs', 4, 'maximum_legs', 5, 'cap', 500000),
      jsonb_build_object('minimum_legs', 6, 'maximum_legs', 8, 'cap', 1000000)
    ),
    'invalid_match', jsonb_build_object(
      'single', 'refund_stake',
      'parlay', 'remove_invalid_leg_and_recalculate_each_original_combination',
      'one_leg_remaining', 'settle_with_remaining_fixed_odds',
      'no_valid_legs_remaining', 'refund_stake',
      'm_by_n', 'apply_recalculation_to_each_expanded_combination',
      'odds_one_shortcut_allowed', false
    ),
    'calculation', jsonb_build_object(
      'bet_count', 'sum of expanded valid combinations including compound selections',
      'stake', 'bet_count * stake_per_bet * multiplier',
      'theoretical_payout', 'sum of fixed-odds products * stake_per_bet * multiplier capped per ticket',
      'rounding', 'half_even_each_expanded_winning_bet_to_two_decimals'
    ),
    'official_sources', jsonb_build_array(
      'https://www.sporttery.cn/help/2968.html?gid=9',
      'https://m.sporttery.cn/bzzx/20210118/3002863.html?gid=7',
      'https://www.sporttery.cn/help/40213.html',
      'https://www.sporttery.cn/football/jcjq/2018/0530/320867.html'
    ),
    'verification_status', 'official_materials_transcribed; Python and TypeScript golden verification required'
  ) as rules
)
insert into sporttery_rule_versions (
  version,
  source_url,
  source_observed_at,
  source_evidence_hash,
  rules,
  license_status,
  effective_at
)
select
  1,
  'https://www.sporttery.cn/jc/jsq/zqspf/',
  '2026-07-20 00:00:00+08',
  encode(extensions.digest(convert_to(rules::text, 'utf8'), 'sha256'), 'hex'),
  rules,
  'rules_public_reference_only; automated_data_reuse_unverified',
  '2026-07-20 00:00:00+08'
from rule_seed;
