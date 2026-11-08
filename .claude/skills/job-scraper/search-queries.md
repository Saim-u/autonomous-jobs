# Search Queries for Job Scraper

<!-- Personalized for Saim Saeed: remote full-stack / frontend / backend roles. -->

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Shipped country-agnostic CLIs include `linkedin-search` and `freehire-search`; Danish demos and any skill you add with `/add-portal` are included the same way. You do **not** need a matching `site:` line below for those CLIs to run.

The `site:` query templates in this file are the **WebSearch fallback** — for portals without a CLI, company career pages, or when a CLI fails.

**Language scope:** write every query category in every language listed in your CLAUDE.md Languages table (typically 1-2, sometimes more). A posting requiring a language you have *not* declared, as a job condition, is excluded before scoring; a posting requiring a *higher level* than you declared in a language you *do* work in is flagged for your own judgment, not excluded — see `04-job-evaluation.md`'s Language Gate, the single source of truth for this rule. Translate each category's keywords rather than machine-translating word-for-word (e.g. "Frontend Developer" -> "Desarrollador Frontend", not a literal word-for-word translation) if you work in more than one language.

## Search Sites

Primary (remote-first market):
- **linkedin.com/jobs** - LinkedIn job listings; also covered by `linkedin-search` CLI. Use `--location "Remote"` + `--remote remote`, plus `--location "Pakistan"` for Lahore-based remote-friendly employers
- **freehire.me** - remote-friendly tech aggregator; covered by `freehire-search` CLI
- **Wellfound** (wellfound.com) - startup roles, many remote (WebSearch fallback)
- **We Work Remotely** (weworkremotely.com) - remote-only board (WebSearch fallback)

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for target remote-first companies (SaaS, fintech, developer tools, e-commerce, AI-enabled products)

## Query Categories

Queries are grouped by priority. Write **each category in every language from your Languages table** (see Language scope above). Combine each query with your location terms (e.g. your city, region, or metro area) where the site supports it.

**Organize by function, not job title.** The same underlying work carries different titles across companies and markets (a "Data Scientist" role at one employer may be posted as "Insights Analyst" or "Data Consultant" at another). Name each priority category after the function it covers, and list several plausible job titles as query variants within that category rather than betting an entire priority tier on one exact title string.

### Priority 1: Full-stack product engineering (primary direction)

These match your strongest and most desired career direction: TypeScript/React/Next.js plus Python/FastAPI, owning features end to end.

```
site:linkedin.com/jobs "full stack developer" remote
site:linkedin.com/jobs "full stack engineer" remote
site:linkedin.com/jobs "full-stack software engineer" remote
site:linkedin.com/jobs "Next.js developer" remote
site:linkedin.com/jobs "TypeScript" "React" "Python" remote
site:freehire.me "full stack" remote
site:weworkremotely.com "full stack" developer
site:linkedin.com/jobs "فل اسٹیک ڈویلپر" ریموٹ
site:rozee.pk "فل اسٹیک ڈویلپر" لاہور
```

### Priority 2: Frontend engineering

React/Next.js roles with performance and state-management depth.

```
site:linkedin.com/jobs "frontend engineer" remote
site:linkedin.com/jobs "frontend developer" "React" remote
site:linkedin.com/jobs "React developer" remote
site:linkedin.com/jobs "Next.js engineer" remote
site:freehire.me "frontend" React remote
site:wellfound.com "frontend engineer" remote
site:linkedin.com/jobs "فرنٹ اینڈ ڈویلپر" ریموٹ
site:rozee.pk "فرنٹ اینڈ ڈویلپر" لاہور
```

### Priority 3: Backend / platform engineering

Python/FastAPI and Node.js services, APIs, auth, and data layers.

```
site:linkedin.com/jobs "backend engineer" Python remote
site:linkedin.com/jobs "backend developer" "FastAPI" remote
site:linkedin.com/jobs "Python backend developer" remote
site:linkedin.com/jobs "Node.js developer" remote
site:freehire.me "backend" Python remote
site:linkedin.com/jobs "بیک اینڈ ڈویلپر" ریموٹ
site:rozee.pk "بیک اینڈ ڈویلپر" لاہور
```

### Priority 4: Adjacent and domain roles

Real-time media, SaaS platform, and infrastructure-adjacent roles where your LiveKit/WebRTC, Docker/Terraform, and multi-tenant SaaS experience applies.

```
site:linkedin.com/jobs "WebRTC" engineer remote
site:linkedin.com/jobs "real-time" "software engineer" remote
site:linkedin.com/jobs "video platform" engineer remote
site:linkedin.com/jobs "platform engineer" Docker AWS remote
site:linkedin.com/jobs "SaaS" "full stack" engineer remote
site:linkedin.com/jobs "ریموٹ" "سافٹ ویئر انجینئر"
```

## Location Filter

Based in Lahore, Pakistan; remote roles are preferred, and relocation is acceptable within Pakistan and abroad when the role requires it.

- **Remote (worldwide)** - acceptable, including employers without a Pakistan entity if they hire contractors
- **Remote within Europe / US time zones** - acceptable where async or overlap with PKT (UTC+5) is workable; he currently works with US clients
- **Lahore, Pakistan (on-site or hybrid)** - acceptable
- **On-site or hybrid elsewhere in Pakistan** - acceptable; he is willing to relocate (note the city)
- **On-site abroad** - acceptable when the employer offers visa/relocation support; flag the posting when sponsorship or right-to-work is unclear
- **"Remote" that hides a country-restricted location** - flag it: a posting that says remote but limits hiring to a country he cannot work from is not a match

## Language Filter

Your working languages and levels are in CLAUDE.md's Languages table. When filtering scraped results, apply `04-job-evaluation.md`'s Language Gate: a posting requiring a language you haven't declared at all is excluded; a posting requiring a higher level than you declared in a language you do work in is not excluded, flag it clearly instead (see `job-scraper/SKILL.md`'s Step 3 "Quick Fit Assessment" for how the flag surfaces in `/scrape` output). Postings simply *written* in a language you don't work in, that don't require it on the job, are fine.

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries
