#!/usr/bin/env python3
"""generator.py -- Static site generation (step 2 of the autopilot loop).

Reads data/entries.json and renders a complete static site (Jinja2):
  - index.html                 homepage with categories + featured
  - categories/*.html          per-category listings
  - entries/*.html             per-entry pages with affiliate CTAs
  - rss.xml / sitemap.xml      feeds for search engines
  - attribution.md             source-licensing attribution report

Usage:
    python generator.py                        # uses config.yaml in cwd
    LOOP_OUTPUT_SITE=./site python generator.py

Licensed MIT.
"""
import os
import json
import re
from pathlib import Path
from datetime import datetime, timezone

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


ENV = Environment(
    loader=FileSystemLoader(str(Path("src/site/template").resolve())),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def load_entries():
    p = Path("data/entries.json")
    if not p.exists():
        raise SystemExit("No data/entries.json found — run 'python ingest.py' first.")
    with open(p) as fh:
        return json.load(fh)


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"&[a-z]+;", "", s)


def make_entry(entry):
    e = dict(entry)
    e["name"] = strip_html(e["title"] or "Untitled")
    desc = strip_html(e.get("description") or "")
    e["description"] = (desc[:160] + "...") if len(desc) > 160 else desc
    if not e["description"].endswith("."):
        e["description"] += "."
    aff = e.get("affiliate") or {}
    e["offer"] = {
        "program": aff.get("program"),
        "url": aff.get("offer_url"),
        "label": aff.get("label") or "Visit official site",
    }
    e["own_link"] = e.get("url")
    return e


def build_index(entries, meta):
    env = ENV.get_template("index.html")
    cats = {}
    featured = []
    for e in entries:
        cat = e.get("category", "Uncategorized")
        cats.setdefault(cat, []).append(e)
        if len(featured) < 48:
            featured.append(e)
    html = env.render(entries=featured[:24], categories=sorted(cats.items()),
                      count=len(entries), site=meta["site"], now=datetime.now(timezone.utc))
    Path(meta["output_site"]).joinpath("index.html").write_text(html)
    print(f"index.html -> {len(entries)} entries shown")


def build_categories(entries, meta):
    cats = {}
    for e in entries:
        cats.setdefault(e.get("category", "Uncategorized"), []).append(e)
    for cat, items in cats.items():
        safe = re.sub(r"[^a-z0-9]+", "-", cat.lower()).strip("-")
        if not safe:
            safe = "misc"
        env = ENV.get_template("category.html")
        html = env.render(items=items[:50], category=cat, count=len(items),
                          site=meta["site"], now=datetime.now(timezone.utc))
        out = Path(meta["output_site"]) / "categories" / f"{safe}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html)
    print(f"categories written: {len(cats)}")


def build_entries(entries, meta):
    env = ENV.get_template("entry.html")
    written = 0
    for e in entries:
        safe = re.sub(r"[^a-z0-9]+", "-", e["slug"].lower()).strip("-")
        if not safe:
            safe = "entry-" + str(abs(hash(e["url"])))[-6:]
        html = env.render(entry=e, site=meta["site"], now=datetime.now(timezone.utc))
        out = Path(meta["output_site"]) / "entries" / f"{safe}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html)
        written += 1
    print(f"entry pages written: {written}")


def build_rss(entries, meta):
    env = ENV.get_template("rss.xml")
    html = env.render(entries=[make_entry(e) for e in entries[:30]],
                      site=meta["site"], now=datetime.now(timezone.utc))
    Path(meta["output_site"]).joinpath("rss.xml").write_text(html)
    print("rss.xml written")


def build_sitemap(entries, meta):
    urls = ["/"]
    for e in entries[:50]:
        safe = re.sub(r"[^a-z0-9]+", "-", e["slug"].lower()).strip("-")
        if safe:
            urls.append(f"/entries/{safe}.html")
    html = ENV.from_string(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '{% for u in urls %}<url><loc>{site.domain.rstrip("/")}}/{{u.lstrip("/")}}</loc></url>{% endfor %}\n</urlset>'
    ).render(urls=urls, site=meta["site"])
    Path(meta["output_site"]).joinpath("sitemap.xml").write_text(html)
    print("sitemap.xml written")


def build_attribution(source_meta, output_site):
    rows = []
    for s in source_meta:
        rows.append(
            '<tr><td><a href="https://github.com/' + s["owner"] + '/' + s["repo"] + '">' +
            s["owner"] + '/' + s["repo"] + '</a></td><td>' + s["license"] + '</td></tr>')
    html = ('<!DOCTYPE html>'
            '<html><head><meta charset="utf-8"><title>Attribution</title>'
            '<style>body{font-family:-apple-system,sans-serif;max-width:900px;margin:32px auto;line-height:1.5}</style></head>'
            '<body><h1>Source Attribution &amp; License Compliance</h1>'
            '<p>This site republishes curated lists from GitHub repositories. All listed repos are permissively licensed and credited here.</p>'
            '<table style="width:100%;border-collapse:collapse;margin-top:16px;"><tr style="background:#f4f6f8;text-align:left">'
            '<th style="padding:8px">Source repo</th><th style="padding:8px">License</th></tr>'
            + ''.join(rows) + '</table>'
            '<p style="margin-top:16px;font-size:13px;color:#6b7280">Keep this page in sync every run so your license compliance stays verifiable.</p>'
            '</body></html>')
    Path(output_site).joinpath("attribution.md").write_text(html)
    print("attribution page written")


def main():
    with open("config.yaml") as fh:
        cfg = yaml.safe_load(fh)
    data = load_entries()
    site = cfg.get("site", {})
    output_site = os.environ.get("LOOP_OUTPUT_SITE", str(Path(cfg["output"]["site_dir"])))
    Path(output_site).mkdir(parents=True, exist_ok=True)

    build_index(data["entries"], {"site": site, "output_site": output_site})
    build_categories(data["entries"], {"site": site, "output_site": output_site})
    build_entries(data["entries"], {"site": site, "output_site": output_site})
    build_rss(data["entries"], {"site": site, "output_site": output_site})
    build_sitemap(data["entries"], {"site": site, "output_site": output_site})
    build_attribution(data["meta"].get("sources", []), output_site)
    print("generator: static site built at", output_site)


if __name__ == "__main__":
    main()
