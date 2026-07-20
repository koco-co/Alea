export interface VoteAgent {
  name: string;
  logo: string;
  instance?: number;
  score: number;
  reason: string;
}

export function VoteBar({
  score,
  agents,
  total = 7,
}: {
  score: string;
  agents: VoteAgent[];
  total?: number;
}) {
  const width = Math.max(8, Math.round((agents.length / total) * 100));
  return (
    <div className="vote-row">
      <strong>{score}</strong>
      <div className="vote-agents" aria-label={`${agents.length} 个 AI 投票`}>
        {agents.map((agent) => (
          <button
            className={
              agent.score >= 85 ? "vote-agent high-score" : "vote-agent"
            }
            key={agent.name}
            type="button"
            aria-label={`${agent.name}，综合准确分 ${agent.score}，理由：${agent.reason}`}
            title={`${agent.name} · ${agent.score} 分 · ${agent.reason}`}
          >
            <img src={agent.logo} alt="" />
            {agent.instance ? <span>{agent.instance}</span> : null}
          </button>
        ))}
      </div>
      <div className="vote-progress" aria-hidden="true">
        <span style={{ width: `${width}%` }} />
      </div>
      <b>{agents.length} 票</b>
    </div>
  );
}
