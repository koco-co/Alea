import Link from "next/link";

import { FixtureDetailTabs } from "@/components/fixtures/fixture-detail-tabs";

export default async function FixtureDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="console-main detail-page fixture-detail-page">
      <Link className="button secondary back-link" href="/console/fixtures">返回赛程列表</Link>
      <section className="fixture-hero">
        <div className="fixture-hero-title"><p>2026 FIFA 世界杯 · MATCH {id}</p><h1>西班牙 vs 阿根廷</h1></div>
        <span className="status-chip warning">赛前 · 赛果待定</span>
        <div className="team-side"><img src="/assets/teams/flag-spain.png" alt="西班牙国旗" /><strong>西班牙</strong><span>国家队</span></div>
        <div className="fixture-kickoff"><strong>VS</strong><span>比赛尚未开始</span><small>赛事详情官方确认</small></div>
        <div className="team-side"><img src="/assets/teams/flag-argentina.png" alt="阿根廷国旗" /><strong>阿根廷</strong><span>国家队</span></div>
        <div className="fixture-meta"><div><span>纽约时间</span><strong>2026-07-19 15:00 ET</strong></div><div><span>北京时间</span><strong>2026-07-20 03:00</strong></div><div><span>比赛场地</span><strong>New York New Jersey Stadium</strong></div></div>
      </section>
      <FixtureDetailTabs />
    </main>
  );
}
