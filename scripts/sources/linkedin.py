"""LinkedIn jobs via the public guest endpoints (no login, so the user's account is never touched).

Top picks need the logged-in feed, so their job ids are collected in Chrome and saved to
data/linkedin_top_picks.txt; this module then reads each posting through the guest API.
"""
import html
import re
import time
import urllib.parse
from pathlib import Path

from .common import Job, get, strip_html

GUEST = "https://www.linkedin.com/jobs-guest/jobs/api"
PAUSE = 2.0  # seconds between requests


def _get(url: str) -> str:
    """GET with backoff: LinkedIn answers bursts with HTTP 429."""
    for wait in (0, 15, 45):
        time.sleep(wait)
        try:
            return get(url).decode()
        except Exception as e:
            if "429" not in str(e):
                raise
    raise RuntimeError(f"rate limited: {url}")


def _text(pattern: str, s: str) -> str:
    m = re.search(pattern, s, re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""


def search(cfg: dict) -> list[Job]:
    jobs = {}
    for q in cfg.get("queries", []):
        for start in range(0, cfg.get("max_per_query", 50), 10):
            params = {"keywords": q, "location": cfg.get("location", "Germany"),
                      "f_TPR": f"r{cfg.get('posted_within_hours', 24) * 3600}", "start": start}
            try:
                page = _get(f"{GUEST}/seeMoreJobPostings/search?{urllib.parse.urlencode(params)}")
            except RuntimeError:
                break  # skip the rest of this query, keep the others
            cards = re.split(r'(?=<div[^>]+data-entity-urn="urn:li:jobPosting:)', page)[1:]
            for c in cards:
                jid = re.search(r"urn:li:jobPosting:(\d+)", c).group(1)
                jobs[jid] = Job(source="linkedin", external_id=jid, url=f"https://www.linkedin.com/jobs/view/{jid}",
                                company=_text(r"base-search-card__subtitle[^>]*>(.*?)</h4>", c),
                                title=_text(r"base-search-card__title[^>]*>(.*?)</h3>", c),
                                location=_text(r"job-search-card__location[^>]*>(.*?)</span>", c) or "Germany")
            time.sleep(PAUSE)
            if len(cards) < 10:
                break
    return list(jobs.values())


def top_picks(path: Path) -> list[Job]:
    if not path.exists():
        return []
    ids = [i for i in re.split(r"[,\s]+", path.read_text()) if i.isdigit()]
    out = []
    for jid in ids:
        job = Job(source="linkedin", external_id=jid, url=f"https://www.linkedin.com/jobs/view/{jid}",
                  company="", title="")
        try:
            fetch_description(job)
        except Exception:
            continue
        out.append(job)
        time.sleep(PAUSE)
    return out


def fetch_description(job: Job) -> None:
    s = _get(f"{GUEST}/jobPosting/{job.external_id}")
    job.title = job.title or _text(r"<h2[^>]*top-card-layout__title[^>]*>(.*?)</h2>", s)
    job.company = job.company or _text(r"topcard__org-name-link[^>]*>(.*?)</a>", s)
    loc = _text(r"topcard__flavor--bullet[^>]*>(.*?)</span>", s)
    if loc:
        job.location = loc if "germany" in loc.lower() else f"{loc}, Germany"
    m = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", s, re.S)
    job.description = strip_html(m.group(1)) if m else ""
    job.extra["easy_apply"] = "apply-link-offsite" not in s
    job.apply_url = job.url
