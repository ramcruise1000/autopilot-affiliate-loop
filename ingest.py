#!/usr/bin/env python3
"""ingest.py -- Content Ingestion (step 1 of the autopilot loop).

Fetches the GitHub repositories configured in config.yaml, validates that each
source is permissively licensed, parses its curated list of tools/resources,
normalizes & deduplicates entries, enriches them with affiliate-program offers
(affiliates.json), and writes /data/entries.json plus a run log.

Usage:
    python ingest.py                          # uses config.yaml in cwd
    LOOP_CONFIG=prod.yaml python ingest.py
    LOOP_DATA=./data python ingest.py

Licensed MIT.
"""
import os
import re
import json
import yaml
from pathlib import Path
from difflib import SequenceMatcher

import github  # PyGithub: unauthenticated access works against public repos


# ---------- defaults / constants ---------------------------------------------
CONFIG_PATH = Path(os.environ.get("LOOP_CONFIG", "config.yaml"))
DATA_DIR = Path(os.environ.get("LOOP_DATA", str(Path.cwd() / "data")))
ALLOWED_LICENSES = {
    "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause",
    "gpl-3.0-only", "cc0-1.0", "cc-by-4.0", "unlicense",
}
COPyleft_LICENSES = {"gpl-3.0-only", "lgpl-3.0", "agpl-3.0"}
TRACKING_PREFIXES = (
    "utm_", "fbclid_", "igshid_", "xpid_", "tw_src_", "twitterref_",
    "igpr_", "gtm_", "gclid_", "yclid_", "refid_", "srsltid_",
)
TRACKING_PARAMS = set(p.replace("_", "") for p in TRACKING_PREFIXES)


class Log:
    def __init__(self):
        self.items = []
    def info(self, msg, **kw): self.items.append({"level": "INFO", "msg": msg.format(**kw)})
    def warn(self, msg, **kw): self.items.append({"level": "WARN", "msg": msg.format(**kw)})
    def error(self, msg, **kw): self.items.append({"level": "ERROR", "msg": msg.format(**kw)})
    def dump(self):
        return {"started": None, "ended": None, "steps": self.items}


log = Log()


