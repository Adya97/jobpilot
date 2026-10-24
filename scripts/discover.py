"""Discovery: pull jobs from every source, apply hard filters, store new ones.

    python3 scripts/discover.py            # all sources
    python3 scripts/discover.py --only greenhouse,ashby
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import db  # noqa: E402
from sources import arbeitsagentur, ats, linkedin  # noqa: E402
from sources.common import Job, in_germany  # noqa: E402

SEARCH = yaml.safe_load((ROOT / "config/search.yaml").read_text())
COMPANIES = yaml.safe_load((ROOT / "config/companies.yaml").read_text())


def _pattern(words):
    return re.compile(r"(?<![a-z])(" + "|".join(re.escape(w) for w in words) + r")(?![a-z])", re.I)


TITLE_IN = _pattern(SEARCH["title_include"])
TITLE_OUT = _pattern(SEARCH["title_exclude"])
EUROPE = re.compile(r"\b(europe|emea|eu|dach|cet)\b", re.I)

DE_WORDS = set("und der die das mit für wir sie ist von zu auf ihre unsere eine einen sowie bei".split())
EN_WORDS = set("and the with for we you is of to our your an as at this will".split())
GERMAN_REQUIRED = re.compile(
    r"(fluent|fluency|business[- ]fluent|native|excellent|very good|strong|proficien\w*|good command|C1|C2|B2)"
    r"[^.\n]{0,40}\bGerman\b(?![^.\n]{0,40}(plus|advantage|nice|bonus|preferred|beneficial|not required))"
    r"|\bGerman\b[^.\n]{0,25}\b(C1|C2|B2|required|mandatory|is a must|must)\b"
    r"|(verhandlungssicher|fließend)\w*[^.\n]{0,20}Deutsch|Deutsch\w*[^.\n]{0,30}(verhandlungssicher|fließend|C1|C2)",
    re.I)


def fingerprint(job: Job) -> str:
    company = re.sub(r"\b(gmbh|ag|se|kg|co|inc|ltd|group|deutschland|germany)\b|[^a-z0-9]", "", job.company.lower())
    title = re.sub(r"\((m|f|w|d|x|div|all|gn)[^)]*\)|[^a-z0-9]", "", job.title.lower())
    return f"{company}|{title}"


def title_ok(title: str) -> bool:
    return bool(TITLE_IN.search(title)) and not TITLE_OUT.search(title)


def location_ok(job: Job) -> bool:
    if job.source in ("arbeitsagentur", "smartrecruiters", "linkedin"):
        return True  # queried for Germany already
    if in_germany(job.location):
        return True
    remote = job.work_mode == "remote" or "remote" in job.location.lower()
    return remote and bool(EUROPE.search(job.location))


MAX_AGE = timedelta(days=SEARCH["max_age_days"])


def fresh(job: Job) -> bool:
    if not job.posted_at:
        return True
    try:
        posted = datetime.fromisoformat(job.posted_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    return posted >= datetime.now(timezone.utc) - MAX_AGE


def language_verdict(desc: str) -> str | None:
    words = re.findall(r"[a-zäöüß]+", desc.lower())
    de, en = sum(w in DE_WORDS for w in words), sum(w in EN_WORDS for w in words)
    if de > en:
        return "german_posting"
    if GERMAN_REQUIRED.search(desc):
        return "german_required"
    return None


def collect(only: set[str] | None) -> tuple[list[Job], dict]:
    tasks = []
    if not only or "arbeitsagentur" in only:
        tasks.append(("arbeitsagentur", "*", lambda: arbeitsagentur.search(SEARCH["arbeitsagentur"])))
    if not only or "linkedin" in only:
        li = SEARCH.get("linkedin", {})
        # one task, so search and top picks never hit LinkedIn at the same time
        tasks.append(("linkedin", "*", lambda: linkedin.search(li) + linkedin.top_picks(ROOT / li.get("top_picks_file", "x"))))
    for board, slugs in COMPANIES.items():
        if only and board not in only:
            continue
        for slug in slugs or []:
            tasks.append((board, slug, lambda b=board, s=slug: ats.BOARDS[b](s)))
    jobs, stats = [], {}
    with cf.ThreadPoolExecutor(12) as ex:
        futures = {ex.submit(fn): (b, s) for b, s, fn in tasks}
        for f in cf.as_completed(futures):
            b, s = futures[f]
            try:
                got = f.result()
                jobs += got
                stats[f"{b}:{s}"] = len(got)
            except Exception as e:  # one broken board must not stop the run
                stats[f"{b}:{s}"] = f"error: {e}"
    return jobs, stats


def fill_description(job: Job) -> None:
    if job.description:
        return
    if job.source == "arbeitsagentur":
        arbeitsagentur.fetch_description(job)
    elif job.source == "smartrecruiters":
        ats.smartrecruiters_description(job)
    elif job.source == "linkedin":
        linkedin.fetch_description(job)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated sources")
    ap.add_argument("--hours", type=int, help="only postings from the last N hours")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    if args.hours:
        global MAX_AGE
        MAX_AGE = timedelta(hours=args.hours)
        SEARCH["arbeitsagentur"]["published_within_days"] = max(1, -(-args.hours // 24))
        SEARCH.setdefault("linkedin", {})["posted_within_hours"] = args.hours

    conn = db.connect()
    known_ids = {r[0] for r in conn.execute("SELECT id FROM jobs")}
    known_fp = {r[0] for r in conn.execute("SELECT fingerprint FROM jobs")}
    blocked = {r[0].lower() for r in conn.execute("SELECT name FROM companies WHERE policy='never'")}
    blocked |= {c.lower() for c in SEARCH.get("blocked_companies", [])}

    raw, stats = collect(only)
    candidates, seen = [], set()
    for j in raw:
        fp = fingerprint(j)
        if j.id in known_ids or fp in known_fp or fp in seen:
            continue
        if any(b.split()[0] in j.company.lower() for b in blocked):
            continue
        if title_ok(j.title) and location_ok(j) and fresh(j):
            seen.add(fp)
            candidates.append((j, fp))

    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda c: _safe(fill_description, c[0]), candidates))

    counts = {"to_score": 0, "filtered": 0}
    for j, fp in candidates:
        reason = "no_description" if not j.description else (None if SEARCH.get("allow_german") else language_verdict(j.description))
        status = "filtered" if reason else "to_score"
        counts[status] += 1
        conn.execute(
            """INSERT OR IGNORE INTO jobs (id, source, url, apply_url, company, title, location, work_mode,
               description, posted_at, fingerprint, status, score_reasons, easy_apply)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (j.id, j.source, j.url, j.apply_url or j.url, j.company, j.title, j.location, j.work_mode,
             j.description, j.posted_at, fp, status, json.dumps({"filter": reason}) if reason else None,
             j.extra.get("easy_apply")))
        conn.execute("INSERT INTO events (job_id, kind, detail) VALUES (?, 'discovered', ?)", (j.id, status))
    conn.commit()

    errors = {k: v for k, v in stats.items() if isinstance(v, str)}
    print(json.dumps({"fetched": len(raw), "new_relevant": len(candidates), **counts,
                      "board_errors": errors}, indent=2))


def _safe(fn, job):
    try:
        fn(job)
    except Exception:
        pass


if __name__ == "__main__":
    main()
