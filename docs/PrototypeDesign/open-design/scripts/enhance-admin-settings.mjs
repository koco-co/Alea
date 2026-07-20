import fs from "node:fs";

const file = "alea-admin.html";
let html = fs.readFileSync(file, "utf8");

const settingsSection = `
        <section class="admin-screen" id="settings" data-od-id="admin-settings-screen">
          <header class="admin-head"><div><p class="eyebrow">系统管理 · 系统设置 · PRD 15.6</p><h1>每一项运行参数都要可定位、可验证、可追溯。</h1><p>设置按业务边界分组；修改只生成新版本，不覆盖历史圆桌、方案或结算记录。</p></div><span class="status status-neutral" id="settingsVersion">system-settings-v2.0</span></header>
          <div class="settings-search card"><label for="settingsSearch"><span class="eyebrow">快速定位</span><strong>搜索设置</strong></label><input id="settingsSearch" type="search" placeholder="例如：评分、风控、同步、提示词" autocomplete="off"><span class="status status-neutral" id="settingsSearchStatus" role="status">5 个分组</span></div>
          <div class="settings-layout">
            <aside class="card settings-index" aria-label="设置分组">
              <a class="active" href="#settings-scoring">评分与规则</a>
              <a href="#settings-risk">模拟盘与风控</a>
              <a href="#settings-automation">数据与自动化</a>
              <a href="#settings-access">用户管理</a>
              <a href="#settings-prompts">提示词与方法论</a>
            </aside>
            <div class="settings-panels">
              <section class="card settings-panel" id="settings-scoring" data-settings-group="评分 规则 权重 体彩 版本">
                <div class="admin-card-head"><div><p class="eyebrow">scoring-rules-v1.3</p><h2>评分权重与竞彩规则</h2></div><button class="btn btn-secondary" type="button" data-settings-save>保存更改</button></div>
                <div class="settings-form-grid three">
                  <div class="admin-field"><label for="settingsScoreAccuracy">准确率权重（%）</label><input id="settingsScoreAccuracy" type="number" min="0" max="100" value="50" aria-describedby="settingsValidation"><small>当前版本 50%</small></div>
                  <div class="admin-field"><label for="settingsScoreCalibration">校准度权重（%）</label><input id="settingsScoreCalibration" type="number" min="0" max="100" value="25" aria-describedby="settingsValidation"><small>当前版本 25%</small></div>
                  <div class="admin-field"><label for="settingsScoreProfit">模拟收益权重（%）</label><input id="settingsScoreProfit" type="number" min="0" max="100" value="25" aria-describedby="settingsValidation"><small>三项之和必须为 100%</small></div>
                </div>
                <div class="readonly-facts"><div class="readonly-fact"><span>当前评分版本</span><strong>scoring-rules-v1.3 · 2026-07-01 生效</strong></div><div class="readonly-fact"><span>历史版本</span><strong>v1.2 · v1.1 · 只读可回看</strong></div><div class="readonly-fact"><span>竞彩规则</span><strong>sports-lottery-rules-v1.0 · 销售规则源待连接</strong></div></div>
              </section>

              <section class="card settings-panel" id="settings-risk" data-settings-group="模拟盘 风控 资金 仓位 风险 文案">
                <div class="admin-card-head"><div><p class="eyebrow">simulation-risk-v1.4</p><h2>模拟盘与风险边界</h2></div><button class="btn btn-secondary" type="button" data-settings-save>保存更改</button></div>
                <div class="settings-form-grid">
                  <div class="admin-field"><label for="settingsInitialBankroll">初始资金（模拟币）</label><input id="settingsInitialBankroll" type="number" min="1000" max="10000000" step="1000" value="100000"></div>
                  <div class="admin-field"><label for="settingsExposure">单日风险敞口上限（%）</label><input id="settingsExposure" type="number" min="1" max="100" value="20"></div>
                  <div class="admin-field"><label for="settingsPositionMin">单方案仓位下限（%）</label><input id="settingsPositionMin" type="number" min="0" max="100" value="1"></div>
                  <div class="admin-field"><label for="settingsPositionMax">单方案仓位上限（%）</label><input id="settingsPositionMax" type="number" min="1" max="100" value="5"></div>
                  <div class="admin-field wide"><label for="settingsRiskCopy">风险提示文案</label><textarea id="settingsRiskCopy" rows="3">本产品仅用于 AI 推演研究与娱乐展示，不构成投注建议；请量力而行并遵守所在地法律。</textarea><small>发布到所有预测与方案页面；修改后生成新版本。</small></div>
                </div>
              </section>

              <section class="card settings-panel" id="settings-automation" data-settings-group="数据 自动化 同步 定时 圆桌 复盘 历史 上下文">
                <div class="admin-card-head"><div><p class="eyebrow">automation-policy-v2.0</p><h2>数据同步与圆桌自动化</h2></div><button class="btn btn-secondary" type="button" data-settings-save>保存更改</button></div>
                <div class="settings-form-grid three">
                  <div class="admin-field"><label for="settingsSyncCadence">常规同步周期（分钟）</label><input id="settingsSyncCadence" type="number" min="5" max="1440" value="30"><small>临近开赛可由管道策略加密。</small></div>
                  <div class="admin-field"><label for="settingsScheduleTime">每日自动发起时间</label><input id="settingsScheduleTime" type="time" value="08:00"></div>
                  <div class="admin-field"><label for="settingsDefaultLineup">默认阵容</label><select id="settingsDefaultLineup"><option value="lineup-v1.6">lineup-v1.6 · 7 实例</option><option value="manual">每次手动选择</option></select></div>
                  <div class="admin-field"><label for="settingsDebateRounds">默认辩论轮数</label><input id="settingsDebateRounds" type="number" min="1" max="5" value="2"></div>
                  <div class="admin-field"><label for="settingsCandidateLimit">默认入围上限</label><input id="settingsCandidateLimit" type="number" min="1" max="20" value="8"></div>
                  <div class="admin-field"><label for="settingsRecentLimit">近期已结算记录</label><input id="settingsRecentLimit" type="number" min="1" max="50" value="10" aria-describedby="settingsRecentHelp settingsValidation"><small id="settingsRecentHelp">范围 1–50，默认 10。</small></div>
                  <div class="admin-field"><label for="settingsLessonLimit">有效教训上限</label><input id="settingsLessonLimit" type="number" min="1" max="20" value="5" aria-describedby="settingsLessonHelp settingsValidation"><small id="settingsLessonHelp">范围 1–20，默认 5。</small></div>
                </div>
                <div class="settings-toggle-grid">
                  <label class="lineup-switch"><input id="settingsAutoRoundtable" type="checkbox" checked><span><strong>开启每日定时圆桌</strong><small>按上方时间、阵容与轮数创建新圆桌</small></span></label>
                  <label class="lineup-switch"><input id="settingsAutoReview" type="checkbox" checked><span><strong>赛果确认后自动创建复盘</strong><small>赛果冲突未裁定时不会触发</small></span></label>
                </div>
              </section>

              <section class="card settings-panel" id="settings-access" data-settings-group="用户 管理 搜索 状态 禁用 恢复 权限">
                <div class="admin-card-head"><div><p class="eyebrow">访问控制</p><h2>用户与角色操作</h2></div><a class="btn btn-secondary" href="#users">打开用户管理</a></div>
                <div class="readonly-facts"><div class="readonly-fact"><span>启用账户</span><strong>2</strong></div><div class="readonly-fact"><span>待接受邀请</span><strong>1</strong></div><div class="readonly-fact"><span>权限原则</span><strong>普通用户不渲染任何管理员入口</strong></div></div>
                <div class="admin-state-callout"><strong>审计要求</strong><p>禁用、恢复和角色变更必须二次确认，并记录操作者、时间与原因；历史预测、公证、积分与账本不随账户状态删除。</p></div>
              </section>

              <section class="card settings-panel" id="settings-prompts" data-settings-group="提示词 方法论 版本 发布 回滚">
                <div class="admin-card-head"><div><p class="eyebrow">只读版本引用</p><h2>提示词与核心方法论</h2></div><a class="btn btn-secondary" href="#methodology">查看方法提议</a></div>
                <div class="readonly-facts"><div class="readonly-fact"><span>预测提示词</span><strong>prediction-v1.6 · 生效中</strong></div><div class="readonly-fact"><span>复盘提示词</span><strong>review-v1.2 · 生效中</strong></div><div class="readonly-fact"><span>方法论</span><strong>core-methodology-v1.1 · 2026-07-19 发布</strong></div></div>
                <div class="queue-list"><div class="queue-row"><div><strong>core-methodology-v1.1</strong><small>当前生产引用 · 完整内容与发布记录只读</small></div><span class="status status-good">生效中</span></div><div class="queue-row"><div><strong>core-methodology-v1.0</strong><small>历史版本 · 可从方法评审页发起回滚</small></div><span class="status status-neutral">历史</span></div></div>
              </section>

              <p class="lineup-validation settings-validation" id="settingsValidation" role="alert"></p>
              <div class="settings-savebar" data-od-id="settings-save-bar"><div><span class="status status-neutral" id="settingsSaveStatus" role="status" aria-live="polite">正在加载</span><p id="settingsSaveHelp">正在读取 system-settings-v2.0。</p></div><div class="lineup-save-actions"><button class="btn btn-secondary" id="discardSettings" type="button" disabled>撤销修改</button><button class="btn btn-primary" id="saveSettings" type="button" disabled>保存新版本</button></div></div>
            </div>
          </div>
          <section class="lineup-dialog" id="settingsLeaveDialog" role="dialog" aria-modal="true" aria-labelledby="settingsLeaveTitle" aria-describedby="settingsLeaveDescription" hidden><h2 id="settingsLeaveTitle">系统设置还有未保存修改</h2><p id="settingsLeaveDescription">离开会丢弃本次设置草稿。你可以留在此页修正并保存为新版本。</p><div class="lineup-inline-actions"><button class="btn btn-primary" id="staySettings" type="button">留在此页</button><button class="btn btn-secondary" id="leaveSettings" type="button">不保存并离开</button></div></section>
        </section>
`;

