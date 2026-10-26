# ME Tourism Intelligence Hub — GitHub MVP v0.1

Static GitHub Pages dashboard + scheduled GitHub Actions collector + browser-local private leads.

## Features implemented
- Daily automatic collection (03:15 UTC) and GitHub Actions **Run workflow** manual re-run.
- Conservative collection from publicly accessible, same-domain official newsroom listing links. Initial enabled sources: Emirates and Etihad; other destinations are registered but disabled until custom collector verification.
- Chinese dashboard, competitor/category/search filters, explicit upcoming dates, source run status.
- Private manual intelligence form, local browser storage, JSON backup/import, confidential flag, verification label.
- English Markdown brief draft. **Not AI-generated**; impact and recommendations explicitly require analyst review.

## Quick start (GitHub)
1. Create an empty GitHub repository, default branch `main`.
2. Upload all contents of this folder (including `.github/workflows/`). Do **not** upload your private manual-lead JSON backup.
3. In **Settings → Pages**, select **GitHub Actions** as deployment source.
4. In **Actions → Update public intelligence → Run workflow**, run the collector manually for the first time.
5. In **Actions → Deploy dashboard to GitHub Pages**, check the deployment. Your published URL follows `https://<owner>.github.io/<repo>/` (subject to account and repo settings).
6. Open the site, view updated records and source status; schedule runs daily automatically (GitHub cron may be delayed or skipped under high load).

## Local test
```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/collect.py
mkdir -p _site && cp web/* data/*.json sources.json _site/
python -m http.server 8000 --directory _site
```
For local display the files `data/activities.json`, `data/source_status.json` and `sources.json` must also be copied into `web/`, or serve a temporary directory built like the workflow: `mkdir -p _site && cp web/* _site/ && cp data/*.json sources.json _site/ && python -m http.server 8000 --directory _site`.

## Important privacy/technical boundaries
- GitHub Pages is a **publicly accessible static website** for standard public Pages deployments. GitHub repository privacy does not automatically make the published site private. Do not publish private partner leads via Actions-generated JSON or source files.
- Manual notes stay in the **current browser's localStorage**, not in GitHub, and are absent on other devices. Back up using the JSON export; imported backups remain on the importing browser. LocalStorage is not encrypted and should **not** hold sensitive trade secrets, PII, or identifiable informants.
- A browser-side button cannot safely trigger a GitHub workflow without an authenticated backend. Manual refresh fetches the latest deployed data; start an actual new scrape via the Actions workflow page.
- Listing-page extraction provides leads, **not verified full articles**. Publication dates may be missing; inferred future dates are tentative. Open the cited original URL before publishing reports.
- The `sources.json` registry enumerates candidates; `enabled=false` explicitly means the collector is not validated for that site. Social/OTA integrations require separate permissions and adapters.
- English report export is template-driven in v0.1; OpenAI analysis requires a separate server-side job, secrets, controlled prompt, review flow, and cost controls.
- For organization deployment, request approval before publishing publicly; avoid committing confidential data or API credentials.

## Next development milestones
1. Source-specific selectors, complete article parsing, HTML change detection, robots/policy review.
2. Normalized activity database (Postgres): `activities`, `sources`, `evidence`, `status_history`, `manual_leads`, `reviews`.
3. Reliable upcoming date/event-state extraction, human review, postponement/cancellation tracking.
4. Server-side AI summarization with citations and explicit fact/inference boundaries.
5. Authenticated private input if sharing manual leads across devices or team members; not GitHub Pages alone.
6. Weekly scheduled report (docx/pptx) only after human-review workflow.
