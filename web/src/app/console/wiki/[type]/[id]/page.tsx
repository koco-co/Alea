import Link from "next/link";

export default async function WikiDetailPage({
  params,
}: {
  params: Promise<{ type: string; id: string }>;
}) {
  const { type, id } = await params;
  return (
    <main className="console-main detail-page">
      <Link className="button secondary back-link" href="/console/wiki">
        返回赛事资料
      </Link>
      <section className="wiki-source-empty">
        <img src="/assets/icons/user-round.svg" alt="" />
        <p className="eyebrow">
          资料详情 · {type}/{id}
        </p>
        <h1>可信资料源尚未接入</h1>
        <p>
          当前没有已授权、带时间戳且完成实体映射的资料快照，因此不展示球队、赛果、
          排名或历史命中率示例。
        </p>
      </section>
    </main>
  );
}