const sectionPattern = /        <section class="admin-screen" id="settings"[\s\S]*?\n        <section class="admin-screen" id="methodology"/;
if (!sectionPattern.test(html)) throw new Error("settings section not found");
html = html.replace(sectionPattern, `${settingsSection}\n        <section class="admin-screen" id="methodology"`);

const cssInsertion = `
    .settings-search{display:grid;grid-template-columns:auto minmax(220px,1fr) auto;gap:14px;align-items:center;margin-bottom:14px;padding:14px 16px}.settings-search label span,.settings-search label strong{display:block}.settings-search label strong{margin-top:2px;font-size:13px}.settings-search input{width:100%}
    .settings-panels{display:grid;gap:14px}.settings-form-grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.settings-toggle-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}.settings-toggle-grid .lineup-switch{align-items:flex-start;padding:12px;border:1px solid var(--border-soft);border-radius:var(--radius-md);background:var(--surface-warm)}.settings-toggle-grid strong,.settings-toggle-grid small{display:block}.settings-toggle-grid small{margin-top:3px;color:var(--muted);font-size:9px;line-height:1.45}.settings-validation{position:sticky;bottom:92px;z-index:19;margin:0;padding:0 2px}.settings-panel[hidden]{display:none}
`;
if (!html.includes(".settings-search{")) html = html.replace("    @media(max-width:1000px)", `${cssInsertion}    @media(max-width:1000px)`);
html = html.replace(
  "@media(max-width:760px){.admin-main",
  "@media(max-width:760px){.settings-search{grid-template-columns:1fr}.settings-search .status{justify-self:start}.settings-form-grid.three,.settings-toggle-grid{grid-template-columns:minmax(0,1fr)}.admin-main",
);

