import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { AppRouterContext } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { SearchParamsContext } from "next/dist/shared/lib/hooks-client-context.shared-runtime";

import AuthLayout from "../src/app/(auth)/layout";
import MarketingHomePage from "../src/app/(marketing)/page";
import CalculatorPage from "../src/app/console/calculator/page";
import FixtureDetailPage from "../src/app/console/fixtures/[id]/page";
import FixturesPage from "../src/app/console/fixtures/page";
import ConsolePage from "../src/app/console/page";
import PredictionDetailPage from "../src/app/console/predictions/[id]/page";
import PredictionsPage from "../src/app/console/predictions/page";
import { AuthForm } from "../src/components/auth/auth-form";
import { ConsentForm } from "../src/components/auth/consent-form";
import { TopNavView } from "../src/components/ui/top-nav";

const target = process.argv[2] ?? "console-admin";
const outputPath = process.argv[3];
const router = {
  back() {},
  forward() {},
  refresh() {},
  hmrRefresh() {},
  push() {},
  replace() {},
  prefetch: async () => undefined,
};

function withRouter(element: React.ReactNode): React.ReactElement {
  return (
    <AppRouterContext.Provider value={router}>
      <SearchParamsContext.Provider value={new URLSearchParams()}>
        {element}
      </SearchParamsContext.Provider>
    </AppRouterContext.Provider>
  );
}

let content: React.ReactNode;
if (target === "marketing") {
  content = <MarketingHomePage />;
} else if (["predictions", "prediction-detail", "fixtures", "fixture-detail", "calculator"].includes(target)) {
  const routeContent =
    target === "predictions" ? <PredictionsPage /> :
    target === "prediction-detail" ? await PredictionDetailPage({ params: Promise.resolve({ id: "n8c4-02" }) }) :
    target === "fixtures" ? <FixturesPage /> :
    target === "fixture-detail" ? await FixtureDetailPage({ params: Promise.resolve({ id: "104" }) }) :
    <CalculatorPage />;
  const path =
    target === "predictions" ? "/console/predictions" :
    target === "prediction-detail" ? "/console/predictions/n8c4-02" :
    target === "fixtures" ? "/console/fixtures" :
    target === "fixture-detail" ? "/console/fixtures/104" :
    "/console/calculator";
  content = <div className="console-shell"><TopNavView role="user" email="user@alea.local" path={path} />{routeContent}</div>;
} else if (target.startsWith("console")) {
  const role = target.endsWith("user") ? "user" : "admin";
  process.env.ALEA_DEMO_ROLE = role;
  content = (
    <div className="console-shell">
      <TopNavView role={role} email={`${role}@alea.local`} path="/console" />
      {await ConsolePage()}
    </div>
  );
} else {
  const authContent =
    target === "consent" ? (
      <ConsentForm />
    ) : (
      <AuthForm mode={target === "signup" || target === "forgot" ? target : "login"} />
    );
  content = <AuthLayout>{withRouter(authContent)}</AuthLayout>;
}

const builtCssDirectory = new URL("../.next/static/css/", import.meta.url);
const builtCssFile = readdirSync(builtCssDirectory).find((file) => file.endsWith(".css"));
const css = builtCssFile
  ? readFileSync(new URL(builtCssFile, builtCssDirectory), "utf8")
  : readFileSync(new URL("../src/app/globals.css", import.meta.url), "utf8").replace('@import "tailwindcss";', "");
const body = renderToStaticMarkup(withRouter(content));
const assetRoot = new URL("../public/assets/", import.meta.url).pathname;
const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alea visual check</title><style>${css}</style></head><body>${body}</body></html>`
  .replaceAll('src="/assets/', `src="file://${assetRoot}`);
if (outputPath) writeFileSync(outputPath, html);
else process.stdout.write(html);
