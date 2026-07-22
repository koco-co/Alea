import Link from "next/link";

import { AdminTodos } from "@/components/console/admin-todos";
import { DailyBrief } from "@/components/console/daily-brief";
import {
  FreshnessIndicator,
  GlobalStatusBanner,
} from "@/components/ui/system-status";
import { getAccessContext } from "@/lib/supabase/access";

export default async function ConsoleOverviewPage() {
  const access = await getAccessContext();
  const isAdmin = access?.role === "admin";
  const now = new Date();
  const syncedAt = now;
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
            <div className="wide-empty-state">
              <strong>暂无可核验的竞彩 Offer</strong>
              <p>页面不会用固定比赛或静态预测填充生产状态。</p>
              <Link className="button secondary" href="/console/fixtures">
                查看真实赛程
              </Link>
            </div>
            {isAdmin ? (
              <div className="admin-inline">
                <span>管理员视图</span>
                <strong>待办数量由真实后端返回</strong>
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
            <span className="status-dot warning">等待真实投影</span>
          </div>
          <dl className="status-list">
            <div>
              <dt>最近阶段</dt>
              <dd>—</dd>
            </div>
            <div>
              <dt>Provider 可用</dt>
              <dd>—</dd>
            </div>
            <div>
              <dt>数据新鲜度</dt>
              <dd>—</dd>
            </div>
            {isAdmin ? (
              <>
                <div>
                  <dt>失败任务</dt>
                  <dd className="warning-text">—</dd>
                </div>
                <div>
                  <dt>赛果冲突</dt>
                  <dd>—</dd>
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
