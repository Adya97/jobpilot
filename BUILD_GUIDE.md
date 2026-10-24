# JobPilot build guide (for Claude Code)

> **How to use this file:** open Claude Code in an empty folder (or in a clone of this repo) and say:
> *"Read BUILD_GUIDE.md and set up JobPilot for me. Ask me the interview questions first."*
> Claude then interviews you, builds or adapts every part below, and runs the pipeline with you.

**Claude, read this whole file before you start.** It is the full specification of a working,
approval-gated job application pipeline built only from Claude Code features (skills, subagents,
hooks, Claude in Chrome). It needs a Claude subscription and nothing else: no API key and no paid
services. Follow the order in [Build order](#9-build-order). Ask the interview questions in
[section 2](#2-interview-the-user-first) before writing any profile content, and never invent facts about the user.

---

## 1. What the system does

```
discover ──► score ──► tailor ──► APPROVE (human) ──► submit ──► follow up
 (scripts)  (subagents) (subagents   (dashboard)      (Claude in    (reminders)
                        + guard hook)                  Chrome)
```

1. **Discover**: a Python script pulls fresh postings from free public sources, filters them by
   title, location, freshness and blocked companies, removes duplicates, and stores them in SQLite.
2. **Score**: Claude scores each job 0–100 against the user's profile with a fixed rubric. With many
   jobs it spawns one subagent per batch of 15. Jobs at 65 or above go to `ready_to_tailor`.
3. **Tailor**: one subagent per job writes a `tailor.yaml`. It holds the CV content picked from the profile,
   a cover letter, form answers and a short recruiter note. A **PostToolUse hook** runs `guard.py`
   on every write and blocks invented facts, misattributed numbers and AI-sounding writing.
   `render.py` turns it into a LaTeX PDF CV and cover letter.
4. **Approve**: a local web dashboard shows each job with its PDFs. The user clicks Approve or Reject.
   **Nothing is submitted without status `approved`.**
5. **Submit**: Claude fills the application form in the user's Chrome (Claude in Chrome extension),
   uploads the PDFs, answers questions only from the answer bank, takes screenshots before and after
   submitting, and records the result.
6. **Follow up**: each applied job gets a follow-up date 7 days later.

What it deliberately does **not** do: solve CAPTCHAs, create accounts, enter passwords, tick
optional consents, send emails without asking, or exceed 15 submissions per day.

---

## 2. Interview the user first

Use the AskUserQuestion tool in rounds of up to 4 questions. Use the answers to fill
`profile/master_profile.yaml`, `profile/answer_bank.yaml`, `config/search.yaml` and the
"Candidate rules" section of `CLAUDE.md`. Ask follow-ups whenever something is unclear. Write
`TODO` for anything the user skips, and never fill a gap by guessing.

**Round 1: goal and scope**
- Which country or countries, and which cities? Is relocation OK?
- Which role families (for example Cloud/DevOps, AI/ML, QA, Backend, Data)? Which seniority?
- Work mode: onsite, hybrid or remote?
- How many applications per day? (Default 10–15, hard cap 15.)

**Round 2: sources and review**
- Which sources: national job boards (e.g. Bundesagentur für Arbeit in Germany), company ATS boards
  (Greenhouse, Lever, Ashby, SmartRecruiters, Personio), LinkedIn (search and "Top job picks")?
- Should LinkedIn Easy Apply go through the same approve-first flow? (Recommended: yes.)
- Only postings from the last 24 hours, or older ones too?
- Review style: approve every job on the dashboard (recommended), or approve in batches?

**Round 3: the CV**
- Ask the user for their current CV (PDF/DOCX path) and any new experience not in it yet.
  Read the files and extract facts into `master_profile.yaml`. Show the user the result.
- Ask for **real numbers** behind achievements. Never make metrics up. If a metric is unknown, leave it out.
- Which CV style? Default: "Jake's Resume" LaTeX style, no photo, experience before education,
  2 pages max. If the user has a reference CV they like, read it and match fonts and layout.
- Which links go in the header (LinkedIn, GitHub, portfolio)?

**Round 4: form answers (answer bank)**
- Work permit / visa status and whether sponsorship is needed. Permit expiry (optional).
- Salary expectation as a range, as a single number, and monthly. Notice period and earliest start date.
- Language levels (CEFR). Rule: never claim a level above what the user states.
- Years of experience, total and per key tool if they want.
- Optional equal-opportunity answers: gender, disability, nationality, citizenship, country of birth.
  Offer "Prefer not to say".
- Forms-only data: street address, postcode, date of birth. Never print these on the CV.
- Companies to never apply to (current employer, former employers).
- Consent policy: may Claude tick REQUIRED privacy/terms boxes on approved applications (ask per day)?
  Optional consents always stay unticked.

**Round 5: writing style**
- Show one sample cover letter paragraph and ask whether the tone fits.
- Default style rules (keep unless the user objects): short plain sentences, no em dashes, en dashes
  or semicolons, no stock phrases ("passionate", "leverage", "seamless", "I am writing to express").
  Users notice AI-sounding writing and dislike it.

---

## 3. Repository layout

```
CLAUDE.md                         hard rules + candidate rules (loaded every session)
BUILD_GUIDE.md                    this file
profile/
  master_profile.yaml             facts: personal, target, summaries per track, experience (ids!),
                                  education, projects, achievements, skills       [git-ignored]
  answer_bank.yaml                form answers                                    [git-ignored]
  *.example.yaml                  fictional templates
config/
  search.yaml                     title include/exclude, queries, LinkedIn settings, blocked_companies
  companies.yaml                  ATS board slugs to poll
scripts/
  demo.py                         smoke test with the fictional example profile
  db.py                           SQLite schema (jobs, applications, events, companies)
  discover.py                     collect → filter → dedupe → fetch descriptions → insert (--hours N)
  sources/common.py               Job dataclass, HTTP helpers (browser User-Agent), Germany matcher
  sources/arbeitsagentur.py       Bundesagentur für Arbeit public API
  sources/ats.py                  Greenhouse, Lever, Ashby, SmartRecruiters, Personio
  sources/linkedin.py             LinkedIn guest API + saved top-pick ids, 429 backoff
  jobs.py                         CLI: list / show / score / status / applied / stats
  guard.py                        anti-invention + attribution + style checker
  render.py                       tailor.yaml → LaTeX → PDF via tectonic
  dashboard.py                    local review UI on http://127.0.0.1:8765
  record_submit.sh                copy screenshots + mark applied
templates/
  preamble.tex, cv.tex, cover_letter.tex   Jinja2 with LaTeX-safe delimiters
  dashboard.html                  single-page review UI
.claude/
  settings.json                   PostToolUse hook registration
  hooks/guard_tailor.sh           runs guard.py when a tailor.yaml is written
  skills/discover|score-jobs|tailor|apply-approved/SKILL.md
data/jobs.db                      [git-ignored]
output/applications/<slug>/       tailor.yaml, cv.pdf, cover_letter.pdf, <First>_<Last>_CV.pdf,
                                  form.jpg, confirmation.jpg                       [git-ignored]
```

If you are working in a clone of this repo, most of this exists. Your job is then to fill the
profile, adjust config and rules, and verify. If you are building from scratch, create it all
using the specs below.

---

## 4. Component specs

### 4.1 Database (`scripts/db.py`)
- `jobs`: `id` (`source:external_id`), `source`, `url`, `apply_url`, `company`, `title`,
  `location`, `work_mode`, `description`, `posted_at`, `found_at`, `fingerprint` (UNIQUE,
  normalised company+title for cross-source dedupe), `score`, `score_reasons` (JSON), `track`,
  `status`, `easy_apply`.
- `applications`: `job_id`, `cv_path`, `cover_path`, `answers_json`, `outreach`, `applied_at`,
  `followup_due`, `notes`.
- `events`: audit log (`job_id`, `at`, `kind`, `detail`).
- `companies`: `name`, `ats`, `board`, `policy` (`normal|always|never`).
- Statuses: `to_score` → `ready_to_tailor` | `rejected_auto` → `ready_for_review` → `approved` |
  `rejected` → `applied` → `interview` | `offer` | `rejected`. Plus `needs_user` (account, CAPTCHA or
  site problem; the note holds the URL) and `closed` (posting removed).
- `connect()` creates tables and runs small migrations (`ALTER TABLE ... ADD COLUMN` when missing).

### 4.2 Discovery (`scripts/discover.py`, `scripts/sources/*`)
- All sources run in a thread pool. One broken board must never stop the run; record
  `board_errors` instead. LinkedIn search and top picks run serially in one task.
- Filters:
  - Title must contain an include term and no exclude term.
  - Location must be in the target country (remote-in-Europe allowed for ATS boards).
  - Postings must be fresh (`max_age_days`, or `--hours N` to override, which also narrows source queries).
  - Blocked companies are dropped (DB `policy='never'` plus `blocked_companies` in config).
  - Duplicates are dropped by `id` and by `fingerprint`.
- Fill in descriptions after filtering (details are a second request per job). Insert with `to_score`.
- Print JSON: `fetched`, `new_relevant`, `to_score`, `filtered`, `board_errors`.

Source notes. These were learned the hard way:
- **Bundesagentur für Arbeit (Germany):**
  - Search: `GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs?was=<q>&angebotsart=1&size=100&veroeffentlichtseit=<days>`.
  - Details: `/pc/v4/jobdetails/<base64(refnr)>`. Both need the header `X-API-Key: jobboerse-jobsuche`. The v4 search returns 403, so use v6 for search.
  - Apply link: the field `externeURL`. `allianzpartnerUrl` is only the portal homepage.
- **Greenhouse:**
  - `boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true`.
  - The HTML content is double-escaped: unescape it before stripping tags.
- **Lever:** `api.lever.co/v0/postings/<slug>?mode=json`.
- **Ashby:**
  - `api.ashbyhq.com/posting-api/job-board/<slug>`.
  - It rejects Python's default User-Agent, so always send a browser User-Agent.
- **SmartRecruiters:**
  - List: `api.smartrecruiters.com/v1/companies/<slug>/postings?country=de`.
  - Each posting's description needs a detail call.
- **Personio:**
  - `<slug>.jobs.personio.de/xml`.
  - Don't append the country to foreign offices.
- **LinkedIn, no login (guest API):**
  - Search: `linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=&location=&f_TPR=r86400&start=`.
  - Detail: `linkedin.com/jobs-guest/jobs/api/jobPosting/<id>`.
  - Rate limiting: it returns HTTP 429. Sleep about 2 s between calls, back off 15 s then 45 s, and never run calls in parallel.
  - Easy Apply detection: a job is Easy Apply when the detail HTML has no `apply-link-offsite`.
  - "Top job picks" are only visible when logged in. Collect their ids in Chrome from
    `/jobs/collections/recommended/` into `data/linkedin_top_picks.txt`, then fetch them through the guest API.

### 4.3 Scoring (`.claude/skills/score-jobs/SKILL.md`)
Rubric (start at 0):
- **Role fit (0–35):**
  - 35 for the core target roles.
  - Up to 20 for adjacent roles.
  - 0–5 for unrelated roles.
- **Stack overlap (0–30):** required tools that appear in the profile skills. Must-haves count more.
- **Seniority (0–15):**
  - 15 if it matches the user's years.
  - 7 for a "5+ years" ask.
  - 0 for 8+ years or staff level.
- **Location/mode (0–10):**
  - 10 in the target country.
  - 8 for a multi-country listing that includes it.
  - 0 if the location is really abroad.
- **Practical (0–10):**
  - Working language, a real product team (not a staffing agency), and salary near the target.

Caps and flags:
- Language required above the user's level: −15, flag `german_required` (or the equivalent for other languages).
- Posting written in another language: flag only, no penalty.
- PhD, research, internship or thesis: max 30.
- Actually based abroad: max 25.
- Agency: flag `agency` and take off practical points.

Save each score with `jobs.py score <id> <score> <track> '<json>'`, where the json is
`{summary, matches, gaps, flags}`. With more than 15 jobs, spawn one background subagent per 15 ids
and give each the rubric and profile path. Afterwards drop duplicates, such as the same text posted twice by an agency.

### 4.4 Tailoring (`.claude/skills/tailor/SKILL.md`)
- One subagent per job once there are more than 3. Each one reads the posting, the profile and a
  reference `tailor.yaml`, then writes `output/applications/<slug>/tailor.yaml`.
- `tailor.yaml` holds:
  - `job_id`, `track`, `headline`, `summary`.
  - `skills`: 5–7 groups of profile skills.
  - `experience`: every employer in profile order, as bullet ids. An optional `text:` rewords a bullet but keeps its facts and numbers.
  - `projects` and `achievements`: ids.
  - `cover_letter` with `greeting`, 4–5 `paragraphs` and `closing`.
  - `answers` with `why_this_role` and `why_company`.
  - `outreach`: under 400 characters.
- What the cover letter covers:
  - Why this role.
  - The strongest evidence from the two latest jobs.
  - One honest sentence on the main gap.
  - Work permit, location/relocation and notice period.
- `render.py <job_id>` runs the guard first. Then it renders CV and letter with Jinja2 into LaTeX and compiles with
  `tectonic`. It reads the page count from the tectonic log (the CV must be at most 2 pages), copies
  `<First>_<Last>_CV.pdf` / `_Cover_Letter.pdf` (recruiters see the filename), writes the
  `applications` row and sets `ready_for_review`.
- LaTeX tips:
  - Use Jinja delimiters `((* *))`, `((( )))` and `((= =))` so they don't clash with LaTeX braces.
  - Escape `& % $ # _ { } ~ ^ \` in a `tex` filter.
  - Load Latin Modern fonts by otf filename (`lmroman10-regular.otf`). Loading them by family name fails under tectonic.

### 4.5 The guard (`scripts/guard.py`) and hook
The guard is the most important safety piece. It runs as a PostToolUse hook on every `Write|Edit`.
The hook reads `tool_input.file_path` from stdin. For `*/tailor.yaml` it runs the guard, and exit
code 2 sends the findings back to Claude, which must fix the file. Checks:
1. Every experience, bullet, project and achievement id exists in the profile.
2. Reworded bullets: every number must be in that bullet's original text. Every technical term
   (a token with an uppercase letter or digit) must appear in the profile.
3. Summary, headline and skills: every term and skill must appear in the profile.
4. Cover letter, answers and outreach: terms may also come from the posting. Numbers must exist in
   the profile or the posting.
5. **Attribution:** in a sentence that names exactly one employer (by `aliases`), every number must
   come from that employer's entry. A `part_of` entry, such as a thesis at an employer, shares the
   parent's numbers. This catches "At Company A I cut costs by 40%" when the 40% belongs to Company B.
6. **Style:**
   - Banned punctuation: em dash, en dash, semicolon, ellipsis, ×.
   - A regex of AI-sounding phrases: leverage, seamless, passionate, robust, "end to end", "I am writing to", "not just", "track record", "excited to", and more.
7. Any `TODO` in the letter or answers fails the check.

Avoid these false positives:
- Sentence-initial capitalised English words. Check them against `/usr/share/dict/words`.
- Word-boundary matching: "EC2" must not match "2", and "CKA" must not match "CKAD".
- Sentence splitting must not break on initials like "M. Example".

### 4.6 Dashboard (`scripts/dashboard.py`, `templates/dashboard.html`)
- `python3 scripts/dashboard.py` serves on `127.0.0.1:8765`. It uses the standard library only.
- `GET /api/jobs`, `GET /api/stats`, `POST /api/jobs/<id>/status` with `{status, note}`.
- Columns follow the statuses. Each card shows score, flags, gaps and links to the PDFs.
  Approve, Reject and Needs-user buttons sit on each card. An "Applied today: n/15" counter is shown.
- Serve PDFs with `Cache-Control: no-store` and link them with `?v=<mtime>`, otherwise browsers show stale PDFs.

### 4.7 Submitting (`.claude/skills/apply-approved/SKILL.md`, Claude in Chrome)
**Flow per approved job:**
1. Open `apply_url` in a new tab and take a screenshot.
2. Fill the fields from the profile and the answer bank.
3. Upload the named PDFs.
4. Paste the cover letter into a text box when there's no upload field.
5. Read back every value.
6. Take a screenshot, then submit.
7. Take a screenshot of the confirmation.
8. Run `scripts/record_submit.sh <id> <form.jpg> <confirmation.jpg>`.

**Stop and mark `needs_user`** for a CAPTCHA, a login or account wall, an assessment, a question the profile can't answer truthfully, or a site error. If a site errors after submit, ask the user to check their email before retrying.

Browser lessons. Each of these cost a real mistake once:
- **Select by label, then verify.** Refs and coordinates go stale after uploads shift the page. Select radios
  and checkboxes with JS by matching label text and calling `label.click()`. Before submitting, read
  back every checked label and every text value and compare them with the intended answers.
- **Enumerate all inputs**, including `type=range` sliders, date and number inputs, and custom widgets.
  A missed salary slider was once submitted at its default of 1,000 EUR/month. Set sliders with the native value
  setter plus `input` and `change` events.
- **React-controlled inputs:** use the native value setter
  (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set`), then dispatch
  `input`, `change` and `blur`. Typing with the keyboard into some LinkedIn textareas drops characters, so set them directly and read them back.
- **React-select comboboxes (Greenhouse):** click the combobox with a real click, then click the option
  inside `#react-select-<id>-listbox` with JS.
- **Shadow DOM (SmartRecruiters):** walk the shadow roots and use the native setter with
  `{bubbles:true, composed:true}`. To upload, move the file input to `document.body`, upload, then move it back.
- **Upload buttons with no file input** (LinkedIn Easy Apply): patch `document.createElement` and
  `HTMLInputElement.prototype.click` to capture the dynamically created `input[type=file]`, append it to
  `document.body` and mark it `data-jp-captured`. Then upload with the file-upload tool.
- **Honeypots:** hidden fields with `tabIndex=-1`, `autocomplete=off`, off-screen or zero height stay empty.
- **Hidden duplicate submit buttons:** click the visible one.
- **Embedded forms:** a Greenhouse `iframe#grnhse_iframe` can be opened directly via its `src`.
- **Popups:** after closing tabs, call the tab-context tool again for fresh tab ids.
- **LinkedIn Easy Apply:**
  - Upload the tailored CV every time. Stored resumes are older versions.
  - Untick "Follow company" before submitting.
  - Answer screening questions only from the answer bank.
  - Wait 60–120 s between submissions, never do more than 5 in a row, and stop on any warning.
- **Cookie banners:** choose reject or necessary-only.
- **Consents:** tick required privacy/terms boxes only, and only after the user's yes for that day.
- **Job-board redirects:** Arbeitsagentur pages link out via "Externe Seite öffnen". Remove `target` and
  click, to stay in the same tab. SAP SuccessFactors, Workday and Avature portals almost always need an
  account, so mark those `needs_user`.

---

## 5. Claude Code features used

| Feature | Where |
|---|---|
| `CLAUDE.md` | Hard rules loaded every session |
| Skills | `discover`, `score-jobs`, `tailor`, `apply-approved` |
| Subagents | Scoring batches of 15, one tailoring subagent per job, run in background in parallel |
| Hooks | PostToolUse `Write|Edit` → `guard_tailor.sh` → `guard.py` (exit 2 = fix it) |
| Claude in Chrome | Filling and submitting forms in the user's real browser |
| AskUserQuestion | Interview, consent, and any unanswered form question |
| Background Bash | Long discovery runs (`discover.py --hours 24`) |
| Memory | Optional: save user preferences such as writing style and consent policy |
| `/loop` or scheduled runs | Optional: a daily discover → score → tailor run, with submission left manual |

---

## 6. Daily workflow (what the user says)

1. "Find jobs from the last 24 hours" → discover skill (`--hours 24`), then score-jobs.
2. "Tailor the best ones" → tailor skill (Claude picks the top ~10–12 and skips agencies,
   duplicates and roles with a strict language requirement unless the fit is strong).
3. The user reviews the PDFs on the dashboard and approves.
4. "I have approved them" → apply-approved skill. Claude reports what was submitted, what is waiting
   on the user (with reasons) and what was skipped.
5. A week later: follow up on `followup_due` jobs, by drafting emails for the user to send.

---

## 7. Setup commands

```bash
brew install tectonic                 # LaTeX engine (macOS). Linux: see tectonic-typesetting.github.io
python3 -m pip install -r requirements.txt
cp profile/master_profile.example.yaml profile/master_profile.yaml
cp profile/answer_bank.example.yaml profile/answer_bank.yaml
python3 scripts/db.py                 # create data/jobs.db
python3 scripts/discover.py --hours 24
python3 scripts/dashboard.py          # http://127.0.0.1:8765
```
You also need Chrome with the **Claude in Chrome** extension, signed in to the user's Claude account.
The user stays logged in to LinkedIn themselves. Claude never handles passwords.

---

## 8. Verification checklist

- `python3 scripts/demo.py` inserts a fictional job, runs the guard and renders the PDFs. Then edit
  `output/applications/example_demo-1/tailor.yaml` so a number is credited to the wrong employer
  (e.g. "At Northwind I lowered the AWS bill by 15%.") and confirm `scripts/guard.py` on it fails.
- `python3 scripts/render.py <job_id>` produces a 1–2 page CV and a 1-page letter. Open them and check fonts and layout.
- The dashboard lists jobs and Approve changes the status.
- On a real form, the first submission is done with the user watching.

---

## 9. Build order

1. Interview (section 2). Fill the profile and answer bank, and show them to the user for a check.
2. DB + discovery + config, then run discovery once and show the counts.
3. Scoring skill. Score a small batch and show the table.
4. Guard + hook + templates + render. Tailor one job and open the PDFs with the user.
   Iterate on style until the user is happy, since that's what most of the feedback is about.
5. Dashboard. The user approves the first batch.
6. Submit skill with Claude in Chrome. Do the first 1–2 together, then continue.
7. Commit after each step (git), with personal files git-ignored.
