// Minimal test of the worker with Resend stubbed. Run: node test.mjs
import worker from "./src/index.js";

const env = {
  ALLOWED_ORIGINS: "https://timosolo.me,https://richideas.co.za",
  TO_EMAIL: "hello@richideas.co.za",
  TO_FREE_WILL: "salome@richideas.co.za",
  FROM_EMAIL: "Rich Ideas website <website@richideas.co.za>",
  RESEND_API_KEY: "re_test"
};
const calls = [];
globalThis.fetch = async (url, init) => { calls.push({ url, body: JSON.parse(init.body) }); return new Response("{}", { status: 200 }); };
const ctx = { waitUntil() {} };
const post = (body, origin = "https://timosolo.me", type = "application/json") =>
  worker.fetch(new Request("https://forms.example/", { method: "POST", headers: { "Content-Type": type, Origin: origin }, body: typeof body === "string" ? body : JSON.stringify(body) }), env, ctx);

let fails = 0;
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails++; };

let r = await post({ subject: "Website: free Will request", form: "free-will", page: "https://timosolo.me/x", replyto: "jane@example.com", "Full name": "Jane Doe", Phone: "0831234567", Notes: "Two kids" });
check("accepts a valid submission", r.status === 200 && (await r.json()).ok === true);
check("routes free-will to Salomé", calls[0].body.to[0] === "salome@richideas.co.za");
check("sets reply-to to the visitor", calls[0].body.reply_to === "jane@example.com");
check("renders fields in order", calls[0].body.text.startsWith("Full name: Jane Doe\nPhone: 0831234567\nNotes: Two kids"));
check("keeps subject", calls[0].body.subject === "Website: free Will request");

r = await post({ subject: "x", form: "contact", Name: "A", _gotcha: "spam" });
check("honeypot returns ok without sending", r.status === 200 && calls.length === 1);

r = await post({ subject: "x", form: "contact", Name: "A" }, "https://evil.example");
check("rejects unknown origin", r.status === 403);

r = await worker.fetch(new Request("https://forms.example/", { method: "OPTIONS", headers: { Origin: "https://timosolo.me" } }), env, ctx);
check("preflight allows the site origin", r.status === 204 && r.headers.get("Access-Control-Allow-Origin") === "https://timosolo.me");

r = await post("Name=Bob&Email=bob%40example.com&Message=Hi&form=contact&subject=Website%3A+contact+message", "https://richideas.co.za", "application/x-www-form-urlencoded");
check("accepts form-encoded bodies and defaults recipient", r.status === 200 && calls[1].body.to[0] === "hello@richideas.co.za" && calls[1].body.reply_to === "bob@example.com");

r = await post({ subject: "x", form: "contact" });
check("rejects empty submission", r.status === 400);

globalThis.fetch = async () => new Response("nope", { status: 401 });
r = await post({ subject: "x", form: "contact", Name: "A" });
check("reports Resend failure as 502", r.status === 502);

console.log(fails ? `${fails} failing` : "all passed");
process.exit(fails ? 1 : 0);
