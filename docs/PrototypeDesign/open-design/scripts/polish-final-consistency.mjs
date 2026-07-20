import fs from "node:fs";

function dedupeRepeated(source, block) {
  while (source.includes(block + block)) source = source.replace(block + block, block);
  return source;
}

const qwenStance = '<div class="stance-item"><span class="ai-id"><span class="ai-avatar" data-instance="1"><img class="ai-mark" src="assets/vendors/qwen.svg" alt=""></span><span><strong>Qwen-1</strong><small>选手 E</small></span></span><span class="mono">2:1</span></div>';
let predictions = fs.readFileSync("alea-predictions.html", "utf8");
predictions = dedupeRepeated(predictions, qwenStance);
fs.writeFileSync("alea-predictions.html", predictions);

const qwenParticipant = '<div class="participant-row"><span class="ai-id"><span class="vendor-avatar"><img src="assets/vendors/qwen.svg" alt="Qwen 标识"></span><span><strong>Qwen-1</strong><small>原型实例 E</small></span></span><span class="status status-good">支持 2 : 1</span></div>';
let admin = fs.readFileSync("alea-admin.html", "utf8");
admin = dedupeRepeated(admin, qwenParticipant);
admin = admin.replace(
  "`已生成 history-context-limits-v1.${settingsVersionPatch}。`",
  "`已生成 system-settings-v2.${settingsVersionPatch}。`",
);
admin = admin.replace(
  ".lineup-provider-list{display:flex;max-width:100%;overflow-x:auto;padding-bottom:3px;scroll-snap-type:x mandatory}.lineup-provider-button{min-width:218px;scroll-snap-align:start}",
  ".lineup-provider-list{display:grid;max-width:100%;overflow:visible;padding-bottom:0;scroll-snap-type:none}.lineup-provider-button{min-width:0;width:100%;scroll-snap-align:none}",
);
admin = admin.replace(
  ".lineup-savebar{bottom:8px;align-items:stretch;flex-direction:column}",
  ".lineup-savebar,.settings-savebar{position:static;bottom:auto;align-items:stretch;flex-direction:column}",
);
admin = admin.replace(
  "publishMethod.addEventListener('click',()=>{document.getElementById('methodVersion').textContent='core-methodology-v1.2';document.getElementById('methodPublishState').textContent='已发布 · 审计记录保留';publishMethod.disabled=true;notify('候选方法论已发布为 v1.2')})",
  "publishMethod.addEventListener('click',()=>{document.getElementById('methodPublishState').textContent='演示完成 · 未写入生产版本';publishMethod.disabled=true;notify('流程演示已完成；生产版本仍为 core-methodology-v1.1')})",
);
admin = admin.replace(
  "document.getElementById('rollbackMethod').addEventListener('click',()=>{document.getElementById('methodVersion').textContent='core-methodology-v1.0';document.getElementById('methodPublishState').textContent='已回滚 · v1.1 与候选版本保留';notify('生产引用已回滚到 v1.0')})",
  "document.getElementById('rollbackMethod').addEventListener('click',()=>notify('回滚需要填写原因并二次确认；当前生产版本未改变'))",
);
fs.writeFileSync("alea-admin.html", admin);

let css = fs.readFileSync("alea.css", "utf8");
if (!css.includes(".review-empty{grid-column:1/-1")) {
  css += "\n.review-empty{grid-column:1/-1;min-height:220px;display:grid;place-content:center;text-align:center}.review-empty p{max-width:720px;margin:8px auto 0}\n";
}
fs.writeFileSync("alea.css", css);