const controlsBefore = `const settingsControls=[document.getElementById('settingsRecentLimit'),document.getElementById('settingsLessonLimit'),document.getElementById('settingsAutoRoundtable'),document.getElementById('settingsAutoReview')],settingsSaveButton=document.getElementById('saveSettings'),settingsDiscardButton=document.getElementById('discardSettings');`;
const controlsAfter = `const settingsControls=['settingsScoreAccuracy','settingsScoreCalibration','settingsScoreProfit','settingsInitialBankroll','settingsExposure','settingsPositionMin','settingsPositionMax','settingsRiskCopy','settingsSyncCadence','settingsScheduleTime','settingsDefaultLineup','settingsDebateRounds','settingsCandidateLimit','settingsRecentLimit','settingsLessonLimit','settingsAutoRoundtable','settingsAutoReview'].map(id=>document.getElementById(id)),settingsSaveButton=document.getElementById('saveSettings'),settingsDiscardButton=document.getElementById('discardSettings');`;
if (!html.includes(controlsBefore)) throw new Error("settings controls initializer not found");
html = html.replace(controlsBefore, controlsAfter);

html = html.replace(
  `function readSettings(){return JSON.stringify({recent:Number(settingsControls[0].value),lessons:Number(settingsControls[1].value),autoRoundtable:settingsControls[2].checked,autoReview:settingsControls[3].checked})}`,
  `function readSettings(){return JSON.stringify(Object.fromEntries(settingsControls.map(control=>[control.id,control.type==='checkbox'?control.checked:control.type==='number'?Number(control.value):control.value])))}`,
);
html = html.replace(
  `function applySettings(snapshot){const data=JSON.parse(snapshot);settingsControls[0].value=data.recent;settingsControls[1].value=data.lessons;settingsControls[2].checked=data.autoRoundtable;settingsControls[3].checked=data.autoReview}`,
  `function applySettings(snapshot){const data=JSON.parse(snapshot);settingsControls.forEach(control=>{control[control.type==='checkbox'?'checked':'value']=data[control.id]})}`,
);
html = html.replace(
  /function settingsErrors\(\)\{[\s\S]*?return errors\}/,
  `function settingsErrors(){const value=id=>Number(document.getElementById(id).value),errors=[];settingsControls.forEach(input=>input.removeAttribute('aria-invalid'));const fail=(id,message)=>{document.getElementById(id).setAttribute('aria-invalid','true');errors.push(message)};if(value('settingsScoreAccuracy')+value('settingsScoreCalibration')+value('settingsScoreProfit')!==100)fail('settingsScoreProfit','三项评分权重之和必须为 100%。');if(value('settingsInitialBankroll')<1000)fail('settingsInitialBankroll','初始资金不得低于 1,000。');if(value('settingsPositionMin')<0||value('settingsPositionMax')>100||value('settingsPositionMin')>value('settingsPositionMax'))fail('settingsPositionMax','仓位上限必须不小于下限且不超过 100%。');if(value('settingsExposure')<1||value('settingsExposure')>100)fail('settingsExposure','风险敞口必须在 1–100% 之间。');if(value('settingsSyncCadence')<5||value('settingsSyncCadence')>1440)fail('settingsSyncCadence','同步周期必须在 5–1440 分钟之间。');if(value('settingsDebateRounds')<1||value('settingsDebateRounds')>5)fail('settingsDebateRounds','辩论轮数必须为 1–5。');if(value('settingsCandidateLimit')<1||value('settingsCandidateLimit')>20)fail('settingsCandidateLimit','入围上限必须为 1–20。');if(value('settingsRecentLimit')<1||value('settingsRecentLimit')>50)fail('settingsRecentLimit','最近记录条数必须为 1–50 的整数。');if(value('settingsLessonLimit')<1||value('settingsLessonLimit')>20)fail('settingsLessonLimit','高相关复盘条数必须为 1–20 的整数。');if(document.getElementById('settingsRiskCopy').value.trim().length<20)fail('settingsRiskCopy','风险提示文案至少需要 20 个字符。');return errors}`,
);
html = html.replaceAll("history-context-limits-v1。", "system-settings-v2.0。");
html = html.replaceAll("`history-context-limits-v1.${settingsVersionPatch}`", "`system-settings-v2.${settingsVersionPatch}`");

