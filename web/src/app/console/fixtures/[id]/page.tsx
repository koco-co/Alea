import Link from "next/link";

export default async function FixtureDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="console-main detail-page fixture-detail-page">
      <Link className="button secondary back-link" href="/console/fixtures">
        返回赛程列表
      </Link>
      <header className="detail-heading">
        <div>
          <p className="eyebrow">竞彩场次 · {id}</p>
          <h1>等待真实 Offer 场次</h1>
          <p>
            只有真实销售
            Offer、赔率快照和销售窗口通过资格校验后才会展示比赛详情。
          </p>
        </div>
        <span className="status-chip warning">未加载</span>
      </header>
      <section className="wide-empty-state">
        <strong>暂无可核验的真实竞彩场次</strong>
        <p>页面不会生成球队、时间、场地、赔率或赛果。</p>
      </section>
    </main>
  );
}
