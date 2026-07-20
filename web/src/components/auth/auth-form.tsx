"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";

import { createClient } from "@/lib/supabase/client";

type Mode = "login" | "signup" | "forgot";

const safeNext = (value: string | null) =>
  value?.startsWith("/") && !value.startsWith("//")
    ? value
    : "/console/predictions";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const params = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    try {
      if (mode === "signup") {
        const confirmPassword = String(form.get("confirmPassword") ?? "");
        if (password !== confirmPassword)
          throw new Error("两次输入的密码不一致");
        if (!ageConfirmed || !termsAccepted)
          throw new Error("请完成年龄与条款确认");
        const response = await fetch("/api/auth/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            password,
            ageConfirmed,
            termsAccepted,
          }),
        });
        const result = (await response.json()) as {
          error?: string;
          requiresEmailConfirmation?: boolean;
        };
        if (!response.ok)
          throw new Error(result.error ?? "注册失败，请稍后再试");
        if (result.requiresEmailConfirmation) {
          setMessage("验证邮件已发送。完成邮箱验证后，请确认同意条款。");
        } else {
          const { error: loginError } =
            await createClient().auth.signInWithPassword({ email, password });
          if (loginError) throw new Error("账户已创建，请使用邮箱和密码登录");
          router.replace("/console/predictions");
          router.refresh();
        }
      } else if (mode === "login") {
        const { error: authError } =
          await createClient().auth.signInWithPassword({ email, password });
        if (authError) throw new Error("邮箱或密码不正确");
        router.replace(safeNext(params.get("next")));
        router.refresh();
      } else {
        const redirectTo = `${window.location.origin}/auth/callback?next=/login`;
        const { error: authError } =
          await createClient().auth.resetPasswordForEmail(email, {
            redirectTo,
          });
        if (authError) throw new Error("暂时无法发送验证邮件");
        setMessage("如果该邮箱已注册，你会收到一封重置邮件。");
      }
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "请求失败，请稍后再试",
      );
    } finally {
      setBusy(false);
    }
  }

  async function oauth(provider: "github" | "google") {
    setBusy(true);
    setError(null);
    const next = mode === "signup" ? "/consent" : safeNext(params.get("next"));
    const { error: authError } = await createClient().auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    if (authError) {
      setError("暂时无法连接第三方账号");
      setBusy(false);
    }
  }

  const title =
    mode === "login" ? "欢迎回来" : mode === "signup" ? "创建账户" : "找回密码";
  const subtitle =
    mode === "login"
      ? "登录后继续查看今天的模型推演。"
      : mode === "signup"
        ? "先确认研究边界，再开始使用 Alea。"
        : "输入注册邮箱，我们会发送安全验证链接。";

  return (
    <div className="auth-card">
      <p className="eyebrow">账户</p>
      <h2>{title}</h2>
      <p className="muted">{subtitle}</p>
      {mode !== "forgot" ? (
        <div className="oauth-grid">
          <button
            disabled={busy}
            type="button"
            className="button secondary"
            onClick={() => oauth("github")}
          >
            GitHub
          </button>
          <button
            disabled={busy}
            type="button"
            className="button secondary"
            onClick={() => oauth("google")}
          >
            Google
          </button>
        </div>
      ) : null}
      {mode !== "forgot" ? (
        <div className="divider">
          <span>或使用邮箱</span>
        </div>
      ) : null}
      <form onSubmit={submit} className="auth-form">
        <label>
          邮箱
          <input
            name="email"
            type="email"
            autoComplete="email"
            required
            placeholder="you@example.com"
          />
        </label>
        {mode !== "forgot" ? (
          <label>
            密码
            <input
              name="password"
              type="password"
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              minLength={8}
              required
            />
          </label>
        ) : null}
        {mode === "signup" ? (
          <>
            <label>
              确认密码
              <input
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
              />
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={ageConfirmed}
                onChange={(event) => setAgeConfirmed(event.target.checked)}
              />
              <span>我已年满 18 周岁</span>
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(event) => setTermsAccepted(event.target.checked)}
              />
              <span>
                我同意《风险声明与隐私条款》，并理解本平台仅提供分析研究、不提供购彩服务。
              </span>
            </label>
          </>
        ) : null}
        {error ? (
          <p className="form-message error" role="alert">
            {error}
          </p>
        ) : null}
        {message ? (
          <p className="form-message success" role="status">
            {message}
          </p>
        ) : null}
        <button
          className="button primary"
          disabled={
            busy || (mode === "signup" && (!ageConfirmed || !termsAccepted))
          }
          type="submit"
        >
          {busy
            ? "处理中…"
            : mode === "login"
              ? "登录"
              : mode === "signup"
                ? "注册"
                : "发送验证邮件"}
        </button>
      </form>
      <div className="auth-links">
        {mode === "login" ? (
          <>
            <Link href="/forgot">忘记密码</Link>
            <Link href="/signup">创建账户</Link>
          </>
        ) : (
          <Link href="/login">返回登录</Link>
        )}
      </div>
    </div>
  );
}
