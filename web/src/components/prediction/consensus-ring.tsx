export function ConsensusRing({ value, votes = "5 / 7" }: { value: number; votes?: string }) {
  return (
    <div className="consensus-ring-wrap">
      <div
        className="consensus-ring"
        role="progressbar"
        aria-label="加权共识"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      >
        <strong>{value}%</strong>
        <span>加权共识</span>
      </div>
      <small>原始票 {votes}</small>
    </div>
  );
}
