---
name: score-jobs
description: Score discovered jobs (status to_score) against the candidate's master profile and move them to ready_to_tailor or rejected_auto. Use after discovery, or when asked to score/rank/triage jobs.
---

# Score jobs

1. Read `profile/master_profile.yaml` once (skills, experience, target roles).
2. Fetch pending jobs: `python3 scripts/jobs.py list --status to_score --limit 15 --full`.
   With more than 15 pending, spawn one subagent per batch of 15, giving each this rubric and the profile.
3. For each job, score 0–100 with the rubric below, then save it:
   `python3 scripts/jobs.py score '<id>' <score> <track> '<json>'`
   with json `{"summary": "<one line>", "matches": [...], "gaps": [...], "flags": [...]}`.
   Jobs scoring ≥65 become `ready_to_tailor`. The rest become `rejected_auto`.
4. End with a table of id, company, title, score and track, best first.

## Rubric
Start at 0 and add points:
- **Role fit (0–35):** The core of the job is DevOps/Cloud/Platform/SRE, AI/ML/MLOps/GenAI engineering, or QA/test automation. Adjacent roles (data platform, release, infrastructure-heavy backend) get up to 20. Other roles (marketing, supplier quality, hardware test, network hardware) get 0–5.
- **Stack overlap (0–30):** Required tools that appear in the profile skills. Score must-haves higher than nice-to-haves.
- **Seniority (0–15):** The profile has roughly 4 years. Junior–mid or "2–5 years" gets 15. "5+ years" gets 7. "8+ years" or staff level gets 0.
- **Location/mode (0–10):** In Germany or remote-in-Germany gets 10. Multi-country listings that include a German city get 8. A Germany entry that is really abroad (e.g. "Timișoara, Germany") gets 0.
- **Practical (0–10):** English or German working language, a real product or engineering team (not a staffing agency), and salary near €65–75k when one is stated.

Hard caps:
- German C1+/fluent required → subtract 15 and flag `german_required` (the profile has B1 German).
- Posting written in German → flag `german_posting` (no penalty). The application stays in English.
- PhD or research-only roles → max 30.
- The job is actually based outside Germany → max 25.

Track: `devops`, `ai_ml` or `qa`, whichever summary and bullet set best fits the job.
Never invent profile facts. Gaps are things the job wants that the profile lacks.
