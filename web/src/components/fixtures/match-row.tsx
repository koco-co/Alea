import Link from "next/link";

export interface MatchRowProps {
  id: string;
  matchNumber?: string | null;
  competition: string;
  round: string;
  kickoff: string;
  home: string;
  away: string;
  homeFlag?: string;
  awayFlag?: string;
  prediction?: string;
  status?: string;
  sourceLabel?: string;
}

export function MatchRow({
  id,
  matchNumber,
  competition,
  round,
  kickoff,
  home,
  away,
  homeFlag,
  awayFlag,
  prediction,
  status = "赛前 · 赛果待定",
  sourceLabel = "来源未连接",
}: MatchRowProps) {
  return (
    <Link className="fixture-row" href={`/console/fixtures/${id}`}>
      <div className="fixture-id">
        <strong>场次 {matchNumber ?? id}</strong>
        <span>{kickoff} 北京</span>
      </div>
      <div className="fixture-matchup">
        <div>
          {homeFlag ? <img src={homeFlag} alt={`${home}国旗`} /> : null}
          <strong>{home}</strong>
        </div>
        <span>vs</span>
        <div>
          <strong>{away}</strong>
          {awayFlag ? <img src={awayFlag} alt={`${away}国旗`} /> : null}
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
        <small>{sourceLabel}</small>
        <b>查看比赛详情</b>
      </div>
    </Link>
  );
}
