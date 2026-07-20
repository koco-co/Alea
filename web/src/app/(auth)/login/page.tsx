import { Suspense } from "react";

import { AuthForm } from "@/components/auth/auth-form";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="auth-card">正在载入…</div>}>
      <AuthForm mode="login" />
    </Suspense>
  );
}
