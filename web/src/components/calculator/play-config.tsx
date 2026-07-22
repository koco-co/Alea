"use client";

import type { CalculatorMode } from "./match-selector";

const plays = ["胜平负", "让球胜平负", "比分", "总进球", "半全场"] as const;

export function PlayConfig({
  mode,
  selected,
  play,
  onPlayChange,
  multiplier,
  onMultiplierChange,
}: {
  mode: CalculatorMode;
  selected: boolean;
  play: string;
  onPlayChange: (play: string) => void;
  multiplier: number;
  onMultiplierChange: (value: number) => void;
}) {
  const disabled = mode === "fact" || !selected;
  return (
    <section
      className="calculator-panel play-config-panel"
      aria-labelledby="play-config-title"
    >
      <div className="calculator-panel-heading">
        <div>
          <span>步骤 2 · 配置玩法</span>
          <h2 id="play-config-title">玩法与倍数</h2>
        </div>
        <span className={`status-chip ${disabled ? "warning" : ""}`}>
          {disabled ? "当前不可配置" : "交互样例"}
        </span>
      </div>
      <div className="play-tabs" role="tablist" aria-label="玩法选择">
        {plays.map((item) => (
          <button
            className={play === item ? "active" : ""}
            disabled={disabled}
            key={item}
            onClick={() => onPlayChange(item)}
            role="tab"
            type="button"
            aria-selected={play === item}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="play-options">
        {disabled ? (
          <div className="config-empty">
            <strong>等待竞彩销售数据</strong>
            <p>
              数据接入并核验销售状态与规则版本前，不生成玩法、赔率、注数或金额。
            </p>
          </div>
        ) : (
          <>
            <p>交互样例 · 非体彩 SP</p>
            <div className="option-grid">
              {["主队胜 · 待确认", "平 · 待确认", "客队胜 · 待确认"].map(
                (option, index) => (
                  <button
                    className={index === 0 ? "selected" : ""}
                    key={option}
                    type="button"
                  >
                    {option}
                  </button>
                ),
              )}
            </div>
            <div className="pass-config">
              <label>
                <span>过关方式</span>
                <select defaultValue="1x1">
                  <option value="1x1">单关 · 交互样例</option>
                </select>
              </label>
              <div className="multiplier">
                <span>倍数</span>
                <button
                  onClick={() =>
                    onMultiplierChange(Math.max(1, multiplier - 1))
                  }
                  type="button"
                  aria-label="减少倍数"
                >
                  −
                </button>
                <strong>{multiplier}</strong>
                <button
                  onClick={() =>
                    onMultiplierChange(Math.min(50, multiplier + 1))
                  }
                  type="button"
                  aria-label="增加倍数"
                >
                  +
                </button>
              </div>
            </div>
            <p className="config-note">
              切换同场玩法会清除原选择；当前规则不允许同场跨玩法混合过关。
            </p>
          </>
        )}
      </div>
    </section>
  );
}
