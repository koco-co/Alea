import fs from 'node:fs';

function read(name) {
  return fs.readFileSync(name, 'utf8');
}

function write(name, source) {
  fs.writeFileSync(name, source);
}

function replace(source, before, after, label) {
  if (!source.includes(before)) {
    console.warn(`Skipped already-applied or unavailable target: ${label}`);
    return source;
  }
  return source.replace(before, after);
}

function replaceAll(source, before, after, label) {
  if (!source.includes(before)) {
    console.warn(`Skipped already-applied or unavailable target: ${label}`);
    return source;
  }
  return source.split(before).join(after);
}

let consoleHtml = read('alea-console.html');
if (consoleHtml.includes("history:[{date:'07/17'")) {
consoleHtml = replaceAll(consoleHtml, '4 / 6', '5 / 7', 'console fixed vote display');
consoleHtml = replaceAll(consoleHtml, '4/6', '5/7', 'console compact fixed vote display');
consoleHtml = replaceAll(
  consoleHtml,
  'Qwen-1 已停用并从本桌分母排除；71% 为六名有效实例的冻结加权共识。',
  '七个实例均已启用并冻结；71% 为七名有效实例的冻结加权共识。',
  'console frozen participant explanation',
);
consoleHtml = replaceAll(
  consoleHtml,
  '6 个启用实例独立提名；Qwen-1 已停用并从本桌分母排除，西班牙 vs 阿根廷以 5/7 原始票入围。',
  '7 个启用实例独立提名；西班牙 vs 阿根廷以 5/7 原始票入围。',
  'console replay participant count',
);
consoleHtml = replace(
  consoleHtml,
  "history:[{date:'07/17',match:'西班牙 vs 阿根廷',prediction:'2:0',actual:'1:2',marks:[false,false,false,false]},{date:'07/14',match:'历史比赛资料待接入',prediction:'1:0',actual:'0:0',marks:[false,false,true,false]}],lessons:[{source:'07/17 · 西班牙',text:'高估主场压迫，低估对手转换效率。',injected:true},{source:'07/14 · 资料待接入',text:'伤停来源确认过晚；需在终投前二次核验。',injected:false}]",
  'history:[],lessons:[]',
  'model profile premature history',
);
consoleHtml = consoleHtml.replace(
  /<div class="review-card-flow" data-od-id="review-card-list">[\s\S]*?\n        <\/div>\n      <\/div>\n      <div class="review-detail-shell"/,
  `<div class="review-card-flow" data-od-id="review-card-list">
          <div class="card review-empty" id="reviewEmpty" role="status" aria-live="polite">
            <h2>赛果确认后才会生成复盘</h2>
            <p>2026 世界杯决赛尚未开赛；当前没有可核验的历史复盘、实际比分或已发布教训。接入真实公证记录与官方赛果后，本页才会出现可筛选记录。</p>
          </div>
        </div>
      </div>
      <div class="review-detail-shell"`,
);
consoleHtml = replaceAll(consoleHtml, '西班牙 vs 阿根廷</h1><p id="reviewReportSummary">从错因、共性与教训三个层次解释这场偏差。', '赛果待确认</h1><p id="reviewReportSummary">当前没有可核验的复盘详情。', 'review detail default title');
consoleHtml = replaceAll(consoleHtml, 'id="reviewReportResult">未中', 'id="reviewReportResult">未生成', 'review detail default result');
consoleHtml = replaceAll(consoleHtml, 'id="reviewReportDate">2026-07-17', 'id="reviewReportDate">日期待确认', 'review detail default date');
consoleHtml = replaceAll(consoleHtml, 'id="reviewReportLedger">公证 N8C4-02', 'id="reviewReportLedger">公证记录待接入', 'review detail default ledger');
consoleHtml = replaceAll(consoleHtml, 'id="reviewPredictedScore">2:0', 'id="reviewPredictedScore">—', 'review detail default prediction');
consoleHtml = replaceAll(consoleHtml, 'id="reviewActualScore">1:2', 'id="reviewActualScore">—', 'review detail default actual');
consoleHtml = replaceAll(consoleHtml, 'id="reviewPredictionReason">判断：主队压迫将限制客队转换。', 'id="reviewPredictionReason">等待真实公证预测。', 'review detail default prediction explanation');
consoleHtml = replaceAll(consoleHtml, 'id="reviewActualSummary">实际：客队两次转换兑现，主队压迫后场暴露。', 'id="reviewActualSummary">等待官方赛果确认。', 'review detail default actual explanation');
consoleHtml = consoleHtml.replace(
  /const reviewReports=\{[\s\S]*?\};const reviewListShell=/,
  'const reviewReports={};const reviewListShell=',
);
consoleHtml = replace(
  consoleHtml,
  "function openReviewDetail(id){document.title='Alea · 模型复盘';const report=reviewReports[id]||reviewReports['rvw-lancheng'];activateReviewsView();reviewListShell.hidden=true;reviewDetailShell.hidden=false;renderReviewReport(report);",
  "function openReviewDetail(id){document.title='Alea · 赛后复盘';const report=reviewReports[id];activateReviewsView();if(!report){closeReviewDetail();showToast('赛果待确认：当前没有可核验的复盘详情');return}reviewListShell.hidden=true;reviewDetailShell.hidden=false;renderReviewReport(report);",
  'review missing-detail recovery',
);
write('alea-console.html', consoleHtml);
}
consoleHtml = read('alea-console.html');
consoleHtml = replaceAll(
  consoleHtml,
  '<span class="status good">命中</span><div class="mini-score">2:1</div><p>预测 2:1 · 实际 2:1</p>',
  '<span class="status good">命中</span><div class="mini-score">—</div><p>组件状态示意 · 不代表当前赛事赛果</p>',
  'neutralize current-fixture hit component sample',
);
consoleHtml = replaceAll(
  consoleHtml,
  '<span class="status bad">未中</span><div class="mini-score">2:0</div><p>实际比分 1:2</p>',
  '<span class="status bad">未中</span><div class="mini-score">—</div><p>组件状态示意 · 不代表当前赛事赛果</p>',
  'neutralize current-fixture miss component sample',
);
write('alea-console.html', consoleHtml);

