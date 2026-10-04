#!/usr/bin/env python3
"""publisher.py -- Distribution (step 3 of the autopilot loop).

Produces and (optionally) sends the daily digest email, mirrors it to a free
Blogger blog via its built-in "post via email" feature (no API keys ever
expire), and generates weekly social-media post batches ready for Postiz/n8n.

Usage:
    python publisher.py                       # email + blog mirror (requires secrets)
    python publisher.py --social-only         # generate social drafts only

No credentials are read from config files; use GitHub repo Secrets:
  SMTP_USER, SMTP_PASS, EMAIL_TO, BLOGGER_SECRET_EMAIL_ADDRESS.

Licensed MIT.
"""
import os
import sys
import json
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime, timezone

import yaml


def load_entries():
    p = Path("data/entries.json")
    if not p.exists():
        raise SystemExit("No data/entries.json found — run 'python ingest.py' first.")
    with open(p) as fh:
        return json.load(fh)["entries"]


def load_config():
    with open("config.yaml") as fh:
        return yaml.safe_load(fh)


def fmt_time(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def make_entry(e):
    d = e.get("description") or ""
    if len(d) > 140:
        d = d[:140] + "..."
    off = e.get("affiliate", {}) or {}
    return {
        "title": e.get("title") or "Untitled",
        "url": e.get("url"),
        "description": d,
        "program": off.get("program"),
        "offer_url": off.get("offer_url"),
        "label": off.get("label") or "Visit official site",
    }


def build_digest_body(entries, day_label="TODAY"):
    random.seed(datetime.now().hour)  # deterministic per hour; shuffle fairly
    picked = entries[:max(5, min(12, len(entries)))]
    html_parts = []
    text_parts = []
    html_parts.append(f"<h2>🤖 Curated Resources Digest • {day_label}</h2>")
    text_parts.append(f"Curated Resources Digest -- {day_label}")
    for i, e in enumerate(picked, 1):
        title = e["title"]
        url = e["url"]
        offer = e["offer_url"]
        label = e["label"]
        html_parts.append(f"<h3>{i}. <a href='{url}' rel='nofollow'>{title}</a></h3>")
        html_parts.append(f"<p>{e['description']} <a href='{offer}' rel='nofollow'>{label}</a></p>")
        text_parts.append(f"{i}. {title}")
        text_parts.append(f"   {url}")
        text_parts.append(f"   {e['description']}")
        text_parts.append(f"   Offer: {offer} ({label})")
    footer_html = ("<hr><p style='color:#666;font-size:12px;'>Sent by your automated loop.</p>" +
                   "<p><a href='/attribution.html'>Source attribution & licenses</a></p>")
    html_parts.append(footer_html)
    text_parts.append("")
    text_parts.append("--")
    text_parts.append("Sent by your automated loop. Source attribution: site/attribution.html")
    return "\n".join(text_parts), "\n".join(html_parts)


def send_email(subject, text, html):
    smtp_cfg = load_config()["distribution"]["smtp"]
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("EMAIL_TO")
    bcc = os.environ.get("BLOGGER_SECRET_EMAIL_ADDRESS")
    if not all([user, password, to_addr]):
        print("[email] skipped — SMTP_USER/SMTP_PASS/EMAIL_TO secrets not set")
        return None
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{load_config()['site']['name']} <{user}>"
    msg["To"] = to_addr
    if bcc:
        msg["Bcc"] = bcc
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    server = smtplib.SMTP(smtp_cfg.get("host", "smtp.gmail.com"), int(smtp_cfg.get("port", 587)))
    server.starttls()
    server.login(user, password)
    server.sendmail(user, [to_addr] + ([bcc] if bcc else []), msg.as_string())
    server.quit()
    recipients = [to_addr]
    if bcc:
        recipients.append(bcc)
    print(f"[email] sent to {recipients}")
    return msg


def generate_social_batch(entries, out_dir):
    """Write one .txt file per weekday containing a curated thread draft."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%A")
    picks = entries[:9]
    lines = [f"🔥 Top {len(picks)} curated resources this {day}", "", "1/"]
    for i, e in enumerate(picks, 1):
        next_n = f"{i+1}/" if i < len(picks) else "END"
        lines.append(f"{next_n} {e['title']} - {e.get('description','')[:110]} ... {e['url']}")
    body = "\n".join(lines)
    fp = out / f"social-{datetime.now().strftime('%Y%m%d')}-{day[:3]}.txt"
    fp.write_text(body)
    print(f"[social] wrote {fp}")


def main():
    cfg = load_config()
    dist = cfg.get("distribution", {})
    if not dist.get("enabled", True):
        print("[publisher] distribution disabled in config; use --social-only to still generate drafts")
    entries = load_entries()
    if not entries:
        print("[publisher] no entries to distribute")
        return

    day = datetime.now().strftime("%A %b %d")
    subject = f"🔥 {day}: {len(entries)} curated resources inside"
    text, html = build_digest_body([make_entry(e) for e in entries], day)

    if os.environ.get("SOCIAL_ONLY") == "1" or "--social-only" in sys.argv:
        generate_social_batch(entries, cfg["output"]["posts_dir"])
        print("[publisher] done (social drafts only)")
        return

    send_email(subject, text, html)
    generate_social_batch(entries, cfg["output"]["posts_dir"])
    print("[publisher] done")


if __name__ == "__main__":
    main()
