import Link from "next/link";

const metrics = [
  {
    label: "在售场次",
    value: "18",
    note: "今日竞彩",
    href: "/console/fixtures?status=on_sale",
  },
  {
    label: "已入圆桌",
    value: "6",
    note: "研究进行中",
    href: "/console/predictions?status=roundtable",
  },
  {
    label: "已发布",
    value: "3",
    note: "可查看推演",
    href: "/console/predictions?status=published",
  },
  {
    label: "待停售",
    value: "4",
    note: "未来 2 小时",
    href: "/console/fixtures?cutoff=soon",
  },
] as const;

export function DailyBrief() {
  return (
    <section aria-labelledby="brief-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">今日研究简报</p>
          <h2 id="brief-title">今天，从四个数字开始</h2>
        </div>
        <p className="muted">最近成功同步 · 18 分钟前</p>
      </div>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <Link className="metric-card" href={metric.href} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.note} →</small>
          </Link>
        ))}
      </div>
    </section>
  );
}
