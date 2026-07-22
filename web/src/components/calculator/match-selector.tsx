export type CalculatorMode = "fact" | "sample";

export function MatchSelector() {
  return (
    <section
      className="calculator-panel match-selector-panel"
      aria-labelledby="match-selector-title"
    >
      <div className="calculator-panel-heading">
        <div>
          <span>步骤 1 · 比赛身份</span>
          <h2 id="match-selector-title">等待真实竞彩场次</h2>
        </div>
        <span className="status-chip warning">未加载</span>
      </div>
      <p>
        只展示已经进入体彩竞彩销售 Offer、具备有效赔率快照并通过资格校验的比赛。
      </p>
      <div className="wide-empty-state">
        <strong>当前没有可核验的真实竞彩场次</strong>
        <p>等待授权来源或管理员合法导入后，比赛才可被选择。</p>
      </div>
      <dl className="data-checklist">
        <div>
          <dt>赛事身份</dt>
          <dd className="good-text">FIFA 已确认</dd>
        </div>
        <div>
          <dt>竞彩销售编号</dt>
          <dd>待确认</dd>
        </div>
        <div>
          <dt>固定奖金 / 停售</dt>
          <dd>待确认</dd>
        </div>
      </dl>
    </section>
  );
}
