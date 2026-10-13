// Password gate for the test site only. Every host except the live domains
// asks for a password (browser basic-auth prompt; the username is ignored).
// The password is the STAGING_PASSWORD secret on the Pages project:
//   npx wrangler pages secret put STAGING_PASSWORD --project-name richideas
const LIVE_HOSTS = new Set(["richideas.co.za", "www.richideas.co.za"]);

export async function onRequest({ request, env, next }) {
  const { hostname } = new URL(request.url);
  if (LIVE_HOSTS.has(hostname)) return next();

  const password = env.STAGING_PASSWORD;
  const given = atob((request.headers.get("Authorization") || "").slice(6) || "Og==");
  if (password && given.slice(given.indexOf(":") + 1) === password) return next();

  return new Response("Password required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Rich Ideas preview"', "Cache-Control": "no-store" },
  });
}
