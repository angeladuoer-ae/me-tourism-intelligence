# ME Tourism Intelligence Hub — v0.2 patch

## Safe upgrade (GitHub website)

**Do not overwrite or delete `data/activities.json` or `data/source_status.json`.** They contain the live, accumulated records.

Replace the following repository files with the files from this patch:

1. `scripts/collect.py` — article page metadata and content extraction, conservative upcoming date detection.
2. `sources.json` — turns on Dubai DET, Jordan JTB, GoTürkiye experimental collectors. Others remain pending.
3. `tests/test_v02.py` — new tests.
4. `web/app.js` — Chinese category helper labels, not machine translation or AI analysis.
5. `web/index.html` — version indicator.
6. `.github/workflows/pages.yml` — includes JSON copy step tested in your repository.
7. `.github/workflows/update.yml` — includes `python -m pytest -q` fix.

**Important:** On GitHub, replacing a file using **Upload files** may fail to overwrite an existing file depending on UI. GitHub Desktop is simpler: clone your existing repository, copy these files while preserving their paths, commit and push. Alternatively use the pencil editor for individual files.

After the patch, run Actions → `Update public intelligence` → `Run workflow`. Check the `collect` job logs for per-source results. A green workflow means the process ran, **not** that every source succeeded. Check `data/source_status.json` to verify each individual source. Then verify `Deploy dashboard to GitHub Pages` and refresh the site.

## Expected limits

* v0.2 does **not** call any paid AI API. No automatic Chinese translation or strategic recommendations are claimed.
* Public HTML and published dates may vary; some sites block automation. Sources returning `no verified articles / review required` need site-specific adapters.
* Upcoming watchlist only lists confidently extracted future dates; it is not a comprehensive event calendar.
* Manual entries remain browser-local, not accessible on other devices. Do not upload confidential sources to a public repo.
* Existing v0.1 records are updated when re-discovered by canonical URL, but undated old records may remain unchanged until a dedicated cleanup/migration is added.
