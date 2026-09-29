/**
 * Rich Ideas form relay: receives the JSON the site's forms POST, emails it via Resend.
 *
 * Request  : POST with JSON body {subject, form, page, replyto, ...fields} (what site/assets/js/site.js sends)
 * Response : {ok:true} or {ok:false, error}
 * Config   : wrangler.toml [vars] + secret RESEND_API_KEY
 */

const META_KEYS = new Set(["subject", "form", "page", "replyto", "access_key", "_gotcha"]);
const MAX_BODY = 64 * 1024;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin, env);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== "POST") {
      return json({ ok: false, error: "Method not allowed" }, 405, cors);
    }
    if (!originAllowed(origin, env)) {
      return json({ ok: false, error: "Origin not allowed" }, 403, cors);
    }

    const len = Number(request.headers.get("Content-Length") || 0);
    if (len > MAX_BODY) {
      return json({ ok: false, error: "Submission too large" }, 413, cors);
    }

    let data;
    try {
      data = await readBody(request);
    } catch (e) {
      return json({ ok: false, error: "Could not read submission" }, 400, cors);
    }

    // Honeypot: real visitors never fill this in.
    if (data._gotcha) {
      return json({ ok: true }, 200, cors);
    }

    const form = String(data.form || "website").slice(0, 40);
    const subject = String(data.subject || "Website enquiry").slice(0, 150);
    const fields = Object.entries(data).filter(([k, v]) => !META_KEYS.has(k) && String(v).trim() !== "");
    if (fields.length === 0) {
      return json({ ok: false, error: "Empty submission" }, 400, cors);
    }

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (env.FORMS && !(await underRateLimit(env, ip))) {
      return json({ ok: false, error: "Too many submissions, please try again later" }, 429, cors);
    }

    const replyTo = String(data.replyto || data.Email || data["Email address"] || "").trim();
    const text = renderText(fields, { form, page: data.page, ip, country: request.headers.get("CF-IPCountry") });
    const to = recipientFor(form, env);

    const sent = await sendWithResend(env, { to, subject, text, replyTo: EMAIL_RE.test(replyTo) ? replyTo : undefined });
    if (env.FORMS) {
      ctx.waitUntil(
        env.FORMS.put(`sub:${Date.now()}:${form}`, JSON.stringify({ form, subject, fields, page: data.page, ip, sent: sent.ok, at: new Date().toISOString() }), {
          expirationTtl: 60 * 60 * 24 * 90
        })
      );
    }
    if (!sent.ok) {
      return json({ ok: false, error: "Email could not be sent" }, 502, cors);
    }
    return json({ ok: true }, 200, cors);
  }
};

function corsHeaders(origin, env) {
  const h = {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin"
  };
  if (originAllowed(origin, env)) {
    h["Access-Control-Allow-Origin"] = origin;
  }
  return h;
}

function originAllowed(origin, env) {
  if (!origin) return false;
  const allowed = String(env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
  return allowed.includes(origin);
}

async function readBody(request) {
  const type = request.headers.get("Content-Type") || "";
  if (type.includes("application/json")) {
    const text = await request.text();
    if (text.length > MAX_BODY) throw new Error("too large");
    return JSON.parse(text);
  }
  const fd = await request.formData();
  const out = {};
  for (const [k, v] of fd.entries()) {
    if (typeof v !== "string") continue;
    out[k] = out[k] ? out[k] + ", " + v : v;
  }
  return out;
}

function recipientFor(form, env) {
  const key = "TO_" + form.toUpperCase().replace(/[^A-Z0-9]+/g, "_");
  return env[key] || env.TO_EMAIL;
}

function renderText(fields, meta) {
  const lines = fields.map(([k, v]) => `${k}: ${String(v).slice(0, 4000)}`);
  lines.push("", "---", `Form: ${meta.form}`);
  if (meta.page) lines.push(`Page: ${meta.page}`);
  lines.push(`Sent: ${new Date().toISOString()}`, `From IP: ${meta.ip}${meta.country ? " (" + meta.country + ")" : ""}`);
  return lines.join("\n");
}

async function underRateLimit(env, ip) {
  const limit = Number(env.RATE_LIMIT || 10);
  const hour = Math.floor(Date.now() / 3600000);
  const key = `rl:${ip}:${hour}`;
  const n = Number((await env.FORMS.get(key)) || 0) + 1;
  await env.FORMS.put(key, String(n), { expirationTtl: 3600 });
  return n <= limit;
}

async function sendWithResend(env, { to, subject, text, replyTo }) {
  if (!env.RESEND_API_KEY) {
    return { ok: false, error: "RESEND_API_KEY not set" };
  }
  const body = { from: env.FROM_EMAIL, to: [to], subject, text };
  if (replyTo) body.reply_to = replyTo;
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!r.ok) {
      console.error("Resend error", r.status, await r.text());
      return { ok: false, error: `Resend ${r.status}` };
    }
    return { ok: true };
  } catch (e) {
    console.error("Resend request failed", e);
    return { ok: false, error: String(e) };
  }
}

function json(obj, status, headers) {
  return new Response(JSON.stringify(obj), { status, headers: { ...headers, "Content-Type": "application/json" } });
}
