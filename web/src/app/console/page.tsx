import Link from "next/link";

import { AdminTodos } from "@/components/console/admin-todos";
import { DailyBrief } from "@/components/console/daily-brief";
import {
  FreshnessIndicator,
  GlobalStatusBanner,
} from "@/components/ui/system-status";
import { getAccessContext } from "@/lib/supabase/access";

const focusMatches = [
  {
    competition: "2026 世界杯 · 决赛",
    time: "07-20 03:00",
    teams: "西班牙  vs  阿根廷",
    status: "已发布推演",
    tone: "positive",
  },
  {
    competition: "挪威超级联赛",
    time: "今日 23:00",
    teams: "罗森博格  vs  布兰",
    status: "距停售 02:18",
    tone: "warning",
  },
  {
    competition: "瑞典超级联赛",
    time: "明日 01:00",
    teams: "马尔默  vs  天狼星",
    status: "资料待补全",
    tone: "neutral",
  },
] as const;

export default async function ConsoleOverviewPage() {
  const access = await getAccessContext();
  const isAdmin = access?.role === "admin";
  const now = new Date();
  const syncedAt = new Date(now.getTime() - 18 * 60_000);
  return (
    <main className="console-main">
      <GlobalStatusBanner status="data_source_partial" />
      <div className="page-heading">
        <div>
          <p className="eyebrow">每日总览</p>
          <h1>早上好，今天研究什么？</h1>
          <p>用一屏掌握赛程、圆桌和需要处理的事项。</p>
        </div>
        <FreshnessIndicator syncedAt={syncedAt} now={now} isAdmin={isAdmin} />
      </div>
      <DailyBrief />
      <div className="dashboard-grid">
        <section className="panel focus-panel" aria-labelledby="focus-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">今日焦点</p>
              <h2 id="focus-title">距离停售最近</h2>
            </div>
            <Link href="/console/fixtures">全部赛程</Link>
          </div>
          <div className="match-list">
            {focusMatches.map((match, index) => (
              <Link
                className="match-row"
                href={
                  index === 0 ? "/console/predictions" : "/console/fixtures"
                }
                key={match.teams}
              >
                <div>
                  <small>{match.competition}</small>
                  <strong>{match.teams}</strong>
                  <span>{match.time}</span>
                </div>
                <span className={`status-dot ${match.tone}`}>
                  {match.status}
                </span>
              </Link>
            ))}
            {isAdmin ? (
              <div className="admin-inline">
                <span>管理员视图</span>
                <strong>1 场推演中 · 2 份待审核</strong>
                <Link href="/console/admin/publish">进入审核</Link>
              </div>
            ) : null}
          </div>
        </section>
        <section
          className="panel status-panel"
          aria-labelledby="roundtable-title"
        >
          <div className="panel-heading">
            <div>
              <p className="eyebrow">圆桌与数据</p>
              <h2 id="roundtable-title">运行状态</h2>
            </div>
            <span className="status-dot positive">运行中</span>
          </div>
          <dl className="status-list">
            <div>
              <dt>最近阶段</dt>
              <dd>比分终投完成</dd>
            </div>
            <div>
              <dt>Provider 可用</dt>
              <dd>8 / 9</dd>
            </div>
            <div>
              <dt>数据新鲜度</dt>
              <dd>18 分钟</dd>
            </div>
            {isAdmin ? (
              <>
                <div>
                  <dt>失败任务</dt>
                  <dd className="warning-text">1</dd>
                </div>
                <div>
                  <dt>赛果冲突</dt>
                  <dd>1</dd>
                </div>
              </>
            ) : null}
          </dl>
          <Link className="text-link" href="/console/predictions">
            查看圆桌记录 →
          </Link>
        </section>
        <section
          className="panel following-panel"
          aria-labelledby="following-title"
        >
          <div className="panel-heading">
            <div>
              <p className="eyebrow">我的关注</p>
              <h2 id="following-title">还没有关注</h2>
            </div>
          </div>
          <div className="empty-state">
            <p>关注比赛或推演卡片后，最新状态会集中显示在这里。</p>
            <Link className="button secondary" href="/console/fixtures">
              去竞猜赛程
            </Link>
          </div>
        </section>
        {isAdmin ? <AdminTodos /> : null}
      </div>
    </main>
  );
}
