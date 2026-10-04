# License Compliance Checklist for Loop Operators

When this loop republishes material from GitHub repositories, YOU remain
responsible for legal compliance. Run through this checklist before going live.

## 1. Only ingest permissively licensed source repos

The loop rejects repos without a recognizable license file (`LICENSE`). That
list is configurable (`ALLOWED_LICENSES` in `ingest.py`): MIT, Apache-2.0,
BSD-2/3-Clause, GPL-3.0, CC0-1.0, CC-BY-4.0, Unlicense. It **warns** on
copyleft-only licenses (GPL/AGPL) — redistribution of a combined work may
require licensing your whole site under GPL; confirm terms before publishing.

**Never** point the loop at a repo whose README/contents state "all rights
reserved", "proprietary", or "no commercial use".

## 2. Preserve attribution and license notices

Every published page carries an `/attribution.html` page listing each source
repo and its license. Do not remove it. The generated site's own code is MIT,
buth source *content* keeps its original license.

## 3. FTC / advertising disclosure

The footer on every page contains the required affiliate disclosure text. If
you operate from a jurisdiction with its own rules (e.g., ASA in the UK), add
the equivalent there too.

## 4. Affiliate-program terms of service

Common rules you MUST read before publishing:

| Network | Key restrictions to check |
|---|---|
| Amazon Associates | No bids on brand keywords; no false claims; disclose clearly; link rules |
| ShareASale / CJ / Impact | Varies by advertiser; many ban coupon-site misrepresentation and paid search on brand terms |
| SaaS programs (hosting, AI tools) | Recurring commission terms; cookie duration; no "free trial" guarantees unless allowed |

Do not claim the site is "official", "sponsored", or "endorsed" by any product.

## 5. Platform TOS you must respect

- **GitHub API**: rate limits apply; do not hammer endpoints. The loop is
  conservative (weekly runs; one request per source).
- **Email**: SMTP/TOS of your provider; Gmail free tier ≈ 500/day. Include an
  unsubscribe mechanism if you grow the mailing list beyond friends/family.
- **Blogger post-via-email**: no extra accounts needed; free forever.
- **Social platforms**: Postiz/n8n/Buffer each have their own API terms; reuse
  rules differ per platform.

## 6. Copyright / scraping boundaries

Never scrape behind a login wall or paywall, and never re-host someone else's
images, videos, or full-text content — linking to their public resource is what
this loop does, which is generally compliant with the source repo's list license.

If a source maintainer asks you to stop, comply promptly.
