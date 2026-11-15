# Outreach pipeline — Reddit leads + cold email

Finds people on Reddit who are **hiring** dev / AI / ML engineers or **buying**
software work, turns each new post into a tracked lead, and writes a ready-to-edit
message for every channel the poster published.

The job-application side of this repo (`/scrape`, `/rank`, `/apply`) stays the
system of record for formal applications. This folder is the direct-outreach
layer: replies to hiring posts, client pitches, and cold email.

## What it does

- Reads `outreach/subreddits.txt` (hiring boards via `/new`, buyer/AI boards via
  keyword search).
- Keeps posts that contain a hiring **or** buying signal **and** a dev/AI/ML role.
- Classifies each as `job` (full-time/salary language) or `client`
  (budget/project/MVP/freelance language).
- Extracts contact details **only from the post body**: email, WhatsApp/`wa.me`,
  Telegram. No profile scraping, no lookup services.
- Appends new leads to `outreach/leads.csv` and writes drafts to `outreach/drafts/`.
- Sends nothing. You review and send.

## Quick start

> **RSS is best-effort.** Reddit throttles anonymous RSS after a handful of
> requests, so a full-list run will often stop with a 429. If you plan to run
> this regularly, do the OAuth setup below first — two minutes, and the problem
> disappears.

```powershell
python outreach/reddit_leads.py --days 3 --limit 50
```

Output:

- `outreach/leads.csv` — one row per lead, editable `status` column
- `outreach/drafts/` — `<date>_<sub>_<slug>_<id>_dm.md` plus `_email.md` /
  `_wa.md` when that contact exists

Useful flags:

```powershell
python outreach/reddit_leads.py --dry-run          # preview, write nothing
python outreach/reddit_leads.py --verbose          # per-feed counts
python outreach/reddit_leads.py --no-drafts        # CSV only
python outreach/reddit_leads.py --queries "hiring developer" "build MVP"
```

Run it once or twice a day. Reddit moves fast; `--days 1` is enough for daily runs.

## Rate limits, and the OAuth upgrade

Reddit throttles unauthenticated RSS hard (HTTP 429). The default fetcher sleeps
3–4.5 s between requests and stops cleanly on a repeated 429 instead of hammering.
If that happens, either wait an hour and lower `--limit`, or switch to OAuth:

1. https://www.reddit.com/prefs/apps → **create another app** → type **script**.
2. Redirect URI: `http://localhost:8080` (unused, but required).
3. Set the credentials in the shell before running:

```powershell
$env:REDDIT_CLIENT_ID      = "your-app-id"
$env:REDDIT_CLIENT_SECRET  = "your-secret"
# optional, only if the app rejects client_credentials:
$env:REDDIT_USERNAME       = "your-reddit-username"
$env:REDDIT_PASSWORD       = "your-reddit-password"
python outreach/reddit_leads.py --source oauth
```

Set them once for the user account to make it permanent (User environment
variables in Windows settings), or re-export per session.

## Daily workflow (10–15 minutes)

1. Run the monitor.
2. Open `outreach/leads.csv`, sort by `score` (or the printed top 10).
3. For each new lead, open the draft, read the actual post, and personalise:
   name their stack, their deadline, or the outcome they described.
4. Choose the channel in this order:
   - **`apply_url` filled** → open it and apply there. Job-aggregator accounts
     (e.g. u/varworld) post on behalf of companies and do not read DMs.
   - **`contact_email` / `contact_whatsapp` filled** → send the matching draft;
     use it only because the poster published it for work inquiries.
   - **Otherwise** → Reddit DM or a comment reply from the `_dm` draft, and only
     if the post invites DMs/comments. Link: the `permalink` column.
5. Update `status`: `new` → `sent` → `replied` / `call` → `won` / `lost` / `skip`.
   Put the date in `notes` if you want a reminder.
6. Follow up **once** after 3–4 days, then stop. Two follow-ups max for email
   (template includes the second, then a final "no problem" note).

### Volume and deliverability guardrails

- 10–20 personalised Reddit messages/day, not more. New/low-karma accounts get
  flagged fast; spacing them out matters more than volume.
- Cold email from a warmed domain: 20–30/day for the first weeks, then scale
  slowly. Never blast a list from your main personal inbox.
- One message per lead. No "just bumping this" spam. Honour any "not interested"
  immediately and mark the lead `skip`.
- Keep a real signature and a one-line opt-out in email
  (`If this isn't relevant, reply "no" and I won't follow up.`). That is also
  what CAN-SPAM/GDPR-style rules expect.

## Contact rules

- The script reads contacts **from the post text only**. If someone didn't post
  an email or number, use Reddit DM — do not go looking for their address.
- Never message a number/email that was posted for a different purpose (e.g. a
  support address, a shared company inbox not related to the role).
- Job posts are applications — send the CV, not a sales pitch. Client posts are
  pitches — lead with the scope and a fixed-price offer.
- Public posts are not consent to bulk outreach. Personalisation and low volume
  are what keep this legitimate (and what actually gets replies).

## Cold email beyond Reddit

For agencies, startups, and companies that are not posting on Reddit:

1. Source the company from `/scrape` results, YC/Wellfound, or a target list.
2. Find a named person (founder, CTO, hiring manager) from the company site or
   LinkedIn — do not guess addresses.
3. Draft from `outreach/templates/cold_email.md`; keep it to one specific hook
   about their product and two proof bullets.
4. Log it in `leads.csv` too (`lead_type=client`, `permalink` = company/careers
   URL, `contact_email` = the published address).

Do not scrape addresses from profiles or buy lists. A small, researched list
beats a big, generic one and keeps the domain out of spam folders.

## Files

| Path | Purpose |
|---|---|
| `reddit_leads.py` | monitor + classifier + contact extractor + draft writer |
| `subreddits.txt` | sources; `<sub> [new\|search]` per line |
| `leads.csv` | lead tracker (append-only; `status` is yours to edit) |
| `drafts/` | generated messages, one file per channel (`_dm`, `_email`, `_wa`) |
| `templates/` | `job_reply.md`, `client_pitch.md`, `cold_email.md`, `whatsapp.md` |

### CSV columns

`id, date_found, lead_type, subreddit, posted_date, title, author, role_focus,
budget_hint, contact_email, contact_whatsapp, contact_other, permalink, score,
status, draft_file, notes`

`status` values: `new`, `sent`, `replied`, `call`, `won`, `lost`, `skip`.
Rows are appended, never rewritten, so manual edits survive. Delete a row if you
want the same post to surface again on the next run.

## Tuning

- Too many `[For Hire]` posts: `forhire` is noisy by design; the filter drops
  seller posts, but lower the `--days` window if volume is high.
- Too few AI leads: add subs to `subreddits.txt` (e.g. `OpenAI`, `ClaudeAI`,
  `n8n`, `SaaS`) and rerun with `--queries "hiring AI engineer"`.
- Thresholds live in `HIRING_RE`, `ROLE_RE`, `BUYER_RE`, `LOW_QUALITY_RE` at the
  top of `reddit_leads.py`.
