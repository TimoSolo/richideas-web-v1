# Notes for Claude

## Deploying after a push

`.github/workflows/deploy.yml` deploys `site/` to Cloudflare Pages on every push to `main`, but pushes
made with `git push` from a Claude Code cloud session do not start the workflow. The Cloudflare secrets
are fine.

After pushing a change under `site/`, start the deploy yourself: run the `deploy.yml` workflow on `main`
with the GitHub `actions_run_trigger` tool (`run_workflow`). Then check that the live site
(https://richideas.co.za/) shows the change before saying it is live.

## Editing pages

Forms live in `templates/forms/` and `scripts/build.py` injects them into `site/`. When changing a form,
edit both the template and the built page under `site/` so they stay in sync.
