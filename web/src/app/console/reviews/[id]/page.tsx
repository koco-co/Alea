import Link from "next/link";

export default async function ReviewDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="console-main detail-page review-detail-page">
      <Link className="button secondary back-link" href="/console/reviews">
        返回复盘记录
      </Link>
      <header className="detail-heading">
        <div>
          <p className="eyebrow">复盘详情 · {id.toUpperCase()}</p>
          <h1>等待真实复盘记录</h1>
          <p>页面不会用固定比赛、比分、AI 判断或教训冒充已发布复盘。</p>
        </div>
        <span className="status-chip warning">未加载</span>
      </header>
      <section className="wide-empty-state">
        <strong>暂无可核验的复盘详情</strong>
        <p>只有真实赛果同步、复盘生成和审核发布完成后，详情才会显示。</p>
      </section>
    </main>
  );
}
