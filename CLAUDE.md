# JobPilot: approval-gated job applications with Claude Code

Pipeline: discover → score → tailor → approve (human, on the dashboard) → submit → follow up.

## Hard rules
- **Never invent facts.** CVs, cover letters and form answers may only use content from
  `profile/master_profile.yaml` and `profile/answer_bank.yaml`. Selecting, reordering and
  rewording is fine. New employers, tools, metrics or achievements are not.
- Never use a profile entry whose value is `TODO`. If a form needs one, stop and ask.
- **Never submit an application without explicit approval** (status `approved` in the DB).
- Max 15 submissions per day. On LinkedIn, act slowly and stop on any CAPTCHA or warning.
- Never solve CAPTCHAs, create accounts or enter passwords for the user. Mark the job `needs_user`.
- Tick only the consent boxes a form REQUIRES, and only after the user has said yes for that day.
  Optional consents (marketing, talent pool, data retention, newsletters) stay unticked.
- Never send emails or messages on the user's behalf without asking first.

## Candidate rules (edit these for your own situation)
- Language: German level is B1. Apply to English and German postings, including ones asking
  for fluent German. CVs and cover letters stay in English. Never claim German above B1.
- Country: Germany only. The candidate has an EU Blue Card, so no sponsorship is needed.
- Never apply to the companies in `config/search.yaml` → `blocked_companies` (e.g. the current employer).
- Target roles and seniority: see `target` in `profile/master_profile.yaml`.

## Layout
- `profile/`: master profile + answer bank (source of truth, git-ignored; start from the `.example.yaml` files)
- `config/`: search terms, title filters, blocked companies, company watchlist
- `data/jobs.db`: SQLite with jobs, applications and events (git-ignored)
- `output/applications/<job_id>/`: tailored CV PDF, cover letter, screenshots (git-ignored)
- `scripts/`: Python helpers (discovery, DB, guard, rendering, dashboard)
- `templates/`: LaTeX CV and cover letter ("Jake's Resume" style), dashboard HTML
- `.claude/skills/`: one skill per pipeline stage. `.claude/hooks/`: guard hook on every tailor.yaml