let predictionsHtml = read('alea-predictions.html');
predictionsHtml = replaceAll(predictionsHtml, '4/6', '5/7', 'predictions compact vote display');
predictionsHtml = replaceAll(predictionsHtml, '6 名有效参与者', '7 名有效参与者', 'predictions participant count');
predictionsHtml = replaceAll(
  predictionsHtml,
  '6 个启用实例独立提名；Qwen-1 已停用并从本桌分母排除，西班牙 vs 阿根廷以 5/7 原始票进入推演。',
  '7 个启用实例独立提名；西班牙 vs 阿根廷以 5/7 原始票进入推演。',
  'predictions selection event',
);
predictionsHtml = replaceAll(
  predictionsHtml,
  '7 名有效参与者；Qwen-1 已停用并从终投、票权快照与证据引用中排除。',
  '7 名有效参与者；Qwen-1 已启用并进入终投、票权快照与证据引用。',
  'predictions notary participant statement',
);
predictionsHtml = replaceAll(predictionsHtml, 'MODEL-6.1 / CONN-6.4', 'MODEL-7.1 / CONN-7.4', 'predictions model and connection versions');
predictionsHtml = replaceAll(predictionsHtml, 'LINEUP-6.4', 'LINEUP-7.4', 'predictions lineup version');
predictionsHtml = replaceAll(predictionsHtml, 'HISTORY-6.1 / 6 份', 'HISTORY-7.1 / 7 份', 'predictions history version');
predictionsHtml = replaceAll(predictionsHtml, 'SCORE-1 / VOTE-6.1', 'SCORE-1 / VOTE-7.1', 'predictions vote version');
predictionsHtml = replace(
  predictionsHtml,
  'aria-label="支持 2 比 1 的 AI：Claude-1、GPT-1、DeepSeek-1、Gemini-1"',
  'aria-label="支持 2 比 1 的 AI：Claude-1、GPT-1、DeepSeek-1、Gemini-1、Qwen-1"',
  'predictions supporting voters label',
);
predictionsHtml = replace(
  predictionsHtml,
  '<button class="ai-avatar vote-avatar" type="button" data-instance="1" data-vote-name="Gemini-1" data-vote-score="原型统计待接入" data-vote-quality="AI 推演数据" data-vote-reason="在不引入未核验首发或伤停的前提下，支持西班牙 2:1。" aria-label="Gemini-1，查看 AI 推演依据" aria-expanded="false" aria-controls="voteDetailPanel"><img class="ai-mark" src="assets/vendors/gemini.svg" alt=""></button></div><span class="vote-count">4 票</span>',
  '<button class="ai-avatar vote-avatar" type="button" data-instance="1" data-vote-name="Gemini-1" data-vote-score="原型统计待接入" data-vote-quality="AI 推演数据" data-vote-reason="在不引入未核验首发或伤停的前提下，支持西班牙 2:1。" aria-label="Gemini-1，查看 AI 推演依据" aria-expanded="false" aria-controls="voteDetailPanel"><img class="ai-mark" src="assets/vendors/gemini.svg" alt=""></button><button class="ai-avatar vote-avatar" type="button" data-instance="1" data-vote-name="Qwen-1" data-vote-score="原型统计待接入" data-vote-quality="AI 推演数据" data-vote-reason="在冻结事实边界内支持西班牙 2:1，并保留阿根廷取得进球的分支。" aria-label="Qwen-1，查看 AI 推演依据" aria-expanded="false" aria-controls="voteDetailPanel"><img class="ai-mark" src="assets/vendors/qwen.svg" alt=""></button></div><span class="vote-count">5 票</span>',
  'predictions Qwen supporting vote',
);
predictionsHtml = replace(
  predictionsHtml,
  '<div class="stance-item"><span class="ai-id"><span class="ai-avatar" data-instance="1"><img class="ai-mark" src="assets/vendors/kimi.png" alt=""></span><span><strong>Kimi-1</strong><small>选手 G</small></span></span><span class="mono">2:2</span></div>',
  '<div class="stance-item"><span class="ai-id"><span class="ai-avatar" data-instance="1"><img class="ai-mark" src="assets/vendors/qwen.svg" alt=""></span><span><strong>Qwen-1</strong><small>选手 E</small></span></span><span class="mono">2:1</span></div><div class="stance-item"><span class="ai-id"><span class="ai-avatar" data-instance="1"><img class="ai-mark" src="assets/vendors/kimi.png" alt=""></span><span><strong>Kimi-1</strong><small>选手 G</small></span></span><span class="mono">2:2</span></div>',
  'predictions Qwen final stance',
);
write('alea-predictions.html', predictionsHtml);

