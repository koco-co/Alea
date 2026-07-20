import { NextResponse } from "next/server";

interface SignupBody {
  email?: unknown;
  password?: unknown;
  ageConfirmed?: unknown;
  termsAccepted?: unknown;
}

export async function POST(request: Request) {
  const requestUrl = new URL(request.url);
  if (request.headers.get("origin") !== requestUrl.origin) {
    return NextResponse.json({ error: "请求来源无效" }, { status: 403 });
  }
  let body: SignupBody;
  try {
    body = (await request.json()) as SignupBody;
  } catch {
    return NextResponse.json({ error: "请求格式无效" }, { status: 400 });
  }
  const email = typeof body.email === "string" ? body.email.trim() : "";
  const password = typeof body.password === "string" ? body.password : "";
  if (!email || password.length < 8) {
    return NextResponse.json(
      { error: "请输入有效邮箱与至少 8 位密码" },
      { status: 400 },
    );
  }
  if (body.ageConfirmed !== true || body.termsAccepted !== true) {
    return NextResponse.json(
      { error: "必须确认年满 18 周岁并同意风险与隐私条款" },
      { status: 422 },
    );
  }
  const internalApiUrl = process.env.INTERNAL_API_URL;
  if (!internalApiUrl)
    return NextResponse.json({ error: "认证服务尚未配置" }, { status: 503 });
  try {
    const upstream = await fetch(
      `${internalApiUrl.replace(/\/$/, "")}/auth/signup`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": crypto.randomUUID(),
        },
        body: JSON.stringify({
          email,
          password,
          age_confirmed: body.ageConfirmed,
          terms_accepted: body.termsAccepted,
        }),
        cache: "no-store",
      },
    );
    const result = (await upstream.json()) as {
      error?: string;
      requiresEmailConfirmation?: boolean;
    };
    if (!upstream.ok) {
      const message =
        result.error === "consent_persistence_failed"
          ? "同意记录未能安全保存，账户未创建"
          : "无法创建账户，请检查邮箱或稍后再试";
      return NextResponse.json({ error: message }, { status: upstream.status });
    }
    return NextResponse.json(
      { requiresEmailConfirmation: result.requiresEmailConfirmation ?? true },
      { status: 201 },
    );
  } catch {
    return NextResponse.json({ error: "认证服务暂时不可用" }, { status: 503 });
  }
}