const listenersNeedle = `settingsControls.forEach(control=>control.addEventListener('input',markSettingsDirty));`;
const listenersExtra = `${listenersNeedle}
    document.querySelectorAll('[data-settings-save]').forEach(button=>button.addEventListener('click',()=>settingsSaveButton.click()));
    const settingsSearch=document.getElementById('settingsSearch'),settingsSearchStatus=document.getElementById('settingsSearchStatus');
    settingsSearch.addEventListener('input',()=>{const query=settingsSearch.value.trim().toLowerCase();let visible=0;document.querySelectorAll('[data-settings-group]').forEach(panel=>{panel.hidden=Boolean(query)&&!(panel.dataset.settingsGroup+' '+panel.textContent).toLowerCase().includes(query);if(!panel.hidden)visible+=1});settingsSearchStatus.textContent=query?\`\${visible} 个匹配分组\`:'5 个分组'});
    document.querySelectorAll('.settings-index a').forEach(link=>link.addEventListener('click',()=>{document.querySelectorAll('.settings-index a').forEach(item=>item.classList.toggle('active',item===link))}));`;
if (!html.includes(listenersNeedle)) throw new Error("settings listeners not found");
html = html.replace(listenersNeedle, listenersExtra);

fs.writeFileSync(file, html);
console.log("Enhanced PRD 15.6 settings surface");
