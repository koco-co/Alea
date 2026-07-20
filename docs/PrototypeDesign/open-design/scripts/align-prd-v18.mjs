import fs from "node:fs";

function read(file) {
  return fs.readFileSync(file, "utf8");
}

function write(file, content) {
  fs.writeFileSync(file, content);
}

function replaceAll(content, replacements) {
  let next = content;
  for (const [from, to] of replacements) {
    next = next.split(from).join(to);
  }
  return next;
}

function requireText(content, text, file) {
  if (!content.includes(text)) {
    throw new Error(`${file} 缺少预期文本：${text.slice(0, 80)}`);
  }
}

{
  const file = "alea.html";
  let html = read(file);
  html = replaceAll(html, [
    ["海湾超级联赛 · 7 月 18 日 21:00 北京时间 · 情景演示", "2026 FIFA 世界杯决赛 · 2026-07-20 03:00 北京时间"],
    ["海湾超级联赛 · 7 月 18 日 21:00 · 情景演示", "2026 FIFA 世界杯决赛 · 2026-07-20 03:00 北京时间"],
    ["海湾超级联赛 · 情景演示记录", "2026 FIFA 世界杯决赛 · AI 推演数据"],
    ["澜城竞技 vs 赤湾联", "西班牙 vs 阿根廷"],
    ["assets/crest-lancheng.png", "assets/flag-spain.png"],
    ["assets/crest-chiwan.png", "assets/flag-argentina.png"],
    ["最终赛果 · 已命中 ✓", "AI 推演 · 待赛果确认"],
    ["最终赛果 2 : 1 · 已命中 ✓", "AI 推演 2 : 1 · 待赛果确认"],
    ["终投共识 · 已命中 ✓", "终投共识 · 待赛果确认"],
    ["<span class=\"status status-good\">已命中 ✓</span>", "<span class=\"tag\">AI 推演数据</span>"],
    ["<span class=\"hit-mark\">已命中 ✓</span>", "<span class=\"tag\">AI 推演数据</span>"],
    ["<span class=\"muted\">最终赛果</span><strong>2 : 1 · 半场 1 : 0</strong>", "<span class=\"muted\">赛果状态</span><strong>待赛果确认</strong>"],
    ["这场终投已标记“已命中 ✓”。同一套记录也会如实保留未命中场次，发布与否不改变结果。", "这场终投已写入原型公证示例，赛果仍待官方确认；发布与否不改变公证记录。"],
    ["把这次命中，也变成下一场的约束。", "赛果确认后，把偏差变成下一场的约束。"],
    ["结果不是终点。赛果、改票轨迹与判断依据被结构化留存，进入下一场的研究上下文。", "赛果确认后，系统会把改票轨迹与判断依据结构化留存，进入下一场的研究上下文。"],
    ["澜城竞技 2 : 1 赤湾联，半场 1 : 0；终投比分与赛果一致。", "模型推演为西班牙 2 : 1 阿根廷，半场 1 : 0；最终赛果仍待官方确认。"],
    ["<span class=\"hit-mark\">最终赛果 2 : 1 · 已命中 ✓</span>", "<span class=\"tag\">AI 推演数据 · 待赛果确认</span>"],
    ["这场终投已标记“已命中 ✓”", "这场终投已写入原型公证示例"],
    ["客队反击窗口已由同步情报核验。", "比赛身份与开球时间已由 FIFA 资料核验。"],
    ["把这次命中，也变成下一场的约束", "赛果确认后，把偏差变成下一场的约束"],
    ["澜城竞技", "西班牙"],
    ["赤湾联", "阿根廷"]
  ]);
  write(file, html);
}

{
  const file = "alea-admin.html";
  let html = read(file);
  html = replaceAll(html, [
    ["系统管理 · 发布审核 · 公证 N8C4-02", "系统管理 · 发布审核 · 组件流程演示"],
    ["用户视角预览 · 周六017", "用户视角预览 · 销售编号待确认"],
    ["海湾超级联赛 · 距停售 00:37", "2026 FIFA 世界杯决赛 · 销售数据待确认"],
    ["assets/crest-lancheng.png", "assets/flag-spain.png"],
    ["assets/crest-chiwan.png", "assets/flag-argentina.png"],
    ["澜城竞技队徽", "西班牙国家标识"],
    ["赤湾联队徽", "阿根廷国家标识"],
    ["澜城竞技", "西班牙"],
    ["赤湾联", "阿根廷"],
    ["比分 2 : 1 @7.20", "比分 2 : 1 · AI 推演数据"],
    ["20:06 · SPORTTERY-2026.07", "待竞彩销售数据确认"],
    ["2 项已验证 · 1 项隔离", "FIFA 赛事事实已核验 · 其余待确认"],
    ["检测到同场在售重复卡，必须先处理。", "检测到重复卡流程样例；竞彩销售数据仍待确认。"],
    ["玩法组合、赔率与停售时间合法", "玩法、赔率与停售时间待销售数据确认"],
    ["处理重复卡并重新质检", "处理重复卡样例"],
    ["发布预测卡", "演示发布确认"],
    ["预测卡已发布", "组件流程已演示"],
    ["用户端已可见；公证 N8C4-02 已在终投时进入排行与模拟盘统计。", "此处仅演示发布锁定、撤回与留痕交互；不是当前比赛的真实发布记录。"],
    ["终投前终止只保留执行审计；不会生成预测卡或公证账本。", "终投前终止只保留执行审计；以下为独立组件状态样例，不对应当前决赛。"]
  ]);
  write(file, html);
}

