export function DailyBrief() {
  return (
    <section aria-labelledby="brief-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">今日研究简报</p>
          <h2 id="brief-title">今天，从四个数字开始</h2>
        </div>
        <p className="muted">指标由真实同步与公证投影返回</p>
      </div>
      <div className="metric-grid">
        {[
          ["在售场次", "/console/fixtures"],
          ["已入圆桌", "/console/predictions"],
          ["已发布", "/console/predictions"],
          ["待停售", "/console/fixtures"],
        ].map(([label, href]) => (
          <a className="metric-card" href={href} key={label}>
            <span>{label}</span>
            <strong>—</strong>
            <small>等待真实数据投影 →</small>
          </a>
        ))}
      </div>
    </section>
  );
}
