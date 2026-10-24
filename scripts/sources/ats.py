"""Public careers-board APIs: Greenhouse, Lever, Ashby, SmartRecruiters, Personio."""
import xml.etree.ElementTree as ET

from .common import Job, get, get_json, strip_html, work_mode_of


def greenhouse(slug: str) -> list[Job]:
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    out = []
    for j in d.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        out.append(Job(source="greenhouse", external_id=f"{slug}-{j['id']}", url=j["absolute_url"],
                       apply_url=j["absolute_url"], company=j.get("company_name") or slug,
                       title=j["title"], location=loc, work_mode=work_mode_of(loc),
                       description=strip_html(j.get("content", "")), posted_at=j.get("updated_at", "")))
    return out


def lever(slug: str) -> list[Job]:
    out = []
    for j in get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        cat = j.get("categories") or {}
        loc = ", ".join(cat.get("allLocations") or [cat.get("location", "")])
        desc = j.get("descriptionPlain", "") + "\n\n" + "\n\n".join(
            f"{l['text']}\n{strip_html(l['content'])}" for l in j.get("lists", []))
        out.append(Job(source="lever", external_id=f"{slug}-{j['id']}", url=j["hostedUrl"],
                       apply_url=j.get("applyUrl", j["hostedUrl"]), company=slug, title=j["text"],
                       location=loc, work_mode=j.get("workplaceType", "") or work_mode_of(loc),
                       description=desc.strip()))
    return out


def ashby(slug: str) -> list[Job]:
    out = []
    for j in get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", []):
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations", [])]
        country = (j.get("address") or {}).get("postalAddress", {}).get("addressCountry", "")
        out.append(Job(source="ashby", external_id=f"{slug}-{j['id']}", url=j["jobUrl"],
                       apply_url=j.get("applyUrl", j["jobUrl"]), company=slug, title=j["title"],
                       location=", ".join(filter(None, locs + [country])),
                       work_mode=(j.get("workplaceType") or "").lower(),
                       description=j.get("descriptionPlain", ""), posted_at=j.get("publishedAt", "")))
    return out


def smartrecruiters(slug: str) -> list[Job]:
    out, offset = [], 0
    while True:
        d = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
                     f"?country=de&limit=100&offset={offset}")
        for j in d.get("content", []):
            loc = j.get("location") or {}
            out.append(Job(source="smartrecruiters", external_id=f"{slug}-{j['id']}",
                           url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                           company=(j.get("company") or {}).get("name", slug), title=j["name"],
                           location=f"{loc.get('city', '')}, Germany",
                           work_mode="remote" if loc.get("remote") else work_mode_of(loc.get("fullLocation", "")),
                           posted_at=j.get("releasedDate", ""), extra={"ref": j.get("ref", "")}))
        offset += 100
        if offset >= d.get("totalFound", 0) or offset >= 1000:
            return out


def smartrecruiters_description(job: Job) -> None:
    d = get_json(job.extra["ref"])
    sections = (d.get("jobAd") or {}).get("sections", {})
    job.description = "\n\n".join(strip_html(s.get("text", "")) for s in sections.values() if isinstance(s, dict))
    job.apply_url = d.get("applyUrl") or job.url


def personio(slug: str) -> list[Job]:
    root = ET.fromstring(get(f"https://{slug}.jobs.personio.de/xml?language=en"))
    out = []
    for p in root.iter("position"):
        pid = p.findtext("id")
        desc = "\n\n".join(f"{d.findtext('name', '')}\n{strip_html(d.findtext('value', ''))}"
                           for d in p.iter("jobDescription"))
        loc = p.findtext("office", "")
        out.append(Job(source="personio", external_id=f"{slug}-{pid}",
                       url=f"https://{slug}.jobs.personio.de/job/{pid}",
                       apply_url=f"https://{slug}.jobs.personio.de/job/{pid}#apply",
                       company=p.findtext("subcompany") or slug, title=p.findtext("name", ""),
                       location=loc,
                       work_mode=work_mode_of(loc), description=desc, posted_at=p.findtext("createdAt", "")))
    return out


BOARDS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby,
          "smartrecruiters": smartrecruiters, "personio": personio}
