export default function PnlPage() {
  return (
    <main className="console-main research-page pnl-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">盈亏账本 · 模拟账户</p>
          <h1>每一条净值，都能回到那次终投。</h1>
          <p>账本只读取已公证且已结算的真实结果；没有结算数据时保持空缺。</p>
        </div>
        <span className="status-chip warning">等待真实结算</span>
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
          <strong>—</strong>
          <small>当前净值</small>
        </div>
        <div>
          <span>总收益率</span>
          <strong>—</strong>
          <small>等待版本化账户数据</small>
        </div>
        <div>
          <span>最大回撤</span>
          <strong>—</strong>
          <small>等待真实结算</small>
        </div>
        <div>
          <span>已执行方案</span>
          <strong>—</strong>
          <small>等待真实结算</small>
        </div>
      </section>
      <div className="wide-empty-state">
        <strong>暂无可核验账本曲线</strong>
        <p>平台不会用固定余额、命中率或收益曲线冒充真实结算。</p>
      </div>
      <section className="data-table-card" id="summary">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">账户汇总</p>
            <h2>模型操盘表现</h2>
          </div>
          <span className="status-chip warning">等待真实账本</span>
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
          <div className="wide-empty-state" role="row">
            <strong>暂无已结算账户</strong>
          </div>
        </div>
      </section>
    </main>
  );
}
