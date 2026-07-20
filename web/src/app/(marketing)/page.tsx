import Link from "next/link";

import { FeatureSection } from "@/components/marketing/feature-section";
import { HeroAnimation } from "@/components/marketing/hero-animation";

const footerGroups = [
  ["产品", ["圆桌辩论", "可验战绩", "竞彩方案"]],
  ["资源", ["赛事资料", "方法说明", "风险提示"]],
  ["关于", ["产品原则", "隐私政策", "服务条款"]],
] as const;

export default function MarketingHomePage() {
  return (
    <main className="marketing-page">
      <header className="marketing-nav">
        <Link className="marketing-brand" href="/" aria-label="Alea 首页">
          <img src="/assets/brand/alea-lockup.png" alt="Alea" />
        </Link>
        <nav aria-label="营销导航">
          <a href="#product">产品</a>
          <a href="#proof">盈亏样例</a>
          <Link href="/login">登录</Link>
          <Link className="marketing-nav-cta" href="/signup">免费注册</Link>
        </nav>
      </header>

      <section className="marketing-hero" aria-labelledby="marketing-title">
        <div className="hero-copy">
          <p className="eyebrow">多 AI 圆桌 · 可追溯研究演示</p>
          <h1 id="marketing-title">让七个 AI，<br />为你吵一场球。</h1>
          <p className="hero-lead">
            多模型独立预测、匿名圆桌辩论、公开改票与投票收敛。每一次判断，都留在可复盘的证据链上。
          </p>
          <div className="hero-actions">
            <Link className="button primary marketing-primary" href="/signup">免费注册</Link>
            <a className="button secondary" href="#product">看看它们怎么吵</a>
          </div>
          <p className="hero-note">演示数据 · 西班牙 vs 阿根廷 · 最终赛果待确认</p>
        </div>
        <HeroAnimation />
      </section>

      <FeatureSection />

      <section className="marketing-cta" aria-labelledby="marketing-cta-title">
        <p className="eyebrow">把结论变成证据</p>
        <h2 id="marketing-cta-title">看完整的推演，而不只看一个比分。</h2>
        <p>注册后可查看圆桌回放、公证摘要与模型立场变化。</p>
        <Link className="button marketing-inverse" href="/signup">开始研究</Link>
      </section>

      <footer className="marketing-footer">
        <div className="footer-main">
          <div>
            <img src="/assets/brand/alea-lockup.png" alt="Alea" />
            <p>竞彩足球 AI 分析研究平台</p>
          </div>
          {footerGroups.map(([title, links]) => (
            <div className="footer-group" key={title}>
              <strong>{title}</strong>
              {links.map((label) => <a href="#product" key={label}>{label}</a>)}
            </div>
          ))}
        </div>
        <div className="risk-copy">
          本平台仅提供 AI 分析研究，不构成投注建议；不提供任何购彩服务；未满 18 周岁禁止购彩；理性购彩。
        </div>
        <div className="footer-bottom"><span>© 2026 Alea</span><span>备案信息占位</span></div>
      </footer>
    </main>
  );
}
