export function isSameOriginRequest(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return false;
  const requestUrl = new URL(request.url);
  const allowedOrigins = new Set([requestUrl.origin]);
  const forwardedHost =
    request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (forwardedHost) {
    const forwardedProtocol =
      request.headers.get("x-forwarded-proto") ??
      requestUrl.protocol.replace(":", "");
    if (forwardedProtocol === "http" || forwardedProtocol === "https") {
      allowedOrigins.add(`${forwardedProtocol}://${forwardedHost}`);
    }
  }
  return allowedOrigins.has(origin);
}
