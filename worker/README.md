# richideas-forms worker

A Cloudflare Worker that receives the site's form submissions and emails them via
[Resend](https://resend.com). About sixty lines, no framework.

## Setup (once)

1. **Resend.** Create an account, add `richideas.co.za` under Domains and publish the three DNS
   records it gives you in Cloudflare DNS (they don't touch Microsoft 365 mail). Create an API key.
   To start without touching the client's domain, verify a domain you own instead and change
   `FROM_EMAIL` in `wrangler.toml`.
2. **Deploy.**
   ```sh
   cd worker
   npx wrangler login
   npx wrangler deploy
   npx wrangler secret put RESEND_API_KEY
   ```
   `wrangler deploy` prints the URL, e.g. `https://richideas-forms.<account>.workers.dev`.
3. **Point the site at it.** In `site/assets/js/config.js` set
   `formEndpoint: "https://richideas-forms.<account>.workers.dev"` and push. Done.

## Options

- **Where mail goes:** `TO_EMAIL` in `wrangler.toml`. Per form: `TO_FREE_WILL`, `TO_REVIEW`,
  `TO_QUESTIONS`, `TO_CONTACT`, `TO_BOOK_A_MEETING` (e.g. send Will requests to Salomé).
- **Allowed origins:** `ALLOWED_ORIGINS`. Must include wherever the site is served from.
- **Keep a copy + rate limiting:** uncomment the KV block, run `npx wrangler kv namespace create FORMS`,
  paste the id. Submissions are then kept for 90 days under `sub:*` keys and each IP is limited to
  `RATE_LIMIT` submissions an hour.
- **Own hostname:** uncomment `routes` for `forms.richideas.co.za`.

## Test

```sh
cd worker && node test.mjs        # unit test with a stubbed Resend
npx wrangler dev                   # local worker on http://localhost:8787
```

Then in `site/assets/js/config.js` set `formEndpoint: "http://localhost:8787"`, serve `site/` on
port 8765 (`python3 -m http.server 8765`) and submit a form.

## Moving to Cloudflare Pages later

The handler is a standard `fetch(request, env)`; drop it into `functions/api/form.js` as a Pages
Function (`export const onRequest = (ctx) => handler.fetch(ctx.request, ctx.env, ctx)`) and set
`formEndpoint: "/api/form"`.
