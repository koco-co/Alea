"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

export function ConsentForm() {
  const router = useRouter();
  const [age, setAge] = useState(false);
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function accept() {
    if (!age || !terms) return;
    setBusy(true);
    setError(null);
    const { error: consentError } = await createClient().rpc("record_current_user_consent", {
      p_age_confirmed: true,
      p_terms_accepted: true,
      p_terms_version: "terms-v1",
      p_privacy_version: "privacy-v1",
      p_risk_version: "risk-v1",
    });
    if (consentError) {
      setError("同意记录保存失败，请稍后再试。");
      setBusy(false);
      return;
    }
    router.replace("/console/predictions");
    router.refresh();
  }

  async function reject() {
    setBusy(true);
    setError(null);
    const supabase = createClient();
    const { error: rejectError } = await supabase.rpc("reject_current_user_consent");
    await supabase.auth.signOut();
    if (rejectError) {
      setError("账户清理未完成，请联系支持人员。");
      setBusy(false);
      return;
    }
    router.replace("/signup");
    router.refresh();
  }

  return (
    <div className="auth-card">
      <p className="eyebrow">使用前确认</p>
      <h2>完成风险与年龄确认</h2>
      <p className="muted">第三方登录不会代替你的明确同意。完成确认后才能进入控制台。</p>
      <div className="consent-copy">
        <strong>Alea 仅提供分析研究，不提供购彩服务。</strong>
        <p>模型推演存在不确定性，不构成收益承诺或投注建议。请遵守所在地法律并量力而行。</p>
      </div>
      <label className="check-row">
        <input type="checkbox" checked={age} onChange={(event) => setAge(event.target.checked)} />
        <span>我确认已年满 18 周岁</span>
      </label>
      <label className="check-row">
        <input type="checkbox" checked={terms} onChange={(event) => setTerms(event.target.checked)} />
        <span>我同意《风险声明与隐私条款》</span>
      </label>
      {error ? <p className="form-message error" role="alert">{error}</p> : null}
      <button className="button primary" type="button" disabled={busy || !age || !terms} onClick={accept}>
        {busy ? "处理中…" : "同意并进入"}
      </button>
      <button className="button ghost" type="button" disabled={busy} onClick={reject}>拒绝并删除账户</button>
    </div>
  );
}