let consoleHtml = fs.readFileSync("alea-console.html", "utf8");
const wikiSection = `<section class="console-view" id="wiki" data-od-id="wiki-view"><div class="page-head"><div><p class="eyebrow">赛事资料 · 资料档案</p><h1>只展示已确认身份，扩展资料保持缺失。</h1><p>当前仅接入 FIFA 已确认的决赛参赛队身份；球员、教练、裁判、积分与近期战绩均没有可信资料源。</p></div><span class="status neutral">资料源边界已锁定</span></div><div class="tabs" role="tablist" aria-label="赛事资料类型"><button class="tab active" role="tab" aria-selected="true" data-wiki-tab="teams">球队资料</button><button class="tab" role="tab" aria-selected="false" disabled title="球员资料源待接入">球员资料</button><button class="tab" role="tab" aria-selected="false" disabled title="教练资料源待接入">教练资料</button><button class="tab" role="tab" aria-selected="false" disabled title="裁判资料源待接入">裁判资料</button></div><div class="wiki-grid" id="wikiGrid" style="margin-top:18px"><article class="card wiki-card"><img src="assets/flag-spain.png" alt="西班牙国旗" style="width:64px;height:72px;object-fit:contain;margin:0 auto"><h3 style="margin-top:12px">西班牙</h3><p>2026 FIFA 世界杯决赛参赛队 · 身份已确认</p><span class="status good" style="margin-top:12px">来源：FIFA</span></article><article class="card wiki-card"><img src="assets/flag-argentina.png" alt="阿根廷国旗" style="width:64px;height:72px;object-fit:contain;margin:0 auto"><h3 style="margin-top:12px">阿根廷</h3><p>2026 FIFA 世界杯决赛参赛队 · 身份已确认</p><span class="status good" style="margin-top:12px">来源：FIFA</span></article><article class="card wiki-card review-empty"><h3>扩展资料待接入</h3><p>不以演示值补齐球员、教练、裁判、积分、阵型或近期战绩。可信来源接入并完成版本化后，本区才会开放筛选与详情。</p></article></div></section>`;
if (!consoleHtml.includes('id="wikiDetailShell"')) {
  consoleHtml = consoleHtml.replace(
    /<section class="console-view" id="wiki"[\s\S]*?<\/section>\n  <\/main>/,
    `${wikiSection}\n  </main>`,
  );
}
consoleHtml = consoleHtml.replace(
  '<a href="#predictions" data-view="predictions">太玄问机</a><a href="#calculator" data-view="calculator">竞彩方案</a>',
  '<a href="alea-predictions.html#today">太玄问机</a><a href="alea-calculator.html">竞彩方案</a>',
);
consoleHtml = consoleHtml.replace(
  "function appendRealPnlAudit(action,summary){const row=document.createElement('div');",
  "function appendRealPnlAudit(action,summary){if(realPnlAudit.children.length===1&&realPnlAudit.textContent.includes('审计日志为空'))realPnlAudit.innerHTML='';const row=document.createElement('div');",
);
fs.writeFileSync("alea-console.html", consoleHtml);

let validator = fs.readFileSync("scripts/validate-prototype.mjs", "utf8");
const anchor = 'check(/addEventListener\\(\'hashchange\',applyCalculatorHash\\)/.test(calculatorSource), "计算器支持 #sample 深链与 hashchange");';
const checks = `${anchor}
check((fs.readFileSync("alea-predictions.html", "utf8").match(/<strong>Qwen-1<\\/strong><small>选手 E<\\/small>/g) || []).length === 1, "预测最终立场仅包含一个 Qwen-1");
check((fs.readFileSync("alea-admin.html", "utf8").match(/<strong>Qwen-1<\\/strong><small>原型实例 E<\\/small>/g) || []).length === 1, "管理直播参与列表仅包含一个 Qwen-1");
check(!/lineup-provider-list\\{display:flex;max-width:100%;overflow-x:auto/.test(fs.readFileSync("alea-admin.html", "utf8")), "移动端厂商目录为单栏且无横向裁切");`;
const methodSafetyCheck = 'check(!/methodVersion[^\\\\n]{0,220}core-methodology-v1\\\\.2/.test(fs.readFileSync("alea-admin.html", "utf8")), "方法论演示发布不会改动生产版本");';
if (!validator.includes("预测最终立场仅包含一个 Qwen-1")) {
  if (!validator.includes(anchor)) throw new Error("validator anchor not found");
  validator = validator.replace(anchor, checks);
}
if (!validator.includes("方法论演示发布不会改动生产版本")) {
  validator = validator.replace(checks, `${checks}\n${methodSafetyCheck}`);
}
if (!validator.includes("赛事资料不使用虚构积分与战绩")) {
  const wikiChecks = `check(!/crest-beijing|crest-haijia|积分 37|积分 24/.test(fs.readFileSync("alea-console.html", "utf8")), "赛事资料不使用虚构积分与战绩");
check(/href="alea-predictions\\.html#today">太玄问机<\\/a><a href="alea-calculator\\.html">竞彩方案/.test(fs.readFileSync("alea-console.html", "utf8")), "移动端底栏指向独立预测与方案页");`;
  validator = validator.replace(methodSafetyCheck, `${methodSafetyCheck}\n${wikiChecks}`);
}
fs.writeFileSync("scripts/validate-prototype.mjs", validator);

console.log("Final consistency polish applied");
