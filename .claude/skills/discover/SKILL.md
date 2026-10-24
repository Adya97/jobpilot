---
name: discover
description: Run job discovery across Arbeitsagentur and all watchlisted company boards, then score the new jobs. Use for "find jobs", "run discovery", or the daily pipeline run.
---

# Discover

1. Run `python3 scripts/discover.py` (add `--hours 24` for only the last day's postings). It prints fetched / new_relevant / to_score / filtered and any board errors.
2. If a board errors two runs in a row, report it. The slug has probably changed; check the company's careers page.
3. If `to_score > 0`, run the `score-jobs` skill.
4. Report: new jobs found, how many reached `ready_to_tailor`, and the top 5 by score.

Search terms and title filters live in `config/search.yaml`. Companies live in `config/companies.yaml`.
To add a company, find its ATS from the careers-page URL and add the slug under that ATS.