{
  const file = "alea-console.html";
  let html = read(file);
  html = replaceAll(html, [
    ["<a href=\"#predictions\" data-view=\"predictions\"><span>太玄问机</span><small>今日推演</small></a>", "<a href=\"alea-predictions.html#today\"><span>太玄问机</span><small>今日推演</small></a>"],
    ["<a href=\"#calculator\" data-view=\"calculator\"><span>竞彩方案</span><small>选择比赛</small></a>", "<a href=\"alea-calculator.html\"><span>竞彩方案</span><small>选择比赛</small></a>"],
    ["海湾超级联赛", "2026 FIFA 世界杯 · AI 推演数据"],
    ["北方冠军联赛", "赛事资料待接入"],
    ["澜城竞技 vs 赤湾联", "西班牙 vs 阿根廷"],
    ["澜城竞技", "西班牙"],
    ["赤湾联", "阿根廷"],
    ["北境工业 vs 海岬城", "历史比赛资料待接入"],
    ["海岬城 vs 北境工业", "历史比赛资料待接入"],
    ["北境工业 主胜", "第二场资料待接入"],
    ["松桥联 让胜", "第三场资料待接入"],
    ["松桥联 vs 山谷联", "比赛资料待接入"],
    ["南岸城 vs 森林竞技", "比赛资料待接入"],
    ["北境工业", "资料待接入"],
    ["海岬城", "资料待接入"],
    ["松桥联", "资料待接入"],
    ["山谷联", "资料待接入"],
    ["南岸城", "资料待接入"],
    ["森林竞技", "资料待接入"],
    ["周六017", "销售编号待确认"],
    ["周六021", "销售编号待确认"],
    ["周四005", "销售编号待确认"],
    ["周四007", "销售编号待确认"],
    ["公证账本 · 已同步", "AI 推演数据 · 待赛果确认"],
    ["<div class=\"banner good\"><span>已验证</span><div><strong>公证账本已写入</strong>", "<div class=\"banner warn\"><span>说明</span><div><strong>原型公证示例已冻结</strong>"],
    ["<span class=\"status good\">在售</span>", "<span class=\"status warn\">销售数据待确认</span>"],
    ["<button class=\"btn btn-primary\" data-adopt>采纳 AI 方案</button>", "<button class=\"btn btn-primary\" data-adopt disabled title=\"待竞彩销售数据确认\">销售数据待确认</button>"],
    ["单场比分与 3 串 1 方案写入公证账本。", "比分终投写入原型公证示例；销售数据接入前不形成串关方案。"],
    ["校验通过 · 俱乐部赛前发布会 · 19:42 · 已广播", "来源：FIFA · 采集 2026-07-19 · 仅赛事事实已核验"],
    ["<div class=\"rank-head-note\"><span class=\"tag\">情景演示</span>", "<div class=\"rank-head-note\"><span class=\"tag\">AI 推演数据</span>"],
    ["情景演示：", "AI 推演数据："],
    ["情景演示净值曲线", "AI 推演数据净值曲线"],
    ["情景演示校准图", "AI 推演数据校准图"],
    ["复盘情景演示", "组件状态样例"],
    ["非真实赛后报告", "非当前比赛记录"],
    ["来自预测 · 西班牙 vs 阿根廷，配置已带入，可返回修改。", "来自 AI 推演 · 西班牙 vs 阿根廷；销售数据待确认，暂不可生成方案。"],
    ["data-odd=\"2.10\"", "data-odd=\"0\" disabled title=\"销售数据待确认\""],
    ["data-odd=\"3.40\"", "data-odd=\"0\" disabled title=\"销售数据待确认\""],
    ["data-odd=\"7.20\"", "data-odd=\"0\" disabled title=\"销售数据待确认\""],
    ["data-odd=\"1.82\"", "data-odd=\"0\" disabled title=\"销售数据待确认\""],
    ["data-odd=\"3.65\"", "data-odd=\"0\" disabled title=\"销售数据待确认\""],
    ["data-odd=\"4.10\"", "data-odd=\"0\" disabled title=\"销售数据待确认\""],
    [">2.10</small>", ">待确认</small>"],
    [">3.40</small>", ">待确认</small>"],
    [">7.20</small>", ">待确认</small>"],
    [">1.82</small>", ">待确认</small>"],
    [">3.65</small>", ">待确认</small>"],
    [">4.10</small>", ">待确认</small>"],
    ["赔率快照已锁定", "竞彩销售数据待确认"],
    ["<span class=\"num\">7.20</span>", "<span class=\"num\">待确认</span>"],
    ["<span class=\"num\">1.82</span>", "<span class=\"num\">待确认</span>"],
    ["¥52.42", "—"],
    ["当前金额未超过单次研究预算 ¥16。", "销售数据接入后才计算金额与预算。"],
    ["PNG 已生成 · 含风险声明", "销售数据待确认，暂不可生成 PNG"],
    ["const value=Math.max(1,Math.min(99,Number(multiple.value)||1)),stake=value*2,returns=(7.2*1.82*stake).toFixed(2);multiple.value=value;document.getElementById('totalStake').textContent=`¥${stake}`;document.getElementById('maxReturn').textContent=`¥${returns}`;document.getElementById('ticketMultiple').textContent=`${value} 倍`;document.getElementById('ticketStake').textContent=`¥${stake}`;document.getElementById('ticketReturn').textContent=`¥${returns}`", "const value=Math.max(1,Math.min(99,Number(multiple.value)||1));multiple.value=value;document.getElementById('totalStake').textContent='—';document.getElementById('maxReturn').textContent='—';document.getElementById('ticketMultiple').textContent='待确认';document.getElementById('ticketStake').textContent='—';document.getElementById('ticketReturn').textContent='—'"],
    ["assets/crest-lancheng.png", "assets/flag-spain.png"],
    ["assets/crest-chiwan.png", "assets/flag-argentina.png"],
    ["澜城竞技队徽", "西班牙国家标识"],
    ["赤湾联队徽", "阿根廷国家标识"],
    ["情景演示", "AI 推演数据"]
  ]);
  write(file, html);
}

