import Link from "next/link";

export default function AuthLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <main className="auth-shell">
      <aside className="auth-story">
        <Link className="brand" href="/" aria-label="Alea 首页">
          <span>Alea</span>
        </Link>
        <div>
          <p className="eyebrow">竞彩足球研究台</p>
          <h1>让判断有迹可循。</h1>
          <p>多模型圆桌、可核验事实与赛后复盘，服务于研究，不提供购彩服务。</p>
        </div>
        <p className="auth-footnote">理性分析 · 年满 18 周岁 · 风险自担</p>
      </aside>
      <section className="auth-panel">{children}</section>
    </main>
  );
}
