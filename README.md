# JobPilot

An approval-gated job application pipeline built entirely with **Claude Code**: skills, subagents,
a guard hook and Claude in Chrome. It finds fresh postings, scores them against your profile,
writes a tailored CV and cover letter for each one, waits for you to approve them on a local
dashboard, and then fills in and submits the application forms in your own browser.

It only needs a Claude subscription: no API key and no paid services.

```
discover ──► score ──► tailor ──► APPROVE (you) ──► submit ──► follow up
```

## Hand it to Claude

The fastest way to set this up for yourself (or a friend):

1. Clone this repo and open Claude Code in it.
2. Say: **"Read BUILD_GUIDE.md and set up JobPilot for me. Ask me the interview questions first."**

Claude asks about your target roles, location, sources, CV, form answers and writing style. Then it
fills your profile and walks you through the first run. [`BUILD_GUIDE.md`](BUILD_GUIDE.md) is the
full specification, detailed enough to rebuild the whole system from an empty folder.

## Safety by design

- **Nothing is submitted without your approval** on the dashboard (status `approved`).
- **Facts only from your profile.** A PostToolUse hook runs `scripts/guard.py` on every tailored file and
  blocks:
  - invented tools or numbers,
  - numbers credited to the wrong employer,
  - AI-sounding phrasing (em dashes, "leverage", "passionate", ...).
- Claude never solves CAPTCHAs, creates accounts, enters passwords or ticks optional consents. Those
  jobs are marked `needs_user` instead.
- At most 15 submissions a day, with slow pacing on LinkedIn.

## Quick start

```bash
brew install tectonic                       # LaTeX engine for the PDFs
python3 -m pip install -r requirements.txt
python3 scripts/demo.py                     # renders a CV for a fictional person to check the setup
python3 scripts/discover.py --hours 24      # fetch postings from the last 24 hours
python3 scripts/dashboard.py                # review UI at http://127.0.0.1:8765
```

Then, in Claude Code: *"score the new jobs"*, *"tailor the best ones"*, approve on the dashboard,
*"submit the approved applications"*. You need Chrome with the Claude in Chrome extension for submitting.

Example output for the fictional profile: [`docs/example_cv.pdf`](docs/example_cv.pdf),
[`docs/example_cover_letter.pdf`](docs/example_cover_letter.pdf).

## Sources

- Bundesagentur für Arbeit (Germany's public job board API).
- Company boards on Greenhouse, Lever, Ashby, SmartRecruiters and Personio (`config/companies.yaml`).
- LinkedIn, through the public guest API, plus your "Top job picks".

The search is tuned for Germany and Cloud/DevOps, AI/ML and QA roles. Change `config/search.yaml` and the
profile `target` to fit your own search.

## Your data stays local

`profile/master_profile.yaml`, `profile/answer_bank.yaml`, `data/` and `output/` are git-ignored.
Start from the `*.example.yaml` templates, which describe a fictional person.

## Layout

See [`BUILD_GUIDE.md` §3](BUILD_GUIDE.md#3-repository-layout).
