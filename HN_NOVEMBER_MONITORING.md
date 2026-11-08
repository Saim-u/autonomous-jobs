# Hacker News November 2026: "Who is Hiring?" Monitoring & Scrape Plan

> **Tracking Duration:** 1 November 2026 to 3 November 2026 (3 Days)  
> **Target Thread:** `Ask HN: Who is hiring? (November 2026)` (Goes live today around ~8:00 PM PKT / 15:00 UTC)  
> **Target Candidate:** Saim Saeed (Lahore, Pakistan) — Full-Stack Developer (TypeScript, React, Next.js, Python, FastAPI)

---

## 🎯 Strict Filtering Conditions (Laazmi Shartain)

Har aane wali job ko in 4 strict filters par check karna hai:

1. **Fully Remote Worldwide:**
   - 100% Remote, open globally / worldwide.
   - ❌ **Reject:** `Remote (US only)`, `Remote (North America)`, `Remote (EU only)`, `Remote (UK only)`, `US Citizenship Required`, `W2 only`.

2. **Experience Level (Junior / Mid / Intern):**
   - Sirf **Junior**, **Mid-level**, **Associate**, ya **Paid Internships** shamil karni hain.
   - Agar koi **Unpaid Internship** ho, to sirf tab shamil karni hai agar unhon ne explicitly likha ho ke **1, 2 ya 3 months baad paid hone / review ke chances hain**.
   - ❌ **Reject:** Strictly `Senior`, `Staff`, `Principal`, `Lead`, `Engineering Manager`, `Director`, `VP` only roles.

3. **Target Roles:**
   - **Backend Developer**
   - **Frontend Developer**
   - **Full-Stack Developer**
   - **Software Engineer (Web / AI App / Products)**
   - ❌ **Reject:** Pure Sales, Marketing, BizOps, Hardware, non-tech roles.

4. **Clean Results:**
   - In sharton ke ilawa koi faltu ya non-qualifying link nahi dena.

5. **Deduplication (Pehelay se applied roles):**
   - Kisi bhi naye result ko dene se pehle [APPLIED_JOBS.md](APPLIED_JOBS.md) aur [job_search_tracker.csv](job_search_tracker.csv) check karna laazmi hai. Jo companies/links pehle se listed hain, unhe dobara recommend nahi karna.

---

## 📅 3-Day Monitoring Schedule

| Day | Date | Action | Focus |
|---|---|---|---|
| **Day 1** | 1 Nov 2026 (~8:00 PM PKT) | Initial Scan | Naye thread ke launch hote hi pehli wave ke worldwide matching jobs scrape karna |
| **Day 2** | 2 Nov 2026 | Morning & Evening Scan | Day 2 par aane wali sab se zyada volume wali listings extract karna |
| **Day 3** | 3 Nov 2026 | Final Review & Catch-up | Late post karne wali companies aur follow-up roles verify karna |

---

## 🛠️ Automated Quick Check Script

Kisi bhi naye terminal session mein ye Python command chala kar check karein ke naya November thread aa gaya hai ya nahi aur matching jobs filter karein:

```powershell
python -c "
import urllib.request, json
url = 'https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&query=Who+is+hiring'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
for h in data.get('hits', [])[:3]:
    print(h['created_at'], h['objectID'], h['title'])
"
```
