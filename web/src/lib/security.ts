const ALLOWED_TAGS = new Set([
  "A",
  "B",
  "BLOCKQUOTE",
  "BR",
  "CODE",
  "EM",
  "LI",
  "OL",
  "P",
  "PRE",
  "STRONG",
  "UL",
]);

const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

export function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ] ?? character,
  );
}

export function sanitizeHtml(value: string): string {
  if (typeof DOMParser === "undefined") return escapeHtml(value);
  const document = new DOMParser().parseFromString(value, "text/html");
  for (const element of [...document.body.querySelectorAll("*")]) {
    if (!ALLOWED_TAGS.has(element.tagName)) {
      element.replaceWith(document.createTextNode(element.textContent ?? ""));
      continue;
    }
    const href = element.tagName === "A" ? element.getAttribute("href") : null;
    for (const attribute of [...element.attributes]) element.removeAttribute(attribute.name);
    if (element.tagName === "A") {
      try {
        const url = new URL(href ?? "", window.location.origin);
        if (!SAFE_PROTOCOLS.has(url.protocol)) throw new Error("unsafe protocol");
        element.setAttribute("href", url.href);
        element.setAttribute("rel", "nofollow noopener");
        if (url.origin !== window.location.origin) element.setAttribute("target", "_blank");
      } catch {
        element.replaceWith(document.createTextNode(element.textContent ?? ""));
      }
    }
  }
  return document.body.innerHTML;
}

export function sanitizeMarkdown(value: string): string {
  const escaped = escapeHtml(value);
  const links = escaped.replace(/\[([^\]]+)]\(([^)]+)\)/g, (_match, label, href) => {
    try {
      const url = new URL(href, "https://alea.invalid");
      if (!SAFE_PROTOCOLS.has(url.protocol)) return label;
      const target = url.origin === "https://alea.invalid" ? url.pathname : url.href;
      return `<a href="${escapeHtml(target)}" rel="nofollow noopener">${label}</a>`;
    } catch {
      return label;
    }
  });
  return links
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

export function createCsrfToken(): string {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes)).replace(/[+/=]/g, "");
}

export function contentSecurityPolicy(nonce: string): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https://*.supabase.co wss://*.supabase.co",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    "upgrade-insecure-requests",
  ].join("; ");
}

const SENSITIVE_KEYS = /authorization|cookie|api[-_]?key|secret|token|password|provider.*body/i;

export function redactSensitive(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactSensitive);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        SENSITIVE_KEYS.test(key) ? "[REDACTED]" : redactSensitive(item),
      ]),
    );
  }
  if (typeof value === "string") {
    return value
      .replace(/\bBearer\s+\S+/gi, "Bearer [REDACTED]")
      .replace(/\b(?:sk|key|token)[-_][a-z0-9_-]{8,}\b/gi, "[REDACTED]");
  }
  return value;
}
