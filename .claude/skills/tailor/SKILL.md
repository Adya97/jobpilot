---
name: tailor
description: Write a tailored CV, cover letter, form answers and recruiter note for jobs in ready_to_tailor, then render the PDFs. Use for "tailor", "prepare applications", or after scoring.
---

# Tailor applications

For each job (`python3 scripts/jobs.py list --status ready_to_tailor`), or one job id if given:

1. Read the posting in full (`python3 scripts/jobs.py show '<id>'`) and `profile/master_profile.yaml`.
   With more than 3 jobs, spawn one subagent per job, each with these instructions.
2. Write `output/applications/<slug>/tailor.yaml`. The slug is the job id with non `[A-Za-z0-9_-]` characters
   replaced by `_`. Use `output/applications/greenhouse_jetbrains-4966818101/tailor.yaml` as the reference format.
   - `headline` and `summary`: start from the track's summary in the profile and reorder it toward the job.
   - `skills`: 5–7 groups, most relevant first. Items must be skills listed in the profile.
   - `experience`: every employer, in profile order. Choose and order bullets by relevance:
     current role 5–7, previous role 3–5, thesis 2–4, older roles 1–2 each.
     Add `text:` only to reword a bullet toward the posting's language, keeping its facts and numbers.
   - `projects` and `achievements`: include only the relevant ones.
   - `cover_letter`: 4–5 short paragraphs. Cover why this role, the strongest matching evidence from
     the two most recent roles, one honest sentence on the main gap, then work permit, location and
     notice period (from the answer bank). No clichés and no "I am writing to express my interest".
   - `answers`: `why_this_role` and `why_company`, 2 sentences each.
   - `outreach`: a LinkedIn note to the hiring manager, under 400 characters.
   - Attribution: every number and achievement must be credited to the employer it belongs to in the profile
     (a number from one job must never appear next to another employer's name). Name the employer
     in the same sentence. The guard checks this using each experience entry's `aliases`.
   - Write like a person, not like AI. Use short, plain sentences and everyday verbs (built, fixed, run, set up).
     No em dashes, en dashes or semicolons in prose. No stock phrases: "end to end", "at the root", "wired into",
     "I'd welcome the chance", "seamless", "leverage", "passionate", "exactly the kind of", "not just X".
     End the letter simply, for example "I'm happy to talk whenever suits you." The guard blocks the full list.
3. A hook runs `scripts/guard.py` on every write. If it reports violations, remove the claim. Never add
   the missing fact to the profile to make the guard pass.
4. Run `python3 scripts/render.py '<id>'`. The CV must be 2 pages or fewer. If it is longer, drop the least
   relevant bullets.
5. Report each job with its CV and cover letter paths. Status is now `ready_for_review`.
