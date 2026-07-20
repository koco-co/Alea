import Link from "next/link";

const teams = {
  spain: {
    name: "西班牙",
    region: "UEFA · 国家队",
    flag: "/assets/teams/flag-spain.png",
    rank: "2",
    coach: "资料待同步",
    accuracy: "67%",
    form: ["胜", "胜", "平", "胜", "胜"],
  },
  argentina: {
    name: "阿根廷",
    region: "CONMEBOL · 国家队",
    flag: "/assets/teams/flag-argentina.png",
    rank: "1",
    coach: "资料待同步",
    accuracy: "64%",
    form: ["胜", "平", "胜", "胜", "胜"],
  },
} as const;

export default async function WikiDetailPage({
  params,
}: {
  params: Promise<{ type: string; id: string }>;
}) {
  const { type, id } = await params;
  const team = type === "team" ? teams[id as keyof typeof teams] : undefined;
  if (!team)
    return (
      <main className="console-main detail-page">
        <Link className="button secondary back-link" href="/console/wiki">
          返回赛事资料
        </Link>
        <section className="wiki-source-empty">
          <img src="/assets/icons/user-round.svg" alt="" />
          <p className="eyebrow">资料详情</p>
          <h1>可信资料源尚未接入</h1>
          <p>此实体没有可验证的资料快照，因此不展示虚构字段。</p>
        </section>
      </main>
    );
  return (
    <main className="console-main detail-page wiki-detail-page">
      <Link className="button secondary back-link" href="/console/wiki">
        返回赛事资料
      </Link>
      <header className="wiki-profile-hero">
        <img src={team.flag} alt={`${team.name}国旗`} />
        <div>
          <p className="eyebrow">球队档案 · 2026 FIFA 世界杯</p>
          <h1>{team.name}</h1>
          <p>{team.region} · 身份已核对，阵容与统计来源待接入。</p>
        </div>
        <span className="status-chip">FIFA 排名 {team.rank}</span>
      </header>
      <section className="wiki-profile-metrics">
        <div>
          <span>当前排名</span>
          <strong>#{team.rank}</strong>
          <small>FIFA 排名</small>
        </div>
        <div>
          <span>Alea 历史命中率</span>
          <strong>{team.accuracy}</strong>
          <small>已结算样本 3 场</small>
        </div>
        <div>
          <span>近 5 场</span>
          <strong className="form-text">{team.form.join(" · ")}</strong>
          <small>赛果摘要</small>
        </div>
        <div>
          <span>主教练</span>
          <strong className="pending-copy">{team.coach}</strong>
          <small>不得猜测</small>
        </div>
      </section>
      <div className="wiki-detail-grid">
        <section className="data-table-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">近期与未来赛程</p>
              <h2>已核对赛事</h2>
            </div>
          </div>
          <div className="fixture-archive">
            <div>
              <time>2026-07-20</time>
              <strong>
                {team.name} vs {team.name === "西班牙" ? "阿根廷" : "西班牙"}
              </strong>
              <span className="status-chip warning">赛前</span>
            </div>
            <div>
              <time>资料待同步</time>
              <strong>暂无更多可信赛程</strong>
              <span>—</span>
            </div>
          </div>
        </section>
        <aside className="wiki-side-stack">
          <section>
            <p className="eyebrow">主力阵容</p>
            <h2>球员资料待同步</h2>
            <p>阵容、号码与伤停都必须来自带时间戳的可信快照。</p>
          </section>
          <section>
            <p className="eyebrow">历史预测关联</p>
            <h2>Alea 研究记录</h2>
            <Link href="/console/predictions/n8c4-02">世界杯决赛推演 →</Link>
            <Link href="/console/reviews/review-20260718">相关复盘档案 →</Link>
          </section>
        </aside>
      </div>
    </main>
  );
}
