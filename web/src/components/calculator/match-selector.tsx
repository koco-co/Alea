export type CalculatorMode = "fact" | "sample";

export function MatchSelector({
  mode,
  selected,
  onToggle,
}: {
  mode: CalculatorMode;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <section
      className="calculator-panel match-selector-panel"
      aria-labelledby="match-selector-title"
    >
      <div className="calculator-panel-heading">
        <div>
          <span>步骤 1 · 比赛身份</span>
          <h2 id="match-selector-title">2026 FIFA 世界杯决赛</h2>
        </div>
        <span className="status-chip">第 104 场</span>
      </div>
      <p>
        当前原型唯一用于贯穿体验的比赛；没有添加虚构联赛或第二场未关联比赛。
      </p>
      <button
        className={
          selected ? "calculator-match-card selected" : "calculator-match-card"
        }
        onClick={onToggle}
        type="button"
        aria-pressed={selected}
      >
        <span className="match-check" aria-hidden="true">
          {selected ? "已选" : "选择"}
        </span>
        <div>
          <img src="/assets/teams/flag-spain.png" alt="西班牙国旗" />
          <img src="/assets/teams/flag-argentina.png" alt="阿根廷国旗" />
        </div>
        <strong>西班牙 vs 阿根廷</strong>
        <span>北京时间 2026-07-20 03:00</span>
        <small>New York New Jersey Stadium</small>
        <b>固定 AI 推演：2 : 1 · 半场 1 : 0</b>
      </button>
      <dl className="data-checklist">
        <div>
          <dt>赛事身份</dt>
          <dd className="good-text">FIFA 已确认</dd>
        </div>
        <div>
          <dt>竞彩销售编号</dt>
          <dd>{mode === "sample" ? "非官方交互样例" : "待确认"}</dd>
        </div>
        <div>
          <dt>固定奖金 / 停售</dt>
          <dd>{mode === "sample" ? "非体彩 SP" : "待确认"}</dd>
        </div>
      </dl>
    </section>
  );
}
