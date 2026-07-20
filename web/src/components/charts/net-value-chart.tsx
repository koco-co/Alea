"use client";

import { useMemo, useState } from "react";

type Range = "7d" | "30d" | "all";

const accounts = [
  {
    id: "consensus",
    name: "圆桌共识",
    color: "#cc785c",
    values: [
      10000, 10048, 10031, 10116, 10204, 10182, 10276, 10340, 10318, 10442,
      10528, 10502, 10614, 10688,
    ],
  },
  {
    id: "openai",
    name: "远见 · OpenAI",
    color: "#5b7568",
    values: [
      10000, 10022, 9988, 10054, 10112, 10087, 10154, 10196, 10172, 10232,
      10270, 10242, 10308, 10374,
    ],
  },
  {
    id: "anthropic",
    name: "慎思 · Anthropic",
    color: "#b28a4b",
    values: [
      10000, 9974, 10018, 10002, 10066, 10108, 10082, 10148, 10186, 10220,
      10194, 10256, 10292, 10318,
    ],
  },
  {
    id: "deepseek",
    name: "深策 · DeepSeek",
    color: "#647f9b",
    values: [
      10000, 10036, 10072, 10048, 10130, 10104, 10178, 10148, 10214, 10276,
      10242, 10320, 10374, 10408,
    ],
  },
] as const;

const width = 920;
const height = 330;
const padding = { top: 24, right: 28, bottom: 42, left: 64 };

function points(values: readonly number[], min: number, max: number) {
  return values
    .map((value, index) => {
      const x =
        padding.left +
        (index / (values.length - 1)) * (width - padding.left - padding.right);
      const y =
        padding.top +
        ((max - value) / (max - min)) * (height - padding.top - padding.bottom);
      return `${x},${y}`;
    })
    .join(" ");
}

export function NetValueChart() {
  const [range, setRange] = useState<Range>("30d");
  const [visible, setVisible] = useState(accounts.map((account) => account.id));
  const [hover, setHover] = useState<number | null>(null);
  const shown = accounts.filter((account) => visible.includes(account.id));
  const bounds = useMemo(() => {
    const all = shown.flatMap((account) => [...account.values]);
    return {
      min: Math.floor((Math.min(...all, 9900) - 40) / 100) * 100,
      max: Math.ceil((Math.max(...all, 10700) + 40) / 100) * 100,
    };
  }, [shown]);
  const index = hover ?? accounts[0].values.length - 1;
  const hoverX =
    padding.left +
    (index / (accounts[0].values.length - 1)) *
      (width - padding.left - padding.right);

  return (
    <section className="net-chart" aria-label="模拟账户净值走势">
      <div className="chart-toolbar">
        <div>
          <p className="eyebrow">净值走势</p>
          <h2>从 10,000 模拟币开始</h2>
        </div>
        <div className="segmented-control" aria-label="时间范围">
          {(
            [
              ["7d", "7 天"],
              ["30d", "30 天"],
              ["all", "全部"],
            ] as const
          ).map(([value, label]) => (
            <button
              className={range === value ? "active" : ""}
              type="button"
              key={value}
              aria-pressed={range === value}
              onClick={() => setRange(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-legend">
        {accounts.map((account) => (
          <label key={account.id}>
            <input
              type="checkbox"
              checked={visible.includes(account.id)}
              onChange={() =>
                setVisible((items) =>
                  items.includes(account.id)
                    ? items.filter((id) => id !== account.id)
                    : [...items, account.id],
                )
              }
            />
            <span style={{ background: account.color }} />
            <strong>{account.name}</strong>
          </label>
        ))}
      </div>
      <div className="chart-stage">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-labelledby="net-chart-title"
          onMouseLeave={() => setHover(null)}
          onMouseMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * width;
            setHover(
              Math.max(
                0,
                Math.min(
                  accounts[0].values.length - 1,
                  Math.round(
                    ((x - padding.left) /
                      (width - padding.left - padding.right)) *
                      (accounts[0].values.length - 1),
                  ),
                ),
              ),
            );
          }}
        >
          <title id="net-chart-title">
            圆桌共识与三个 AI 实例的模拟账户净值折线图
          </title>
          {[0, 1, 2, 3, 4].map((step) => {
            const y =
              padding.top +
              step * ((height - padding.top - padding.bottom) / 4);
            const value = Math.round(
              bounds.max - step * ((bounds.max - bounds.min) / 4),
            );
            return (
              <g key={step}>
                <line
                  x1={padding.left}
                  x2={width - padding.right}
                  y1={y}
                  y2={y}
                  className="chart-grid-line"
                />
                <text x={padding.left - 12} y={y + 4} textAnchor="end">
                  {value.toLocaleString()}
                </text>
              </g>
            );
          })}
          {shown.map((account) => (
            <polyline
              key={account.id}
              points={points(account.values, bounds.min, bounds.max)}
              fill="none"
              stroke={account.color}
              strokeWidth={account.id === "consensus" ? 4 : 2.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}
          <line
            x1={hoverX}
            x2={hoverX}
            y1={padding.top}
            y2={height - padding.bottom}
            className="chart-crosshair"
          />
          <text x={padding.left} y={height - 13}>
            07-07
          </text>
          <text x={width / 2} y={height - 13} textAnchor="middle">
            07-13
          </text>
          <text x={width - padding.right} y={height - 13} textAnchor="end">
            07-20
          </text>
        </svg>
        <div
          className="chart-tooltip"
          style={{
            left: `${Math.min(76, Math.max(12, (hoverX / width) * 100))}%`,
          }}
        >
          <strong>7 月 {7 + index} 日</strong>
          {shown.map((account) => (
            <span key={account.id}>
              <i style={{ background: account.color }} />
              {account.name}
              <b>{account.values[index].toLocaleString()}</b>
            </span>
          ))}
          <small>当日投入 286 · 回收 364</small>
        </div>
      </div>
      <p className="chart-footnote">
        结算以公证账本为唯一依据；发布或撤回不改变模拟盘统计。
      </p>
    </section>
  );
}
