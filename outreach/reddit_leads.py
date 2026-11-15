#!/usr/bin/env python3
"""Reddit hiring/client lead monitor for the outreach pipeline.

Reads public posts from the subreddits listed in outreach/subreddits.txt, keeps
the ones that read like someone buying software work (hiring, project, budget),
classifies each as a job or a client, and extracts only contact details the
poster published in the post itself. Writes outreach/leads.csv (append-only, so
manual status edits survive) and one draft message per new lead.

Data sources:
  * RSS (default, no setup) - https://www.reddit.com/r/<sub>/new/.rss
  * OAuth (reliable, 100 QPM) - set REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET,
    optionally REDDIT_USERNAME + REDDIT_PASSWORD for a password grant.

Reddit rate-limits unauthenticated RSS aggressively; the fetcher sleeps between
requests and stops cleanly on a repeated 429 instead of hammering.

No Reddit login is required for RSS, no profile scraping happens, and nothing is
sent automatically.

Usage:
  python outreach/reddit_leads.py
  python outreach/reddit_leads.py --days 2 --limit 50
  python outreach/reddit_leads.py --dry-run --verbose
  python outreach/reddit_leads.py --source oauth
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import json
import os
import random
import re
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTREACH = ROOT / "outreach"
TEMPLATES = OUTREACH / "templates"
DRAFTS = OUTREACH / "drafts"
LEADS_CSV = OUTREACH / "leads.csv"
SUBS_FILE = OUTREACH / "subreddits.txt"

USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT", "script:outreach-leads:v1.0 (by /u/saim)"
)
ATOM = {"a": "http://www.w3.org/2005/Atom"}

CSV_FIELDS = [
    "id", "date_found", "lead_type", "subreddit", "posted_date", "title",
    "author", "role_focus", "budget_hint", "contact_email", "contact_whatsapp",
    "contact_other", "permalink", "apply_url", "score", "status", "draft_file",
    "notes",
]

SEARCH_QUERIES = [
    "hiring developer",
    "looking for developer",
    "need a developer",
    "hiring AI engineer",
    "ML engineer needed",
    "build MVP developer",
    "freelance developer needed",
    "automation developer",
]

HIRING_RE = re.compile(
    r"\[?\bhiring\b\]?|\blooking for\b|\bneed (?:a|an|someone|help)\b|"
    r"\bseeking\b|\brecruit(?:er|ing|ment)?\b|\bjob (?:opening|post)\b|"
    r"\bposition\b|\bapply\b|\bvacanc(?:y|ies)\b|\bwho can (?:build|help|do)\b",
    re.I,
)
BUYER_RE = re.compile(
    r"\bbudget\b|\bpaid\b|\bpaying\b|\$\s?\d|\busd\b|\bper hour\b|/hr\b|"
    r"\bcontract\b|\bfreelanc\w*\b|\bgig\b|\bproject\b|\bmvp\b|\bquote\b|"
    r"\bproposal\b|\bbuild\b|\bfix\b|\bautomate\b|\bdeliverable\b",
    re.I,
)
ROLE_RE = re.compile(
    r"\b(?:developer|programmer|"
    r"(?:software|backend|back-end|frontend|front-end|full[- ]?stack|devops|ml|ai|"
    r"machine learning|data|platform|systems|cloud|api) engineer|"
    r"full[- ]?stack|front[- ]?end|back[- ]?end|"
    r"typescript|javascript|python|react|next\.?js|node(?:\.js)?|fastapi|django|"
    r"flask|postgres(?:ql)?|sql|mongodb|redis|"
    r"web ?app(?:lication)?|web ?developer|website|saas|api|"
    r"llm|rag|agentic|ai agent|gpt|openai|claude|mcp|machine learning|"
    r"data scien\w+|automation|scrap(?:er|ing)|chatbot|ai|ml)\b",
    re.I,
)
NONDEV_RE = re.compile(
    r"\b(?:content writer|copywriter|writer|editor|video editor|video editing|"
    r"video|graphic design\w*|designer|marketing|sales|telemarketer|salesperson|"
    r"customer support|virtual assistant|data entry|translator|voice actor|"
    r"social media|seo|accountant|recruiter|moderator|chatter|"
    r"growth(?: hacker| marketer| specialist)?|community manager|"
    r"lead generation|cold email|outreach specialist|appointment setter|sdr|"
    r"specialist|manager|coordinator|strategist|consultant)\b",
    re.I,
)
HARD_DEV_RE = re.compile(
    r"\b(?:developer|software engineer|programmer|full[- ]?stack|front[- ]?end|"
    r"back[- ]?end|react|next\.?js|node(?:\.js)?|python|typescript|javascript|"
    r"fastapi|django|postgres(?:ql)?|llm|rag|agentic|ai agent|machine learning|"
    r"data scien\w+|automation|scrap(?:er|ing)|chatbot|web ?developer|saas)\b",
    re.I,
)
JOB_RE = re.compile(
    r"\bfull[- ]time\b|\bpart[- ]time\b|\bsalary\b|\bbenefits\b|\bemployment\b|"
    r"\bper year\b|/year\b|\bannual\b|\bcompensation\b|\bequity\b|"
    r"\bapply (?:at|via|here|through)\b|"
    r"\bjob description\b|\bresponsibilities\b|\brequirements\b",
    re.I,
)
SEEKER_RE = re.compile(
    r"\blooking for (?:paid )?(?:work|a job|a role|a position|opportunit\w+|referral)\b|"
    r"\bopen to (?:work|opportunities|roles)\b|\bjob referral\b|\bhire me\b|"
    r"\bmy (?:cv|resume|portfolio)\b|"
    r"\bI(?:'m| am) (?:looking|seeking|searching) for\b|"
    r"\bI(?:'m| am) (?:a|an)\b.{0,50}\b(?:developer|engineer)\b.{0,80}"
    r"\b(?:looking|seeking|open to)\b",
    re.I,
)
NOISE_RE = re.compile(
    r"\bhas anyone (?:tried|used|heard|hired|worked)\b|\bis it worth\b|"
    r"\bworth \$?\d|\banyone (?:having )?luck\b|\bwhat do you think\b|"
    r"\bthoughts\?|\badvice (?:needed|wanted)\b",
    re.I,
)
CLIENT_RE = re.compile(
    r"\bbudget\b|\bfreelanc\w*\b|\bcontractor\b|\bmvp\b|\bquote\b|\bproposal\b|"
    r"\bscope\b|\bdeliverable\b|\bbuild (?:me|us|a|an)\b|\bfix\b|\bautomate\b",
    re.I,
)
SELLER_RE = re.compile(r"\[?\bfor\s*hire\b\]?", re.I)
LOW_QUALITY_RE = re.compile(
    r"\bunpaid\b|\bno budget\b|\bequity[- ]only\b|\brevenue[- ]share\b|"
    r"\bcommission[- ]only\b|\bvolunteer\b|\bfree (?:work|of charge)\b",
    re.I,
)
BUDGET_RE = re.compile(
    r"(?:budget[^\n.;]{0,40})|(?:\$\s?\d[\d,.]*\s?(?:k|m|/hr|/hour)?)|"
    r"(?:\d[\d,.]*\s?(?:usd|eur|gbp|pkr|inr|aed|cad|aud)\b)",
    re.I,
)

EMAIL_RE = re.compile(
    r"(?<![\w.+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)(?![\w.-])"
)
WA_LINK_RE = re.compile(r"wa\.me/(\+?\d[\d\s().-]{5,18})", re.I)
WA_MENTION_RE = re.compile(
    r"whats\s?app[^\n+@\d]{0,25}(\+?\d[\d\s().-]{6,18})", re.I
)
TG_RE = re.compile(
    r"(?:t\.me/([A-Za-z0-9_]{4,32})|telegram[^\n@]{0,20}@([A-Za-z0-9_]{4,32}))",
    re.I,
)

BAD_EMAIL_DOMAINS = {
    "reddit.com", "redditmail.com", "example.com", "example.org",
    "domain.com", "email.com", "yourdomain.com",
}

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
URL_SKIP_HOSTS = (
    "reddit.com", "redd.it", "redditmedia.com", "redditstatic.com",
    "imgur.com", "youtube.com", "youtu.be", "discord.gg", "t.me",
)

PROOF_RULES = [
    (
        r"\b(?:livekit|webrtc|video|stream|hls|real-?time)\b",
        "Built ZensZoom, a multi-tenant live-classroom platform: Next.js + async "
        "FastAPI, LiveKit SFU, HLS recording, Stripe billing.",
    ),
    (
        r"\b(?:stripe|payment|billing|subscription|checkout)\b",
        "Shipped Stripe/PayFast billing and subscription flows end to end, "
        "including webhooks.",
    ),
    (
        r"\b(?:fastapi|python|postgres|sqlalchemy|backend|back-end)\b",
        "Work daily in async FastAPI + PostgreSQL (SQLAlchemy 2, Alembic) on AWS "
        "EC2, with Docker and Terraform.",
    ),
    (
        r"\b(?:react|next\.?js|typescript|frontend|front-end|ui)\b",
        "Build production UI in React 19 / Next.js App Router with TypeScript, "
        "including data-heavy dashboards.",
    ),
    (
        r"\b(?:ai|ml|llm|rag|agent|gpt|openai|claude|mcp|automation)\b",
        "Ship AI-enabled product features with Claude Code in the loop — scoped, "
        "implemented, and reviewed like any other production change.",
    ),
    (
        r"\b(?:e-?commerce|shopify|store|product page)\b",
        "Shipped e-commerce features end to end, including product pages, "
        "variants, and order flows.",
    ),
]

SIGNATURE = (
    "Saim Saeed\n"
    "Full-stack engineer — TypeScript/React/Next.js, Python/FastAPI, AWS\n"
    "saeedsaim299@gmail.com | +92 324 1706744\n"
    "linkedin.com/in/saim-saeed-719a6a3a9 | github.com/Saim-u"
)
SIGNATURE_SHORT = (
    "Saim Saeed — saeedsaim299@gmail.com | "
    "linkedin.com/in/saim-saeed-719a6a3a9"
)


class FetcherStopped(RuntimeError):
    """Raised when Reddit keeps answering 429 after the one bounded retry."""


def _text(el) -> str:
    return (el.text or "") if el is not None else ""


def _parse_dt(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def _strip_html(raw: str) -> str:
    text = html.unescape(raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_rss(xml_text: str, subreddit: str) -> list:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    posts = []
    for entry in root.findall("a:entry", ATOM):
        link = entry.find("a:link", ATOM)
        url = (link.get("href") or "").split("?")[0] if link is not None else ""
        author = re.sub(r"^/?u/", "", _text(entry.find("a:author/a:name", ATOM)))
        published = _text(entry.find("a:published", ATOM)) or _text(
            entry.find("a:updated", ATOM)
        )
        raw_id = _text(entry.find("a:id", ATOM))
        post_id = raw_id.split("_", 1)[-1] if raw_id else hashlib.sha1(
            url.encode("utf-8")
        ).hexdigest()[:10]
        flair = " ".join(
            (cat.get("label") or cat.get("term") or "").strip()
            for cat in entry.findall("a:category", ATOM)
        ).strip()
        posts.append({
            "id": post_id,
            "subreddit": subreddit,
            "title": html.unescape(_text(entry.find("a:title", ATOM))).strip(),
            "body": _strip_html(_text(entry.find("a:content", ATOM))),
            "author": author,
            "permalink": url,
            "created": _parse_dt(published),
            "flair": flair,
            "source": "rss",
        })
    return posts


def _from_json(data: dict) -> dict:
    return {
        "id": data.get("id", ""),
        "subreddit": data.get("subreddit", ""),
        "title": html.unescape(data.get("title") or "").strip(),
        "body": _strip_html(data.get("selftext") or ""),
        "author": data.get("author", ""),
        "permalink": "https://www.reddit.com" + (data.get("permalink") or ""),
        "created": datetime.fromtimestamp(
            data.get("created_utc", 0), tz=timezone.utc
        ),
        "flair": data.get("link_flair_text") or "",
        "source": "oauth",
    }


class Fetcher:
    def __init__(self, source: str, delay: float, verbose: bool):
        if source == "auto":
            source = (
                "oauth"
                if os.environ.get("REDDIT_CLIENT_ID")
                and os.environ.get("REDDIT_CLIENT_SECRET")
                else "rss"
            )
        self.source = source
        self.delay = delay
        self.verbose = verbose
        self.token = None
        self.requests = 0
        self.stopped = False

    def _raw(self, url, params=None, data=None, headers=None):
        if params:
            joiner = "&" if "?" in url else "?"
            url = url + joiner + urllib.parse.urlencode(params)
        merged = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        if headers:
            merged.update(headers)
        return urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers=merged), timeout=30
        )

    def _sleep(self):
        time.sleep(self.delay + random.uniform(0, 1.5))

    def _get(self, url, params=None, data=None, headers=None) -> bytes:
        if self.stopped:
            raise FetcherStopped("skipped after an earlier rate limit")
        for attempt in (1, 2):
            try:
                response = self._raw(url, params, data, headers)
                body = response.read()
                self.requests += 1
                self._sleep()
                return body
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    retry_after = exc.headers.get("Retry-After", "")
                    wait = int(retry_after) if retry_after.isdigit() else 20
                    if attempt == 1 and wait <= 30:
                        print(f"  rate limited, waiting {wait}s ...")
                        time.sleep(wait)
                        continue
                    self.stopped = True
                    raise FetcherStopped(
                        "Reddit rate-limited this IP (429). Run later, lower "
                        "--limit, or set OAuth credentials — see outreach/README.md."
                    ) from exc
                if exc.code in (403, 404):
                    raise
                if attempt == 1:
                    time.sleep(2)
                    continue
                raise
            except urllib.error.URLError:
                if attempt == 1:
                    time.sleep(2)
                    continue
                raise
        raise RuntimeError("unreachable")

    def _ensure_token(self) -> str:
        if self.token:
            return self.token
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise SystemExit(
                "--source oauth needs REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
            )
        username = os.environ.get("REDDIT_USERNAME")
        password = os.environ.get("REDDIT_PASSWORD")
        if username and password:
            form = {
                "grant_type": "password",
                "username": username,
                "password": password,
            }
        else:
            form = {"grant_type": "client_credentials"}
        basic = base64.b64encode(
            f"{client_id}:{client_secret}".encode("utf-8")
        ).decode("ascii")
        body = self._get(
            "https://www.reddit.com/api/v1/access_token",
            data=urllib.parse.urlencode(form).encode("utf-8"),
            headers={
                "Authorization": "Basic " + basic,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        self.token = json.loads(body.decode("utf-8"))["access_token"]
        return self.token

    def fetch_new(self, subreddit: str, limit: int) -> list:
        if self.source == "oauth":
            body = self._get(
                f"https://oauth.reddit.com/r/{subreddit}/new",
                {"limit": limit, "raw_json": 1},
                headers={"Authorization": "Bearer " + self._ensure_token()},
            )
            payload = json.loads(body.decode("utf-8"))
            return [
                _from_json(child["data"])
                for child in payload.get("data", {}).get("children", [])
                if child.get("kind") == "t3"
            ]
        body = self._get(
            f"https://www.reddit.com/r/{subreddit}/new/.rss", {"limit": limit}
        )
        return parse_rss(body.decode("utf-8", "replace"), subreddit)

    def search(self, subreddit: str, query: str, limit: int) -> list:
        params = {
            "q": query, "restrict_sr": "on", "sort": "new",
            "t": "month", "limit": limit,
        }
        if self.source == "oauth":
            body = self._get(
                f"https://oauth.reddit.com/r/{subreddit}/search",
                dict(params, raw_json=1),
                headers={"Authorization": "Bearer " + self._ensure_token()},
            )
            payload = json.loads(body.decode("utf-8"))
            return [
                _from_json(child["data"])
                for child in payload.get("data", {}).get("children", [])
                if child.get("kind") == "t3"
            ]
        body = self._get(
            f"https://www.reddit.com/r/{subreddit}/search.rss", params
        )
        return parse_rss(body.decode("utf-8", "replace"), subreddit)


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00"):
        digits = digits[2:]
    if not 8 <= len(digits) <= 15:
        return ""
    return "+" + digits


def extract_emails(text: str) -> list:
    found = []
    for match in EMAIL_RE.finditer(text):
        email = match.group(1).strip(".,;:").lower()
        domain = email.rsplit("@", 1)[-1]
        if any(domain == bad or domain.endswith("." + bad) for bad in BAD_EMAIL_DOMAINS):
            continue
        if "noreply" in email or "no-reply" in email:
            continue
        if email not in found:
            found.append(email)
    return found[:2]


def extract_whatsapp(text: str) -> list:
    found = []
    for pattern in (WA_LINK_RE, WA_MENTION_RE):
        for match in pattern.finditer(text):
            number = normalize_phone(match.group(1))
            if number and number not in found:
                found.append(number)
    return found[:2]


def extract_telegram(text: str) -> list:
    found = []
    for match in TG_RE.finditer(text):
        handle = (match.group(1) or match.group(2) or "").strip()
        entry = "Telegram @" + handle
        if handle and entry not in found:
            found.append(entry)
    return found


def role_focus(title: str, body: str) -> str:
    for text in (title, body[:300]):
        lower = text.lower()
        if re.search(r"full[\s-]?stack", lower):
            return "full-stack"
        if re.search(
            r"\b(?:ai|ml|llm|rag|gpt|openai|claude|mcp|agentic|machine learning)\b",
            lower,
        ):
            return "AI/ML"
        if re.search(r"\b(?:n8n|automation|automate|scrap(?:er|ing)|workflow)\b", lower):
            return "automation"
        if re.search(
            r"\b(?:frontend|front-end|react|next\.?js|typescript|web app|website)\b",
            lower,
        ):
            return "web/frontend"
        if re.search(
            r"\b(?:backend|back-end|fastapi|django|python|node|api|postgres)\b", lower
        ):
            return "backend"
    return "software"


def budget_hint(text: str) -> str:
    match = BUDGET_RE.search(text)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(0)).strip(" ,.;:")[:60]


def apply_url(text: str) -> str:
    match = re.search(
        r"\bapply(?:\s+here|\s+now|\s+at)?\s*[:\-–]?\s*(https?://[^\s<>\"')\]]+)",
        text,
        re.I,
    )
    candidates = [match.group(1)] if match else []
    candidates += URL_RE.findall(text)
    for url in candidates:
        cleaned = url.rstrip(".,;:!?)]}'\"")
        host = urllib.parse.urlsplit(cleaned).netloc.lower()
        if not host:
            continue
        if any(host == skip or host.endswith("." + skip) for skip in URL_SKIP_HOSTS):
            continue
        return cleaned
    return ""


def proof_lines(text: str) -> list:
    picked = []
    for pattern, line in PROOF_RULES:
        if re.search(pattern, text, re.I) and line not in picked:
            picked.append(line)
    if not picked:
        picked = [PROOF_RULES[2][1], PROOF_RULES[3][1]]
    return picked[:2]


def contact_line(emails: list, numbers: list, others: list) -> str:
    parts = []
    if emails:
        parts.append("Email: " + ", ".join(emails))
    if numbers:
        parts.append("WhatsApp: " + ", ".join(numbers))
    if others:
        parts.append(", ".join(others))
    return " | ".join(parts) if parts else "Reddit DM only"


def evaluate(post: dict, now: datetime, days: int):
    if not post.get("id") or not post.get("title"):
        return None, "empty"
    author = (post.get("author") or "").lower()
    if author in {"", "[deleted]", "automoderator", "deleted", "removed"}:
        return None, "moderator"
    age = now - post["created"]
    if age > timedelta(days=days) or age < timedelta(days=-1):
        return None, "old"

    title = post["title"]
    body = post.get("body", "")[:2000]
    text = title + "\n" + body + "\n" + post.get("flair", "")
    if SELLER_RE.search(title) and not re.search(r"\bhiring\b", title, re.I):
        return None, "for_hire"
    if SEEKER_RE.search(title + "\n" + body[:800]):
        return None, "job_seeker"
    if NOISE_RE.search(title):
        return None, "noise"
    if LOW_QUALITY_RE.search(text):
        return None, "unpaid"

    if NONDEV_RE.search(title) and not HARD_DEV_RE.search(title):
        return None, "non_dev"
    title_role = ROLE_RE.search(title)
    if title_role:
        roles = ROLE_RE.findall(title + "\n" + body[:600])
    else:
        roles = ROLE_RE.findall(body[:600])
        if not roles:
            return None, "no_role"
    hiring = HIRING_RE.findall(text)
    buyer = BUYER_RE.findall(text)
    if not hiring and not buyer:
        return None, "no_signal"

    annual_title = (
        re.search(r"\$\s?\d{2,3}(?:[.,]\d+)?\s?k\b", title, re.I)
        and re.search(r"\[?\bhiring\b\]?|\brole\b|\bposition\b", title, re.I)
        and not re.search(
            r"\bbudget\b|\bproject\b|\bmvp\b|\bgig\b|\bfixed\b", title, re.I
        )
    )
    if JOB_RE.search(text) or annual_title:
        lead_type = "job"
    elif re.search(r"\[?\bhiring\b\]?", title, re.I) and not re.search(
        r"\bbudget\b|\bmvp\b|\bfreelanc|\bcontractor\b|\bquote\b|\bproposal\b",
        text,
        re.I,
    ):
        lead_type = "job"
    elif CLIENT_RE.search(text):
        lead_type = "client"
    elif re.search(r"\bhiring\b", title, re.I):
        lead_type = "job"
    else:
        lead_type = "client"

    emails = extract_emails(text)
    numbers = extract_whatsapp(text)
    others = extract_telegram(text)

    score = (
        2 * min(len({h.lower() for h in hiring}), 3)
        + 2 * min(len({r.lower() for r in roles}), 4)
        + min(len({b.lower() for b in buyer}), 3)
    )
    if emails or numbers:
        score += 2
    score = min(score, 99)

    signals = []
    if hiring:
        signals.append("hiring")
    if buyer:
        signals.append("buyer")
    lead = {
        "id": post["id"],
        "date_found": datetime.now().astimezone().strftime("%Y-%m-%d"),
        "lead_type": lead_type,
        "subreddit": post["subreddit"],
        "posted_date": post["created"].strftime("%Y-%m-%d"),
        "title": title,
        "author": post.get("author", ""),
        "role_focus": role_focus(title, body),
        "budget_hint": budget_hint(text),
        "contact_email": ", ".join(emails),
        "contact_whatsapp": ", ".join(numbers),
        "contact_other": ", ".join(["Reddit DM"] + others),
        "permalink": post["permalink"],
        "apply_url": apply_url(body),
        "score": score,
        "status": "new",
        "draft_file": "",
        "notes": ", ".join(signals) + (" + contact in post" if emails or numbers else ""),
        "_post": post,
        "_emails": emails,
        "_numbers": numbers,
        "_others": others,
    }
    return lead, "ok"


def load_seen_ids(path: Path) -> set:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["id"] for row in csv.DictReader(handle) if row.get("id")}


def append_rows(path: Path, rows: list):
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})


def render(template_name: str, values: dict) -> str:
    path = TEMPLATES / template_name
    if not path.exists():
        raise SystemExit(f"missing template: {path}")
    template = string.Template(path.read_text(encoding="utf-8"))
    return template.safe_substitute(values)


def slugify(value: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug[:limit].rstrip("-") or "lead")


def write_drafts(lead: dict) -> str:
    DRAFTS.mkdir(parents=True, exist_ok=True)
    base = (
        f"{lead['date_found']}_{lead['subreddit']}_"
        f"{slugify(lead['title'], 30)}_{lead['id'][:8]}"
    )
    post = lead["_post"]
    text = post["title"] + "\n" + post.get("body", "")
    role = lead["role_focus"]
    author_short = lead["author"]
    title_short = lead["title"]
    if len(title_short) > 110:
        title_short = title_short[:107].rstrip() + "..."

    if lead["lead_type"] == "job":
        opening = (
            f'I saw your post in r/{lead["subreddit"]} ("{title_short}") and '
            f"wanted to apply for the {role} role."
        )
        ask = (
            "If it's still open, I can send my CV plus a short walkthrough of "
            "two similar builds today."
        )
        subject = f"Application: {role} engineer — Saim Saeed"
        template = "job_reply.md"
    else:
        opening = (
            f'I saw your post in r/{lead["subreddit"]} ("{title_short}") — if '
            f"you still need help with the {role} work, I can take it."
        )
        ask = "If the project is still open, what's the deadline and budget range?"
        subject = f"{role} help for {title_short[:50]}"
        template = "client_pitch.md"

    values = {
        "title": lead["title"],
        "subreddit": lead["subreddit"],
        "author": lead["author"],
        "author_short": author_short,
        "permalink": lead["permalink"],
        "apply_url": lead.get("apply_url") or "not posted",
        "posted_date": lead["posted_date"],
        "contact_line": contact_line(
            lead["_emails"], lead["_numbers"], lead["_others"]
        ),
        "contact_email": lead["contact_email"],
        "role_focus": role,
        "budget_hint": lead["budget_hint"] or "not stated",
        "matched": lead["notes"],
        "opening": opening,
        "proofs": "\n".join("- " + line for line in proof_lines(text)),
        "ask": ask,
        "subject": subject,
        "email_greeting": "there",
        "signature": SIGNATURE,
        "signature_short": SIGNATURE_SHORT,
    }

    dm_path = DRAFTS / f"{base}_dm.md"
    if not dm_path.exists():
        dm_path.write_text(render(template, values), encoding="utf-8")

    written = [dm_path]
    if lead["_emails"]:
        email_path = DRAFTS / f"{base}_email.md"
        if not email_path.exists():
            email_path.write_text(render("cold_email.md", values), encoding="utf-8")
        written.append(email_path)
    if lead["_numbers"]:
        wa_path = DRAFTS / f"{base}_wa.md"
        if not wa_path.exists():
            wa_path.write_text(render("whatsapp.md", values), encoding="utf-8")
        written.append(wa_path)

    try:
        return str(written[0].relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(written[0])


def parse_subreddits(path: Path) -> list:
    entries = []
    seen = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        name = parts[0].removeprefix("r/").strip("/")
        mode = parts[1].lower() if len(parts) > 1 else "new"
        if mode not in ("new", "search"):
            mode = "new"
        key = (name.lower(), mode)
        if name and key not in seen:
            seen.add(key)
            entries.append((name, mode))
    return entries


def rotating_queries(count: int = 2) -> list:
    start = datetime.now(timezone.utc).timetuple().tm_yday % len(SEARCH_QUERIES)
    return [SEARCH_QUERIES[(start + i) % len(SEARCH_QUERIES)] for i in range(count)]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Find Reddit hiring/client leads and draft outreach."
    )
    parser.add_argument("--days", type=int, default=7,
                        help="only posts from the last N days (default 7)")
    parser.add_argument("--limit", type=int, default=50,
                        help="posts per feed request (default 50)")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="seconds between requests (default 3.0)")
    parser.add_argument("--source", choices=["auto", "rss", "oauth"], default="auto")
    parser.add_argument("--subs", type=Path, default=SUBS_FILE)
    parser.add_argument("--queries", nargs="*", default=None,
                        help="override the rotating search queries")
    parser.add_argument("--no-drafts", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not args.subs.exists():
        raise SystemExit(f"subreddit list not found: {args.subs}")
    sources = parse_subreddits(args.subs)
    if not sources:
        raise SystemExit("no subreddits configured")

    fetcher = Fetcher(args.source, args.delay, args.verbose)
    queries = args.queries or rotating_queries(
        2 if fetcher.source == "oauth" else 1
    )
    now = datetime.now(timezone.utc)

    print(f"Fetching {len(sources)} sources via {fetcher.source} ...")
    posts = []
    fetch_errors = []
    for name, mode in sources:
        try:
            if mode == "new":
                batch = fetcher.fetch_new(name, args.limit)
            else:
                batch = []
                for query in queries:
                    batch.extend(fetcher.search(name, query, args.limit))
            if args.verbose:
                print(f"  r/{name} ({mode}): {len(batch)} posts")
            posts.extend(batch)
        except FetcherStopped as exc:
            fetch_errors.append(f"r/{name}: {exc}")
            print(f"  r/{name}: stopped ({exc})")
            break
        except urllib.error.HTTPError as exc:
            fetch_errors.append(f"r/{name}: HTTP {exc.code}")
            print(f"  r/{name}: HTTP {exc.code} (skipped)")
            if exc.code == 403:
                continue
        except Exception as exc:  # noqa: BLE001 - one bad feed must not kill the run
            fetch_errors.append(f"r/{name}: {exc}")
            print(f"  r/{name}: error (skipped)")

    unique = {}
    for post in posts:
        unique.setdefault(post["id"], post)

    seen_ids = load_seen_ids(LEADS_CSV)
    new_leads = []
    skipped = {}
    for post in unique.values():
        lead, reason = evaluate(post, now, args.days)
        if lead is None:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        if lead["id"] in seen_ids:
            skipped["already_tracked"] = skipped.get("already_tracked", 0) + 1
            continue
        new_leads.append(lead)

    new_leads.sort(key=lambda item: (-item["score"], item["posted_date"]))
    jobs = sum(1 for lead in new_leads if lead["lead_type"] == "job")
    clients = len(new_leads) - jobs

    if not args.dry_run:
        for lead in new_leads:
            if not args.no_drafts:
                lead["draft_file"] = write_drafts(lead)
        append_rows(LEADS_CSV, new_leads)

    print()
    print(f"Reddit leads — {datetime.now().astimezone().strftime('%Y-%m-%d')}")
    print(
        f"Fetched {len(unique)} posts, {len(new_leads)} new "
        f"({jobs} job, {clients} client)."
    )
    if skipped:
        detail = ", ".join(f"{key}={value}" for key, value in sorted(skipped.items()))
        print(f"Skipped: {detail}")
    if fetch_errors:
        print(f"Source issues: {'; '.join(fetch_errors)}")
    if new_leads:
        print()
        for lead in new_leads[:10]:
            budget = f" [{lead['budget_hint']}]" if lead["budget_hint"] else ""
            contact = " +contact" if lead["contact_email"] or lead["contact_whatsapp"] else ""
            print(
                f"  [{lead['lead_type']}] r/{lead['subreddit']} — "
                f"{lead['title'][:70]}{budget} (score {lead['score']}{contact})"
            )
        print()
        print(f"CSV:     {LEADS_CSV.relative_to(ROOT)}")
        if not args.no_drafts:
            print(f"Drafts:  {DRAFTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
