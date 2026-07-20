import fs from "node:fs";
import path from "node:path";

const htmlFiles = [
  "index.html",
  "alea.html",
  "alea-auth.html",
  "alea-console.html",
  "alea-predictions.html",
  "alea-calculator.html",
  "alea-admin.html",
  "alea-design-system.html"
];

const failures = [];
const passes = [];

function check(condition, label, detail = "") {
  if (condition) passes.push(label);
  else failures.push(`${label}${detail ? `：${detail}` : ""}`);
}

for (const file of htmlFiles) {
  const html = fs.readFileSync(file, "utf8");
  const markupOnly = html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/g, "")
    .replace(/<script[^>]*>[\s\S]*?<\/script>/g, "");
  const ids = [...markupOnly.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
  const odIds = [...markupOnly.matchAll(/\bdata-od-id="([^"]+)"/g)].map((match) => match[1]);
  const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
  const duplicateOdIds = odIds.filter((id, index) => odIds.indexOf(id) !== index);
  check(duplicateIds.length === 0, `${file} 无重复 id`, [...new Set(duplicateIds)].join(", "));
  check(duplicateOdIds.length === 0, `${file} 无重复 data-od-id`, [...new Set(duplicateOdIds)].join(", "));
  check(!html.includes("scrollIntoView("), `${file} 不使用 scrollIntoView`);
  check(!/\[REPLACE\]|Lorem ipsum/i.test(html), `${file} 无模板占位`);
  check(!/(澜城|赤湾|北境|海岬|松桥|山谷联|南岸城|森林竞技|海湾超级|北方冠军)/.test(html), `${file} 无旧版虚构赛事`);
  check(!/(西班牙|阿根廷)[^<\n]{0,80}已命中/.test(html), `${file} 未提前宣告决赛命中`);
  check(!/(最终赛果)[^<\n]{0,40}2\s*:\s*1/.test(html), `${file} 未把 AI 比分写成赛果`);

  const resources = [...markupOnly.matchAll(/\b(?:src|href)="([^"]+)"/g)]
    .map((match) => match[1])
    .filter((value) => !value.startsWith("#") && !value.startsWith("http") && !value.startsWith("mailto:") && !value.startsWith("javascript:"))
    .map((value) => value.split(/[?#]/)[0])
    .filter((value) => value && !value.endsWith(".md"));
  const missing = resources.filter((resource) => !fs.existsSync(path.resolve(path.dirname(file), resource)));
  check(missing.length === 0, `${file} 本地资源完整`, [...new Set(missing)].join(", "));

  const scripts = [...html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
  let syntaxError = "";
  for (const code of scripts) {
    try {
      new Function(code);
    } catch (error) {
      syntaxError = error.message;
      break;
    }
  }
  check(!syntaxError, `${file} 内联脚本语法有效`, syntaxError);
}

const css = fs.readFileSync("alea.css", "utf8");
check(css.includes("@media(max-width:1000px)") && css.includes("@media(max-width:760px)"), "响应式断点存在");
check(css.includes("prefers-reduced-motion:reduce"), "减少动态效果降级存在");
check(css.includes(".btn{min-height:44px"), "主要按钮满足 44px 触控尺寸");

const frozenFiles = ["alea.html", "alea-console.html", "alea-predictions.html", "alea-calculator.html", "alea-admin.html"];
const frozenSource = frozenFiles.map((file) => fs.readFileSync(file, "utf8")).join("\n");
const consoleSource = fs.readFileSync("alea-console.html", "utf8");
const calculatorSource = fs.readFileSync("alea-calculator.html", "utf8");
const adminSource = fs.readFileSync("alea-admin.html", "utf8");
const predictionsSource = fs.readFileSync("alea-predictions.html", "utf8");
check(!/4\s*\/\s*6/.test(frozenSource), "PRD v1.9 冻结票数不存在 4/6 残留");
check((frozenSource.match(/5\s*\/\s*7/g) || []).length >= 8, "PRD v1.9 固定票数 5/7 跨页面一致");
check(
  !/Qwen-1 已停用|Qwen-1 已排除|停用的 Qwen-1|6\s*个已启用/.test(frozenSource)
    && /7\s*个配置实例\s*·\s*7\s*个已启用/.test(adminSource),
  "Qwen-1 冻结阵容状态跨页面一致"
);
check(!/2026-07-17[\s\S]{0,180}(西班牙 vs 阿根廷|实际[^<]{0,30}1\s*:\s*2)/.test(consoleSource), "未提前伪造世界杯决赛历史赛果");
check(/addEventListener\('hashchange',applyCalculatorHash\)/.test(calculatorSource), "计算器支持 #sample 深链与 hashchange");
check(/id="fillLoginDemo"[^>]*hidden/.test(fs.readFileSync("alea-auth.html", "utf8")) && /id="fillSignupDemo"[^>]*hidden/.test(fs.readFileSync("alea-auth.html", "utf8")), "认证演示填充工具不暴露在产品界面");
check((fs.readFileSync("alea-predictions.html", "utf8").match(/<strong>Qwen-1<\/strong><small>选手 E<\/small>/g) || []).length === 1, "预测最终立场仅包含一个 Qwen-1");
check((fs.readFileSync("alea-admin.html", "utf8").match(/<strong>Qwen-1<\/strong><small>原型实例 E<\/small>/g) || []).length === 1, "管理直播参与列表仅包含一个 Qwen-1");
check(!/lineup-provider-list\{display:flex;max-width:100%;overflow-x:auto/.test(fs.readFileSync("alea-admin.html", "utf8")), "移动端厂商目录为单栏且无横向裁切");
check(!/methodVersion[^\\n]{0,220}core-methodology-v1\\.2/.test(fs.readFileSync("alea-admin.html", "utf8")), "方法论演示发布不会改动生产版本");
check(!/crest-beijing|crest-haijia|积分 37|积分 24/.test(fs.readFileSync("alea-console.html", "utf8")), "赛事资料不使用虚构积分与战绩");
check(/href="alea-predictions\.html#today">太玄问机<\/a><a href="alea-calculator\.html">竞彩方案/.test(fs.readFileSync("alea-console.html", "utf8")), "移动端底栏指向独立预测与方案页");

check(/isAdminPrototype=new URLSearchParams\(location\.search\)\.get\('role'\)==='admin'/.test(fs.readFileSync("alea-console.html", "utf8")), "管理员真实盘入口按角色隔离");
check(/wiki-team-spain/.test(fs.readFileSync("alea-console.html", "utf8")) && /wiki-team-argentina/.test(fs.readFileSync("alea-console.html", "utf8")), "赛事资料身份详情支持双队深链");
check(/id="messages"[\s\S]*id="account"/.test(consoleSource) && /messages:'消息中心'/.test(consoleSource) && /account:'账户设置'/.test(consoleSource), "消息与账户路由支持冷启动");
check(/data-message-filter="all"/.test(consoleSource) && /data-message-filter="unread"/.test(consoleSource) && /data-message-read/.test(consoleSource) && /id="messageMarkAllRead"/.test(consoleSource), "消息中心具备筛选与单条全部已读操作");
check(/id="messageEmpty"/.test(consoleSource) && /href="#account" data-view="account">通知偏好/.test(consoleSource), "消息中心具备空状态与通知偏好入口");
check(/id="messageEmpty"[\s\S]*lucide-bell\.svg/.test(consoleSource) && /id="followedEmpty"[\s\S]*lucide-star\.svg/.test(consoleSource), "消息与关注空状态使用语义匹配图标");
check(["default", "uploaded-success", "load-failure", "no-avatar"].every((state) => consoleSource.includes(`data-avatar-state="${state}"`)), "账户页包含四种命名头像状态");
check(/id="avatarUpload"/.test(consoleSource) && /id="removeAvatar"/.test(consoleSource) && /id="restoreAvatar"/.test(consoleSource) && /id="simulateAvatarFailure"/.test(consoleSource), "头像上传移除恢复与故障模拟入口完整");
check(/id="passwordForm"/.test(consoleSource) && /data-oauth="GitHub"/.test(consoleSource) && /data-oauth="Google"/.test(consoleSource) && /id="deleteAccountDialog"/.test(consoleSource), "密码 OAuth 与删除确认流程完整");
check(/原型本地/.test(consoleSource) && /未请求服务器/.test(consoleSource), "账户效果明确标注为原型本地且非服务器成功");
check(!/官方原型头像/.test(consoleSource) && /使用默认原型头像/.test(consoleSource), "虚构账户头像不冒充官方资产");
check((consoleSource.match(/assets\/accounts\/lin-zhou\.png/g) || []).length >= 3 && (predictionsSource.match(/assets\/accounts\/lin-zhou\.png/g) || []).length >= 2, "用户头像统一使用林舟本地图片");
check((adminSource.match(/assets\/accounts\/admin\.png/g) || []).length >= 2, "管理员头像统一使用管理员本地图片");
check([consoleSource, predictionsSource, adminSource].every((source) => source.includes("assets/icons/lucide-user-round.svg")), "头像加载失败使用统一本地图标");
check(!/(?:avatar-button|account-summary)[^>]*>\s*(?:林|管)\s*</.test([consoleSource, predictionsSource, adminSource].join("\n")), "头部与账户摘要不使用文字首字头像");
check(/alea-console\.html#messages/.test(predictionsSource) && /alea-console\.html#account/.test(predictionsSource) && /alea-console\.html\?role=admin#messages/.test(adminSource) && /alea-console\.html\?role=admin#account/.test(adminSource), "预测与管理入口连接完整消息账户路由并保留角色");
check(/deleteDialog\.addEventListener\('keydown'/.test(consoleSource) && /event\.key==='Escape'/.test(consoleSource) && /deleteReturnFocus/.test(consoleSource), "账户删除对话框支持 Escape 与焦点返回");
check(
  /\.phase-tabs button\{min-height:44px/.test(css)
    && /#fixtures \.fx-filter-tabs button\{min-height:44px/.test(consoleSource)
    && /#fixtures \.fx-detail-tabs button\{min-width:0;min-height:44px/.test(consoleSource)
    && /\.vote-avatar\{width:44px;height:44px/.test(predictionsSource)
    && /\.fixture-row \.follow-button\{[^}]*height:44px/.test(predictionsSource)
    && /\.lineup-model-option\{min-height:44px/.test(adminSource),
  "阶段、赛事、投票、关注与阵容控件满足 44px 触控尺寸"
);
check(/<span class="num">106<\/span> 项通过 · <span class="num">0<\/span> 项失败/.test(fs.readFileSync("index.html", "utf8")), "启动器展示当前自动检查总数");

console.log(`PASS ${passes.length}`);
for (const pass of passes) console.log(`✓ ${pass}`);
if (failures.length) {
  console.log(`FAIL ${failures.length}`);
  for (const failure of failures) console.log(`✗ ${failure}`);
  process.exitCode = 1;
} else {
  console.log("FAIL 0");
}
