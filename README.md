# Autopilot Affiliate Loop

**Build it once — it runs 24/7, forever.** This repo contains a fully working
"set once and forget it" affiliate business loop: it pulls curated resource
tools from open-source GitHub repositories (content someone else already built),
generates a searchable static site with affiliate offers attached, and distributes
daily email digests + social posts automatically. Zero daily effort after setup.

Cost to run: **$0/forever** (GitHub Actions free tier on public repos; free
Blogger mirror; Gmail SMTP).

---

## How it actually makes money (the loop)

```
┌───────────────────┐     fetch weekly     ┌────────────────────────────┐
│ GitHub            │ ──────────────────► │ ingest.py                  │
│ curated lists     │   (MIT/Apache/BSD)  │ license-check + parse      │
│ (existing         │                     │ normalize · dedupe          │
│ material)         │                     │ attach affiliate offers     │
└───────────────────┘                     └──────────────┬─────────────┘
                                                         │ data/entries.json
                    ┌────────────────────────────────────┴─────────────────┐
                    │                                                       │
                    ▼                                                       ▼
        ┌───────────────────────┐                              ┌─────────────────────┐
        │ generator.py          │                              │ publisher.py        │
        │ static site           │                              │ digest email (+      │
        │ index/categories/     │                              │ optional Blogger    │
        │ entry pages w/        │                              │ mirror, social      │
        │ affiliate CTA blocks  │                              │ drafts for          │
        └───────────┬───────────┘                              │ Postiz/n8n)         │
                    │ git push to gh-pages                     └─────────────────────┘
                    ▼
        ┌───────────────────────┐
        │ GitHub Pages          │  visitors click affiliate links → you earn
        │ yourname.github.io    │  recurring hosting commissions (hostinger,
        └───────────────────────┘  siteground, bluehost) + per-sale tool
                                    commissions (AI tools, design SaaS)
```

The loop = **source → ingest → generate → distribute → earn**, triggered by a
GitHub Actions cron schedule. After day 1 there is nothing to touch.

### Why this model works as autopilot

1. **Content already exists** — you reuse MIT-licensed community-maintained lists
   of tools/APIs (e.g. `eudk/awesome-ai-tools`, `public-apis/public-apis`). You
   never write articles yourself; the repo just grows over time.
2. **Evergreen traffic** — curated "best X resources" pages keep getting searched
   and shared for years; the RSS feed feeds newsletters/directories too.
3. **Recurring commissions** — web hosting affiliate programs pay monthly
   for life when a visitor signs up; that's compounding revenue as new pages
   accumulate.
4. **Zero infrastructure** — static files on GitHub Pages, scheduling via GitHub
   Actions, email via your existing Gmail. No server, no credits card.

---

## Contents of this repo

| File | Purpose |
|---|---|
| `config.example.yaml` | Copy to `config.yaml`; point sources, set outputs |
| `ingest.py` | Clones configured GitHub repos, checks licenses, parses lists, dedupes, attaches affiliate offers |
| `generator.py` | Jinja2 static-site builder (home, categories, per-entry pages, RSS, sitemap) |
| `publisher.py` | Daily digest email (SMTP), Blogger "post via email" mirror, weekly social post drafts |
| `.github/workflows/loop.yml` | Main scheduler: ingest → build → deploy to gh-pages every Sunday |
| `.github/workflows/keepalive.yml` | Monthly commit so GitHub doesn't disable your schedule |
| `affiliates.json` / `manual_overrides.yaml` | Map keywords → your affiliate links |
| `src/site/template/` | Site HTML templates |
| `LICENSE-COMPLIANCE.md` | Legal checklist (mandatory reading before going live) |
| `demo/sample-source/` | Tiny local demo repo to test everything offline |

---

## One-time setup (about 30 minutes)

### Step 1 — Create the repo

Create a new public GitHub repo (e.g. `yourname/ai-tools-loop`) and push all these files:

```bash
cd /workspace                 # or any folder on your computer
# clone/fork the repo here, then:
git add .
git commit -m "initial autopilot loop"
git push -u origin main
```

(Or upload the files through the GitHub web UI.)

### Step 2 — Install dependencies locally (one time)

```bash
pip install -r requirements.txt
```

Required in code: `requests, feedparser, jinja2, pyyaml, PyGithub`.

### Step 3 — Configure sources and output

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

- `site.name` / `site.domain` — your site identity;
- `sources` — replace the example AI-tool source with your chosen niche repo(s).
  Every entry in an awesome-style markdown list becomes a page. Good choices:
  `eudk/awesome-ai-tools`, `public-apis/public-apis`, `nanogiants/awesome-ai-tools`,
  `goabstract/Awesome-Design-Tools` — **check each repo's LICENSE file first**.
- `affiliates.file` — your program mappings (`affiliates.json`);
- `output.*` — where artifacts land.

### Step 4 — Set your affiliate mappings

Fill `affiliates.json` with your real affiliate IDs. The default template includes
common evergreen niches:

| Niche | Program | Why it's good |
|---|---|---|
| Web hosting | Hostinger / SiteGround / Bluehost | **Recurring monthly commission** — a visitor who builds a site pays you every month |
| Design / writing | Canva Pro, Jasper | One-time + recurring, high conversion |
| APIs | RapidAPI, Apify | Your catalog entries are literally APIs — natural upsell |

See also `manual_overrides.yaml` to fix exact entries or turn offers off.

### Step 5 — Create the free distribution accounts

- **Gmail** for the digest (Gmail app password required; ~500 emails/day free).
- *(Optional)* A free **Blogger** account for the permanent archive: create `yourname.blogspot.com`
  and copy its secret "post via email" address into `config.yaml` under `distribution.blogger_mirror`
  — the digest then also becomes blog posts forever (no API keys to expire).

