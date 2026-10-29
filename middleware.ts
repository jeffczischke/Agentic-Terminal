// Edge Middleware: HTTP Basic Auth gate for the whole site.
//
// Works on every Vercel plan (including Hobby) — unlike Vercel's native
// "Password Protection", which is Pro-only. Credentials come from the
// project's environment variables, never from source:
//   BASIC_AUTH_USER      — the username
//   BASIC_AUTH_PASSWORD  — the password
// Set both in Vercel → Project → Settings → Environment Variables (Production).

export const config = {
  // Guard everything except Vercel internals and the favicon.
  matcher: "/((?!_next/|favicon.ico).*)",
};

export default function middleware(request: Request): Response | undefined {
  const expectedUser = process.env.BASIC_AUTH_USER;
  const expectedPass = process.env.BASIC_AUTH_PASSWORD;

  // If no credentials are configured, fail closed rather than open.
  if (!expectedUser || !expectedPass) {
    return new Response("Access is not configured.", { status: 503 });
  }

  const header = request.headers.get("authorization");
  if (header) {
    const [scheme, encoded] = header.split(" ");
    if (scheme === "Basic" && encoded) {
      const decoded = atob(encoded);
      const sep = decoded.indexOf(":");
      const user = decoded.slice(0, sep);
      const pass = decoded.slice(sep + 1);
      if (safeEqual(user, expectedUser) && safeEqual(pass, expectedPass)) {
        return undefined; // authorized — continue to the static asset
      }
    }
  }

  return new Response("Authentication required.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Agentic Terminal", charset="UTF-8"',
    },
  });
}

// Length-independent comparison to avoid leaking match length via timing.
function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
