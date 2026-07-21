import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  let credentials: { email?: unknown; password?: unknown };
  try {
    credentials = (await request.json()) as {
      email?: unknown;
      password?: unknown;
    };
  } catch {
    return NextResponse.json({ error: "请求格式无效" }, { status: 400 });
  }
  const email =
    typeof credentials.email === "string" ? credentials.email.trim() : "";
  const password =
    typeof credentials.password === "string" ? credentials.password : "";
  if (!email || !password) {
    return NextResponse.json({ error: "请输入邮箱和密码" }, { status: 400 });
  }
  try {
    const supabase = await createClient();
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) {
      return NextResponse.json({ error: "邮箱或密码不正确" }, { status: 401 });
    }
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json(
      { error: "无法连接认证服务，请稍后重试" },
      { status: 503 },
    );
  }
}