let calculatorHtml = read('alea-calculator.html');
calculatorHtml = replaceAll(calculatorHtml, '4/6', '5/7', 'calculator fixed vote display');
calculatorHtml = replaceAll(calculatorHtml, '4 / 6', '5 / 7', 'calculator spaced fixed vote display');
calculatorHtml = replaceAll(
  calculatorHtml,
  '5/7 原始票、71% 冻结加权共识；停用的 Qwen-1 不进入本桌。',
  '5/7 原始票、71% 冻结加权共识；七个启用实例与冻结阵容一致。',
  'calculator participant statement',
);
calculatorHtml = replace(
  calculatorHtml,
  "const requestedSampleMode=location.hash==='#sample',initialStep=location.hash.match(/^#step-([123])$/)?.[1]||'1';showStep(initialStep);setMode(requestedSampleMode?'sample':'locked',{updateHash:requestedSampleMode});",
  "function applyCalculatorHash(){if(location.hash==='#sample'){setMode('sample',{updateHash:false});return}setMode('locked',{updateHash:false});showStep(location.hash.match(/^#step-([123])$/)?.[1]||'1')}window.addEventListener('hashchange',applyCalculatorHash);applyCalculatorHash();",
  'calculator hash initialization',
);
write('alea-calculator.html', calculatorHtml);

