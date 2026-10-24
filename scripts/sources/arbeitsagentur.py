"""Bundesagentur für Arbeit job search (free public API, fixed public key)."""
import base64
import urllib.parse

from .common import Job, get_json

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}


def search(cfg: dict) -> list[Job]:
    jobs = {}
    for q in cfg["queries"]:
        params = {"was": q, "angebotsart": 1, "size": 100,
                  "veroeffentlichtseit": cfg.get("published_within_days", 7)}
        if cfg.get("exclude_temp_agencies"):
            params["zeitarbeit"] = "false"
        if cfg.get("exclude_private_recruiters"):
            params["pav"] = "false"
        data = get_json(f"{BASE}/v6/jobs?{urllib.parse.urlencode(params)}", HEADERS)
        for r in data.get("ergebnisliste") or []:
            ref = r["referenznummer"]
            addr = (r.get("stellenlokationen") or [{}])[0].get("adresse", {})
            jobs[ref] = Job(
                source="arbeitsagentur", external_id=ref,
                url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}",
                company=r.get("firma", ""), title=r.get("stellenangebotsTitel", ""),
                location=f"{addr.get('ort', '')}, Germany",
                posted_at=r.get("datumErsteVeroeffentlichung", ""),
            )
    return list(jobs.values())


def fetch_description(job: Job) -> None:
    ref = base64.b64encode(job.external_id.encode()).decode()
    d = get_json(f"{BASE}/v4/jobdetails/{ref}", HEADERS)
    job.description = d.get("stellenangebotsBeschreibung", "")
    job.apply_url = d.get("externeURL") or d.get("externeUrl") or job.url  # allianzpartnerUrl is only the portal homepage
