import { NetValueChart } from "@/components/charts/net-value-chart";

const accounts = [
  ["圆桌共识", "10,688", "+6.88%", "-1.04%", "28", "17"],
  ["深策 · DeepSeek", "10,408", "+4.08%", "-0.62%", "26", "15"],
  ["远见 · OpenAI", "10,374", "+3.74%", "-0.54%", "27", "16"],
  ["慎思 · Anthropic", "10,318", "+3.18%", "-0.48%", "25", "14"],
];

export default function PnlPage() {
  return (
    <main className="console-main research-page pnl-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">盈亏账本 · 模拟账户</p>
          <h1>每一条净值，都能回到那次终投。</h1>
          <p>
            圆桌共识账户置顶；每个 AI
            账户只结算自己的最终方案，零仓位决策不计投入场次。
          </p>
        </div>
        <span className="status-chip">账本已公证</span>
      </div>
      <nav className="page-tabs" aria-label="账本类型">
        <a className="active" href="#simulation">
          模拟账户
        </a>
        <a href="#summary">账户汇总</a>
      </nav>
      <section className="consensus-overview" id="simulation">
        <div>
          <span>圆桌共识账户</span>
          <strong>10,688</strong>
          <small>当前净值</small>
        </div>
        <div>
          <span>总收益率</span>
          <strong className="positive-copy">+6.88%</strong>
          <small>起始资金 10,000</small>
        </div>
        <div>
          <span>最大回撤</span>
          <strong>-1.04%</strong>
          <small>近 30 天</small>
        </div>
        <div>
          <span>已执行方案</span>
          <strong>28</strong>
          <small>17 次命中</small>
        </div>
      </section>
      <NetValueChart />
      <section className="data-table-card" id="summary">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">账户汇总</p>
            <h2>模型操盘表现</h2>
          </div>
          <span className="status-chip">截至 07-20 00:00</span>
        </div>
        <div className="data-table" role="table" aria-label="模拟账户汇总">
          <div className="data-table-row data-table-head" role="row">
            <span>AI / 账户</span>
            <span>当前净值</span>
            <span>总收益率</span>
            <span>最大回撤</span>
            <span>投入场次</span>
            <span>命中场次</span>
          </div>
          {accounts.map((account, index) => (
            <div className="data-table-row" role="row" key={account[0]}>
              <strong>
                {account[0]}
                {index === 0 ? <small> 平台最终方案</small> : null}
              </strong>
              <span className="mono-value">{account[1]}</span>
              <span className="positive-copy">{account[2]}</span>
              <span>{account[3]}</span>
              <span>{account[4]}</span>
              <span>{account[5]}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
