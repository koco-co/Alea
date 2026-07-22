import Link from "next/link";

export interface MatchRowProps {
  id: string;
  competition: string;
  round: string;
  kickoff: string;
  home: string;
  away: string;
  homeFlag: string;
  awayFlag: string;
  prediction?: string;
  status?: string;
}

export function MatchRow({
  id,
  competition,
  round,
  kickoff,
  home,
  away,
  homeFlag,
  awayFlag,
  prediction,
  status = "赛前 · 赛果待定",
}: MatchRowProps) {
  return (
    <Link className="fixture-row" href={`/console/fixtures/${id}`}>
      <div className="fixture-id">
        <strong>Match {id}</strong>
        <span>{kickoff} 北京</span>
      </div>
      <div className="fixture-matchup">
        <div>
          <img src={homeFlag} alt={`${home}国旗`} />
          <strong>{home}</strong>
        </div>
        <span>vs</span>
        <div>
          <strong>{away}</strong>
          <img src={awayFlag} alt={`${away}国旗`} />
        </div>
        <small>
          {competition} · {round}
        </small>
      </div>
      <div className="fixture-prediction">
        <span>AI 预测结果 · 仅展示已发布记录</span>
        <strong>{prediction ?? "暂无发布的预测"}</strong>
        {prediction ? <small>来自已公证圆桌</small> : null}
      </div>
      <div className="fixture-state">
        <span className="status-chip warning">{status}</span>
        <small>来源未连接</small>
        <b>查看比赛详情</b>
      </div>
    </Link>
  );
}