{
  const file = "PROTOTYPE-AUDIT.md";
  let md = read(file);
  md = md.replace(
    /^# Alea 原型静态验收报告[\s\S]*$/,
    `# Alea 原型迁移与需求覆盖说明

> 更新日期：2026-07-19  
> 当前需求基线：\`产品需求文档.md\` v1.8  
> 工作副本：当前 Open Design 工作区  
> 源项目：只读，未改动

## 本轮迁移结论

- 已从 Alea 源目录重新迁移全部 HTML、样式、图片和 QA 资产。
- 已单独复制最新 \`产品需求文档.md\`，并以 v1.8 取代旧 \`PRD.md\` v1.4 的验收口径。
- 生产叙事统一为 2026 世界杯决赛“西班牙 vs 阿根廷”。
- 比分 \`2 : 1\`、半场 \`1 : 0\`、原始票 \`5/7\`、加权共识 \`71%\` 统一标记为“AI 推演数据”。
- 最终赛果统一保持“待赛果确认”；未取得授权的销售编号、赔率与停售数据统一保持“待竞彩销售数据确认”。
- 旧版虚构联赛与球队不再作为当前业务记录展示；生命周期、复盘和结算示例明确隔离为“组件状态样例”。

## 页面覆盖

| 页面 | 文件 | 当前覆盖 |
|---|---|---|
| 营销首页 | \`alea.html\` | 圆桌动画、证据链、风险声明、注册入口 |
| 认证 | \`alea-auth.html\` | 登录、注册、18 岁与条款、找回密码、OAuth 样例 |
| 用户控制台 | \`alea-console.html\` | 每日总览、赛程详情、排行、盈亏、复盘、赛事资料、通知与账户菜单 |
| 太玄问机 | \`alea-predictions.html\` | 今日推演、历史筛选、生命周期样例、辩论回放、公证证据 |
| 竞彩方案 | \`alea-calculator.html\` | 响应式三步流程、销售数据缺失锁定、方案卡预览边界 |
| 系统管理 | \`alea-admin.html\` | 双模式发起、直播、阵容、发布审核、终止留痕 |
| 设计系统 | \`alea-design-system.html\` | Token、排版、状态、异常、身份组件与无障碍 |

## 当前诚实边界

- 原型不提供真实购买、支付、出票或兑奖。
- 未授权竞彩销售数据接入前，采纳、计算、出图、复制与下载保持禁用或展示缺失态。
- 排行、净值与复盘中的数字只用于验证组件结构，并标为“AI 推演数据”或“组件状态样例”，不视为真实战绩。
- 真实 OAuth、服务端鉴权、数据同步、Clipboard 权限和 PNG 下载仍属于后续运行态联调。
`
  );
  write(file, md);
}