def clean_text(s):
    """Strip markdown links/formatting and collapse whitespace."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)   # [text](url) -> text
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)           # bold
    s = re.sub(r"__([^_]+)__',", r"\1", s)
    return re.sub(r"\s+", " ", s.strip())


def canonical_url(url):
    """Normalize URL for de-duplication."""
    try:
        from urllib.parse import urlparse, urlsplit, urlunsplit, parse_qsl, urlencode
        p = urlparse(url)
        host = p.netloc.lower().replace("www.", "")
        kept = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                if k.lower().split("_")[0] not in TRACKING_PARAMS
                and not any(k.lower().startswith(prefix) for prefix in TRACKING_PREFIXES)]
        query = urlencode(kept, doseq=True)
        return urlunsplit((p.scheme, host, p.path.rstrip("/"), query, "")).lower()
    except Exception:
        return url.lower()


def norm_title(t):
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return re.sub(r"\s+", " ", t)


def title_similarity(a, b):
    return SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def parse_markdown_list(md):
    """Yield ({title, url, description}) from markdown list lines."""
    out = []
    link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    bullet_re = re.compile(r"^\s*(?:[#\d]*[)\.]?\s+)?(?:[-*•]\s+)?(.+)\s*$")
    # handle trailing description after ")" like ".../tool/) - a great writer"
    desc_re = re.compile(r"\)([^-]*-(.*))$", re.S)
    for raw in md.splitlines():
        m = bullet_re.match(raw)
        if not m:
            continue
        line = m.group(1)
        lm = link_re.search(line)
        if lm:
            title, url = lm.group(1), lm.group(2)
            rest = line[lm.end():]
            dm = desc_re.search(rest)
            if dm and "".join(rest.split()).strip().endswith("-"):
                desc = clean_text(rest.split("-")[-1])
            else:
                desc = clean_text(rest).lstrip("- ")
        else:
            continue
        if len(desc) < 5:
            desc = ""
        if not title.strip():
            continue
        out.append({"title": title, "url": url, "description": desc})
    return out


def parse_markdown_categories(md):
    """Parse markdown -> (categories dict: cat -> [entries])."""
    lines = md.splitlines()
    cur_cat = None
    entries = []
    top_re = re.compile(r'^\s*#{1,2}\s+(.+?)\s*$')
    sub_re = re.compile(r'^\s*#{3,6}\s+(.+?)\s*$')
    for raw in lines:
        mt = top_re.match(raw)
        ms = sub_re.match(raw)
        if mt: cur_cat = clean_text(mt.group(1)); continue
        if ms: entries.append({"title": "", "url": "", "description": cur_cat or "Uncategorized", "_subcat": clean_text(ms.group(1))}); continue
        for item in parse_markdown_list(raw):
            item["category"] = cur_cat or "Uncategorized"
            if ms:
                item["_subcat"] = ms.group(1)
            entries.append(item)
    return entries


def fetch_github_source(owner, repo, branch="main"):
    """Return (markdown_texts, license_key_or_None, topics) for a GitHub repo."""
    g = github.Github()  # anonymous
    gh_repo = g.get_repo(f"{owner}/{repo}")
    lic = gh_repo.get_license()
    key = lic.license.key if lic else None
    try:
        topics = [t.name for t in gh_repo.get_topics()]
    except Exception:
        topics = []
    log.info("GitHub source loaded: {owner}/{repo}@{branch} license={lic_key} topics={topics_count}",
             owner=owner, repo=repo, branch=branch, lic_key=key, topics_count=len(topics))
    docs = []
    try:
        contents = gh_repo.get_contents("")
    except Exception:
        log.warn("Cannot list contents of {owner}/{repo}; skipping", owner=owner, repo=repo)
        return [], key, topics
    stack = [""]
    while stack:
        p = stack.pop()
        try:
            for c in gh_repo.get_contents(p):
                if c.type == "dir":
                    stack.append(c.path)
                elif c.path.lower().endswith(".md"):
                    try:
                        docs.append(c.decoded_content.decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
        except Exception:
            log.warn("Contents read error for {owner}/{repo}@{p}", owner=owner, repo=repo, p=p)
    return docs, key, topics


def fetch_local_source(path):
    """Read all .md files under a local directory (demo/testing only)."""
    path = Path(path)
    log.info("Local source scanned: {path}", path=path)
    docs = []
    for f in path.rglob("*.md"):
        if f.stem.lower() == "readme" and f.parent.name == path.name and len(list(path.rglob("*.md"))) <= 4:
            pass  # still include README.md
        try:
            docs.append(f.read_text(errors="ignore"))
        except Exception:
            pass
    return docs, None, []


def load_affiliates(path):
    path = Path(path)
    if not path.exists():
        log.warn("affiliates file not found at {path}; running with zero offers", path=path)
        return []
    text = path.read_text()
    try:
        data = json.loads(text)
    except Exception:
        data = yaml.safe_load(text)
    return data.get("programs", []) if isinstance(data, dict) else data


def enrich(entry, offers):
    """Attach the best matching affiliate offer, if any."""
    hay = (entry["title"] + " " + entry["description"] + " " + str(entry.get("category", ""))).lower()
    best = None
    best_score = 0
    for o in offers:
        kw = o.get("keyword", "").lower()
        score = hay.count(kw)
        if kw in entry["title"].lower():
            score += 2
        if score >= 1 and score > best_score:
            best_score = score
            best = o
    if best:
        link = best["link_template"].replace("{affiliate_id}", best.get("affiliate_id", ""))
        link = link.replace("{tool_slug}", entry.get("slug", ""))
        label = best["label"].replace("{tool_name}", entry["title"])
        entry["affiliate"] = {"program": best["name"], "offer_url": link, "label": label}
    else:
        entry["affiliate"] = {"program": None, "offer_url": entry["url"], "label": "Visit official site"}
    entry["slug"] = re.sub(r"[^a-z0-9]+", "-", entry["title"].lower()).strip("-")
    return entry


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH) as fh:
        cfg = yaml.safe_load(fh)
    cfg_sources = cfg.get("sources", [])
    max_items = int(cfg.get("ingest", {}).get("max_items", 300))
    sim_th = float(cfg.get("ingest", {}).get("dedupe_similar_title", 0.75))
    min_desc = int(cfg.get("ingest", {}).get("min_description_chars", 5))
    offers = load_affiliates(cfg["affiliates"]["file"])

    all_entries = []          # (priority, sort_key, entry)
    source_meta = []

    for i, src in enumerate(cfg_sources):
        t = src["type"]
        pri = int(src.get("priority", 50))
        if t == "github":
            docs, key, topics = fetch_github_source(src["owner"], src["repo"], src.get("branch", "main"))
            lic_name = key
            if key in COPyleft_LICENSES:
                log.warn("Copyleft source ({owner}/{repo} is under {key}) - confirm redistribution terms before publishing.",
                         owner=src["owner"], repo=src["repo"], key=key)
            if key and key not in ALLOWED_LICENSES:
                log.error("Disallowed license on {owner}/{repo}: {key}. Skipping.",
                          owner=src["owner"], repo=src["repo"], key=key)
                continue
            if not key:
                log.warn("No license file found on {owner}/{repo}; skipping (add a LICENSE file to allow reuse).",
                         owner=src["owner"], repo=src["repo"])
                continue
            for doc in docs:
                for item in parse_markdown_categories(doc):
                    item.pop("_subcat", None)
                    item["url"] = item["url"].strip()
                    item["_priority"] = pri
                    if min_desc and len(item["description"]) < min_desc:
                        continue
                    all_entries.append(item)
            source_meta.append({"owner": src["owner"], "repo": src["repo"], "branch": src.get("branch", "main"),
                                "type": "github", "license": lic_name, "topics": topics})
        elif t == "local":
            docs, key, topics = fetch_local_source(src["path"])
            lic_name = "local-scan"  # license status verified manually for demo sources
            if not docs:
                log.warn("Local source has no .md files: {path}", path=src["path"])
                continue
            for doc in docs:
                for item in parse_markdown_categories(doc):
                    item.pop("_subcat", None)
                    item["url"] = item["url"].strip()
                    item["_priority"] = pri
                    if min_desc and len(item["description"]) < min_desc:
                        continue
                    all_entries.append(item)
            source_meta.append({"owner": "local", "repo": Path(src["path"]).name, "type": "local",
                                "license": lic_name, "topics": topics})
        else:
            log.error("Unknown source type: {t}", t=t)

    # Deduplicate: same canonical URL -> same product. Higher-priority source wins.
    seen = {}
    for e in all_entries:
        key = canonical_url(e["url"])
        if key not in seen:
            seen[key] = e
        else:
            existing = seen[key]
            if e["_priority"] > existing["_priority"]:
                seen[key] = e
            elif abs(e["_priority"] - existing["_priority"]) < 0.01:
                # tie-break: keep the one with longer description / higher similarity to existing titles is avoided
                if title_similarity(e["title"], existing["title"]) < sim_th:
                    seen[key] = e if len(e["description"]) >= len(existing["description"]) else existing
    entries = list(seen.values())
    entries.sort(key=lambda e: (-int(e["_priority"]), canonical_url(e["url"])))
    for e in entries:
        del e["_priority"]
        if e.get("category") == "Uncategorized":
            e.pop("category", None)
        enrich(e, offers)
    entries = entries[:max_items]
    log.info("Ingest complete: {n} unique entries from {s} sources; offers attached", n=len(entries), s=len(source_meta))

    out = {
        "meta": {"generated_at": "placeholder", "sources": source_meta, "offers_loaded": len(offers)},
        "entries": entries,
    }
    out["meta"]["generated_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    with open(DATA_DIR / "entries.json", "w") as fh:
        json.dump(out, fh, indent=1)
    log.dump()["ended"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    with open(DATA_DIR / "log.json", "w") as fh:
        json.dump(log.dump(), fh, indent=1)
    print(f"ingest: {len(entries)} entries -> data/entries.json")


if __name__ == "__main__":
    main()
