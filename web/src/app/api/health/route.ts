export const dynamic = "force-dynamic";

export function GET(): Response {
  return Response.json({ service: "alea-web", status: "ok" });
}