{
  const file = "alea-console.html";
  let html = read(file);
  html = html.replace(
    /<article class="card"><div class="row-between"><span class="tag">串关 · 3 串 1<\/span>[\s\S]*?<\/article><\/div><div class="card" id="replayPanel"/,
    `<article class="card"><div class="row-between"><span class="tag">组合方案</span><span class="status neutral">资料待接入</span></div><h3 style="margin:14px 0">暂无可核验的串关组合</h3><p>当前仅有一场具备可追溯来源的决赛事实；未接入其他真实淘汰赛与竞彩销售数据前，不生成第二场比赛、赔率或串关方案。</p></article></div><div class="card" id="replayPanel"`
  );
  html = replaceAll(html, [
    ["<span class=\"status good\">赔率快照 · 已同步</span>", "<span class=\"status warn\">竞彩销售数据待确认</span>"],
    ["赔率数据已超过 24 小时", "竞彩销售数据尚未接入"],
    ["可以浏览和修改参数，但采纳、生成、复制与下载已禁用；同步恢复后立即开放。", "可以查看产品流程，但采纳、计算、生成、复制与下载保持禁用；可信同步完成后开放。"],
    ["伤停暂缺 · 赔率已同步", "伤停与销售数据均待确认"],
    ["赔率为最近同步快照", "赔率与玩法状态待销售数据确认"],
    ["<span class=\"status good\">新鲜</span>", "<span class=\"status warn\">待数据</span>"],
    ["<strong id=\"totalStake\">¥4</strong>", "<strong id=\"totalStake\">—</strong>"],
    ["<button class=\"btn btn-primary generate-action\" data-next=\"3\">更新方案卡</button>", "<button class=\"btn btn-primary generate-action\" data-next=\"3\" disabled title=\"待竞彩销售数据确认\">销售数据待确认</button>"],
    ["规则 SPORTTERY-2026.07 · 竞彩销售数据待确认", "竞彩规则版本与销售数据待确认"],
    ["<strong class=\"num\" id=\"ticketMultiple\">2 倍</strong>", "<strong class=\"num\" id=\"ticketMultiple\">待确认</strong>"],
    ["<strong class=\"num\" id=\"ticketStake\">¥4</strong>", "<strong class=\"num\" id=\"ticketStake\">—</strong>"],
    ["赔率为生成时快照，以体彩店实际为准。", "赔率与销售状态尚未取得可信快照。"],
    ["<button class=\"btn btn-secondary generate-action\">生成方案卡</button>", "<button class=\"btn btn-secondary generate-action\" disabled title=\"待竞彩销售数据确认\">销售数据待确认</button>"],
    ["type=\"button\" data-export=\"copy\"", "type=\"button\" data-export=\"copy\" disabled title=\"待竞彩销售数据确认\""],
    ["type=\"button\" data-export=\"download\"", "type=\"button\" data-export=\"download\" disabled title=\"待竞彩销售数据确认\""],
    ["function setExpiredState(on){const banner=document.getElementById('expiredBanner');banner.hidden=!on;document.querySelectorAll('.export-action,.generate-action,[data-adopt]').forEach(control=>{control.disabled=on;", "function setExpiredState(on){const banner=document.getElementById('expiredBanner');banner.hidden=false;document.querySelectorAll('.export-action,.generate-action,[data-adopt]').forEach(control=>{control.disabled=true;"]
  ]);
  write(file, html);
}

{
  const file = "alea-admin.html";
  let html = read(file);
  html = replaceAll(html, [
    ["<div class=\"qa-row\"><span class=\"qa-icon\">通过</span><span>玩法、赔率与停售时间待销售数据确认</span><span class=\"status status-good\">通过</span></div>", "<div class=\"qa-row\"><span class=\"qa-icon\">!</span><span>玩法、赔率与停售时间待销售数据确认</span><span class=\"status status-warn\">警告</span></div>"],
    ["<p>AI 结论、投票、玩法、串关结构、赔率快照、倍数与金额全部只读；管理员只能添加备注。</p>", "<p>本页隔离展示审核流程组件；AI 结论与投票只读，竞彩销售字段保持待确认，管理员只能添加备注。</p>"]
  ]);
  write(file, html);
}

console.log("PRD v1.8 对齐完成");