let adminHtml = read('alea-admin.html');
adminHtml = replaceAll(adminHtml, '4 / 6', '5 / 7', 'admin fixed vote display');
adminHtml = replaceAll(adminHtml, '4/6', '5/7', 'admin compact fixed vote display');
adminHtml = replaceAll(adminHtml, '6/6 冻结参与实例', '7/7 冻结参与实例', 'admin live participant count');
adminHtml = replaceAll(adminHtml, '6 / 6 · 冻结参与实例', '7 / 7 · 冻结参与实例', 'admin participant list count');
adminHtml = replaceAll(adminHtml, '六份独立预测已收齐', '七份独立预测已收齐', 'admin live prediction count');
adminHtml = replaceAll(
  adminHtml,
  'Qwen-1 已停用并排除；其余 AI 推演数据彼此不可见',
  '七个启用实例的 AI 推演数据彼此不可见',
  'admin live frozen lineup statement',
);
adminHtml = replaceAll(adminHtml, '正在汇总 6 个启用实例的提名与入围票。', '正在汇总 7 个启用实例的提名与入围票。', 'admin stage selection count');
adminHtml = replaceAll(adminHtml, '6 份比分预测独立生成，互不可见；Qwen-1 已排除。', '7 份比分预测独立生成，互不可见。', 'admin stage prediction count');
adminHtml = replace(
  adminHtml,
  '<div class="lineup-card missing"><span class="vendor-avatar" data-instance="1"><img src="assets/vendors/qwen.svg" alt="阿里云标识"></span><span><strong>Qwen-1</strong><small>已停用 · 不进入新圆桌</small></span></div>',
  '<div class="lineup-card"><span class="vendor-avatar" data-instance="1"><img src="assets/vendors/qwen.svg" alt="阿里云标识"></span><span><strong>Qwen-1</strong><small>已启用 · 进入新圆桌</small></span></div>',
  'admin launch Qwen state',
);
adminHtml = replace(
  adminHtml,
  '<div class="participant-row"><span class="ai-id"><span class="vendor-avatar"><img src="assets/vendors/kimi.png" alt="Kimi 标识"></span><span><strong>Kimi-1</strong><small>原型实例 G</small></span></span><span class="status status-warn">其他比分</span></div>',
  '<div class="participant-row"><span class="ai-id"><span class="vendor-avatar"><img src="assets/vendors/qwen.svg" alt="Qwen 标识"></span><span><strong>Qwen-1</strong><small>原型实例 E</small></span></span><span class="status status-good">支持 2 : 1</span></div><div class="participant-row"><span class="ai-id"><span class="vendor-avatar"><img src="assets/vendors/kimi.png" alt="Kimi 标识"></span><span><strong>Kimi-1</strong><small>原型实例 G</small></span></span><span class="status status-warn">其他比分</span></div>',
  'admin live Qwen participant',
);
adminHtml = replace(
  adminHtml,
  '<span class="muted" style="font-size:11px">支持 2 : 1 的 4 个参与实例</span>',
  '<span class="muted" style="font-size:11px">支持 2 : 1 的 5 个参与实例</span>',
  'admin publish support count',
);
adminHtml = replace(
  adminHtml,
  '<span class="vendor-avatar"><img src="assets/vendors/gemini.svg" alt="Gemini 标识"></span></div></div>',
  '<span class="vendor-avatar"><img src="assets/vendors/gemini.svg" alt="Gemini 标识"></span><span class="vendor-avatar"><img src="assets/vendors/qwen.svg" alt="Qwen 标识"></span></div></div>',
  'admin publish Qwen voter avatar',
);
adminHtml = replace(
  adminHtml,
  "{id:'qwen',name:'阿里云 · Qwen',asset:'assets/vendors/qwen.svg',protocol:'DashScope API',baseUrl:'https://dashscope.aliyuncs.com/compatible-mode/v1',keyState:'saved',keyTail:'A508',available:false,added:true,models:['qwen3-max','qwen3-plus'],selectedModel:'qwen3-max',modelState:'ready',reasoning:true,testState:'failure',testAttempts:0,instances:[{id:1,nickname:'Qwen-1',enabled:false,retired:false,model:'qwen3-max',reasoning:'中',timeout:60,concurrency:1,promptVersion:'prediction-v1.6'}]}",
  "{id:'qwen',name:'阿里云 · Qwen',asset:'assets/vendors/qwen.svg',protocol:'DashScope API',baseUrl:'https://dashscope.aliyuncs.com/compatible-mode/v1',keyState:'saved',keyTail:'A508',available:true,added:true,models:['qwen3-max','qwen3-plus'],selectedModel:'qwen3-max',modelState:'ready',reasoning:true,testState:'success',testAttempts:1,instances:[{id:1,nickname:'Qwen-1',enabled:true,retired:false,model:'qwen3-max',reasoning:'中',timeout:60,concurrency:1,promptVersion:'prediction-v1.6'}]}",
  'admin Qwen provider availability',
);
write('alea-admin.html', adminHtml);

let css = read('alea.css');
css = replace(
  css,
  '.lineup-provider-list{display:flex;max-width:100%;overflow-x:auto;padding-bottom:3px;scroll-snap-type:x mandatory}.lineup-provider-button{min-width:218px;scroll-snap-align:start}',
  '.lineup-provider-list{display:grid;max-width:100%;overflow:visible;padding-bottom:0;scroll-snap-type:none}.lineup-provider-button{min-width:0;width:100%;scroll-snap-align:none}',
  'mobile lineup provider catalog',
);
write('alea.css', css);

let validator = read('scripts/validate-prototype.mjs');
if (!validator.includes('PRD v1.9 冻结票数不存在 4/6 残留')) validator += `

const frozenFiles = ['alea.html', 'alea-console.html', 'alea-predictions.html', 'alea-calculator.html', 'alea-admin.html'];
const frozenSource = frozenFiles.map(file => fs.readFileSync(file, 'utf8')).join('\\n');
check(!/4\\s*\\/\\s*6/.test(frozenSource), 'PRD v1.9 冻结票数不存在 4/6 残留');
check((frozenSource.match(/5\\s*\\/\\s*7/g) || []).length >= 8, 'PRD v1.9 固定票数 5/7 跨页面一致');
check(!/Qwen-1 已停用|Qwen-1 已排除|停用的 Qwen-1/.test(frozenSource), 'Qwen-1 冻结阵容状态跨页面一致');
check(!/2026-07-17[\\s\\S]{0,180}(西班牙 vs 阿根廷|实际[^<]{0,30}1\\s*:\\s*2)/.test(files['alea-console.html']), '未提前伪造世界杯决赛历史赛果');
check(/addEventListener\\('hashchange',applyCalculatorHash\\)/.test(files['alea-calculator.html']), '计算器支持 #sample 深链与 hashchange');
`;
write('scripts/validate-prototype.mjs', validator);

console.log('PRD v1.9 production fixes applied');