### Step 6 — Push credentials to GitHub Secrets

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name | Value | Required? |
|---|---|---|
| `SMTP_USER` | your Gmail address | ✅ |
| `SMTP_PASS` | the 16-char Gmail *App Password* (not your login password) | ✅ |
| `EMAIL_TO` | your address | ✅ |
| `BLOGGER_SECRET_EMAIL_ADDRESS` | Blogger posting address | optional |
| `GH_PAT` | a fine-grained GitHub PAT with `repo` scope | for keepalive/deploy |

Create the App Password at Google Account → Security → 2-Step Verification →
App passwords. Name it something like `loop-digest`.

### Step 7 — First manual run

```bash
python ingest.py
python generator.py
python publisher.py --social-only      # emails skipped unless secrets exist
```

Check `data/entries.json` and the generated `./site/`. If you want a real
offline first-pass, point `sources` at `./demo/sample-source` — it has an
MIT license and ~8 entries.

### Step 8 — Deploy & enable the schedule

```bash
git add . && git commit -m "chore: initial deploy"
git push origin main
```

GitHub Actions will now run the `loop` workflow (cron: Sundays 06:00 UTC).
Click the workflow in the Actions tab → enable it if prompted, and run it once
by hand to confirm the site builds and the email sends. Then **stop touching it**.

---

## What happens while you sleep

Every Sunday at 06:00 UTC (changeable in `loop.yml`):

1. `ingest.py` clones your source repos, validates every LICENSE file,
   parses new/changed list entries, dedupes them, and attaches your affiliate
   offers from `affiliates.json`.
2. `generator.py` rebuilds the entire static site and commits/pushes it to the
   `gh-pages` branch → live on GitHub Pages.
3. `publisher.py` writes that week's social-media thread drafts into `./posts/`
   (one `.txt` per weekday, ready to import into Postiz, n8n, Buffer, etc.).
   If SMTP secrets are present, it also sends your daily digest email to yourself
   (and BCCs your Blogger address for the permanent archive).
4. Every few days the keepalive ping commits so the GitHub schedule survives.

A single run costs ~1–3 minutes of free GitHub Actions time. On a public repo the
schedule is unlimited.

---

## Choosing content sources (the key to profitability)

The loop is agnostic to niche — you pick what monetizes. General rules:

1. **Must be permissively licensed** — MIT/Apache-2.0/BSD/CC0. Run the loop
   against your candidate first; `data/log.json` reports every license decision.
2. **Entries must be products/services with affiliate programs** — AI tools,
   design software, web hosting, APIs, templates, mockups. Avoid lists of papers
   or academic resources unless you have an adjacent offer.
3. **Prefer actively maintained repos** — weekly re-ingestion keeps content fresh
   and earns you fresh search visibility.
4. **Aim for 200+ entries** for a worthwhile site, but start small and let it
   compound as more repos join `sources`.

Top recommended sources (all MIT):
- `eudk/awesome-ai-tools` — huge AI tool directory (perfect for AI-SaaS affiliates)
- `public-apis/public-apis` — free APIs (RapidAPI/Apify hosting affiliates)
- `goabstract/Awesome-Design-Tools` — design tool stack (Canva/Adobe affiliates)

---

## Where the money comes from (tactics)

- **Hosting sidebar CTA** (recurring): every page recommends cheap fast hosting.
  Even 2–3 signups/month from a quiet niche site = steady monthly income that
  compounds as the catalog grows.
- **Entry-level affiliate links**: "Get [tool] free trial / discount" next to
  each resource.
- **Email digest**: keeps subscribers returning; digests naturally drive repeat
  clicks over months/years (evergreen inbox traffic).
- **Google AdSense** once traffic justifies it — add banner spots later;
  don't over-clutter early.

Realistic early expectation: $0–$50/month for the first few months while SEO
builds authority; recurring hosting commissions are what make this truly
passive over years.

---

## Monitoring & troubleshooting

- **Actions tab** shows run results. Green = alive. The keepalive job protects
  the cron schedule.
- Common failures:
  - *"No license file found on X/Y"* → the source repo must have a LICENSE file.
  - *SMTPAuthenticationError* → use a Gmail **App Password**, not your login password.
  - No new entries after a repo update → check `data/log.json` for parse/warn lines.
  - *Schedule disabled* → the keepalive workflow should prevent this; re-enable it
    manually in Actions once, then delete the offending manual commit.

---

## Compliance — read before going live

1. **FTC affiliate disclosure** — included in every page footer. Keep it.
2. **Source licenses** — the loop only accepts recognized permissive licenses and
   writes an `/attribution.html` page. Do not strip it. Never point the loop at
   proprietary/unlicensed content.
3. **Affiliate-program terms** — e.g. Amazon: no brand-keyword bidding, no false
   claims, clear disclosure; SaaS networks vary by advertiser.
4. **Rate limits / scraping rules** — the loop hits the GitHub API conservatively
   (weekly, one request per source). Never scrape behind logins/paywalls.
5. **Social-platform terms** — when you move the generated post drafts into
   Postiz/n8n/etc., follow each platform's API rules.

Full checklist: `LICENSE-COMPLIANCE.md`.

---

## Built from

This system reuses and generalizes the zero-maintenance autopilot patterns from
[ramcruise1000/The-Bundle-ai-news-digest-v1.0](https://github.com/ramcruise1000/The-Bundle-ai-news-digest-v1.0)
(a MIT daily AI-news digest running on GitHub Actions + Blogger post-via-email,
$0 forever) and the automated-backward-reposting / Postiz automation ecosystem.
The delivered code is MIT; source-content licenses remain with their original authors.
