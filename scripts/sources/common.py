import html
import json
import re
import urllib.request
from dataclasses import dataclass, field

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

GERMAN_PLACES = ("germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt",
                 "cologne", "köln", "stuttgart", "düsseldorf", "dusseldorf", "leipzig", "dresden",
                 "hannover", "nuremberg", "nürnberg", "bremen", "karlsruhe", "bonn", "essen",
                 "dortmund", "mannheim", "potsdam", "heidelberg", "darmstadt", "aachen", "kiel")


@dataclass
class Job:
    source: str
    external_id: str
    url: str
    company: str
    title: str
    location: str = ""
    apply_url: str = ""
    work_mode: str = ""
    description: str = ""
    posted_at: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.source}:{self.external_id}"


def get(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url: str, headers: dict | None = None):
    return json.loads(get(url, headers))


def strip_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s or "", flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n- ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def in_germany(location: str) -> bool:
    loc = (location or "").lower()
    return any(p in loc for p in GERMAN_PLACES)


def work_mode_of(text: str) -> str:
    t = (text or "").lower()
    if "remote" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    return ""
