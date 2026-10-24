"""Anti-invention guard: a tailor.yaml may only use facts from the master profile.

    python3 scripts/guard.py output/applications/<slug>/tailor.yaml

Exit 0 = clean, 2 = violations (printed). Used by render.py and the Claude Code hook.
Rules:
  - experience / bullet / project / achievement ids must exist in the profile
  - reworded CV text (bullets, summary, skills): every number and every technical term
    (a token with an uppercase letter or digit) must appear in the profile
  - cover letter, answers, outreach: terms may also come from the job posting, but
    numbers about the candidate must exist in the profile or the posting
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Capitalised English words that are not factual claims.
COMMON = set("""I I'm I've I'd A An The In At On For With As And But Or My Our Your We You It This That These
Those Dear Hello Hi Best Kind Regards Sincerely Thank Thanks Looking Having Building Built Designed Developed
Led Managed Operate Operated Own Owned Recover Restored Architected Maintain Maintained Run Ran Automated
Perform Performed Root-cause Integrated Optimised Optimized Monitored Trained Improved Executed Enhanced Drove
Hiring Team Manager Mr Ms Mrs Engineer Engineering Software DevOps Automation Working Student Master's Thesis
Germany German English Europe European EU Today Currently Previously Since
Yes No Prefer Monday Tuesday Wednesday Thursday Friday January February March April May June July August
September October November December Most What Why How When Where Which Who Whether If Also Both Each Every""".split())

try:
    ENGLISH = set(Path("/usr/share/dict/words").read_text().lower().split())
except OSError:
    ENGLISH = set()

TERM = re.compile(r"[A-Za-z][A-Za-z0-9+#./&'-]*[A-Za-z0-9+#]|[A-Za-z]")
NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z])")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower())


def flatten(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(flatten(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(flatten(v) for v in obj)
    return str(obj)


def has(term: str, corpus: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", corpus) is not None


def unknown(text: str, corpus: str, num_corpus: str | None = None) -> tuple[list[str], list[str]]:
    nums = [n for n in NUMBER.findall(text) if not has(n, num_corpus if num_corpus is not None else corpus)]
    terms = []
    for m in TERM.finditer(text):
        t = m.group().strip(".'-")
        if not t or t in COMMON or not (any(c.isupper() for c in t) or any(c.isdigit() for c in t)):
            continue
        sentence_start = re.search(r"(^|[.!?:]\s+|\n\s*)$", text[:m.start()]) is not None
        if sentence_start and t[1:].islower() and t.lower() in ENGLISH:
            continue  # an ordinary word capitalised only because it opens a sentence
        if not has(t, corpus):
            terms.append(t)
    return sorted(set(nums)), sorted(set(terms))


# Phrasing that reads as AI-written. Recruiters notice it, so tailored text may not use it.
AI_TELLS = re.compile(r"\b(" + "|".join([
    r"end[- ]to[- ]end", r"wired into", r"at the root", r"stress-free", r"invisible", r"exactly the",
    r"I'?d welcome the chance", r"I would welcome", r"seamless\w*", r"robust", r"leverag\w*", r"passionate",
    r"spearhead\w*", r"cutting-edge", r"delv\w+", r"thriv\w+", r"fast-paced", r"synerg\w*", r"holistic",
    r"deeply", r"truly", r"genuinely", r"excited to", r"I'?m drawn", r"resonat\w+", r"keen", r"paved road",
    r"track record", r"not just", r"more than just", r"testament", r"journey", r"landscape", r"realm",
    r"tapestry", r"elevat\w+", r"empower\w*", r"unlock\w*", r"navigat\w+", r"foster\w*", r"pivotal",
    r"crucial", r"I am writing to", r"align\w* (with|perfectly)", r"intersection of", r"game[- ]changer",
    r"in today'?s", r"meaningful", r"impactful", r"stand out", r"look(ing)? forward to the opportunity",
    r"bring (my|a) unique", r"I'?m confident", r"every single", r"world-class", r"state-of-the-art",
    r"rock-solid", r"architected", r"stabilis\w+", r"stabiliz\w+",
]) + r")\b", re.I)
BAD_PUNCT = {"—": "em dash", "–": "en dash", ";": "semicolon", "…": "ellipsis", "×": "times sign"}


def style_issues(field: str, text: str) -> list[str]:
    out = [f"{field}: {name} '{ch}'" for ch, name in BAD_PUNCT.items() if ch in (text or "")]
    out += [f"{field}: AI-sounding phrase '{m.group()}'" for m in AI_TELLS.finditer(text or "")]
    return out


def employer_keys(profile: dict) -> dict[str, list[str]]:
    """Names a sentence may use for each experience entry: `aliases` from the profile, else the company name."""
    keys = {}
    for e in profile["experience"]:
        names = e.get("aliases") or [re.sub(r"\b(gmbh|ag|se|ltd|limited|inc|private|pvt)\b\.?", "", e["company"], flags=re.I).strip()]
        keys[e["id"]] = [n.lower() for n in names if n]
    return keys


def misattributed(text: str, profile: dict) -> list[str]:
    """In a sentence that names exactly one employer, numbers must come from that employer's entry."""
    by_id = {e["id"]: norm(flatten(e)) for e in profile["experience"]}
    for e in profile["experience"]:  # an entry with `part_of` (e.g. a thesis) shares its parent's numbers
        if e.get("part_of") in by_id:
            by_id[e["part_of"]] += " " + by_id[e["id"]]
    parents = {e["id"]: e.get("part_of") for e in profile["experience"]}
    keys = employer_keys(profile)
    errors = []
    for sentence in re.split(r"(?<=[a-z0-9)%][.!?])\s+", text):
        low = sentence.lower()
        named = [k for k, ks in keys.items() if any(key in low for key in ks)]
        named = [k for k in named if parents.get(k) not in named]
        if len(named) != 1:
            continue
        wrong = [n for n in NUMBER.findall(sentence) if not has(n, by_id[named[0]])]
        if wrong:
            errors.append(f"numbers {wrong} are credited to {named[0]} but come from another role: \"{sentence.strip()[:90]}\"")
    return errors


def check(tailor_path: Path) -> list[str]:
    profile = yaml.safe_load((ROOT / "profile/master_profile.yaml").read_text())
    answers = yaml.safe_load((ROOT / "profile/answer_bank.yaml").read_text())
    t = yaml.safe_load(tailor_path.read_text())
    corpus = norm(flatten(profile) + " " + flatten(answers))

    import db
    job = db.connect().execute("SELECT * FROM jobs WHERE id=?", (t["job_id"],)).fetchone()
    if job is None:
        return [f"unknown job_id {t['job_id']}"]
    job_corpus = corpus + " " + norm(" ".join(job[k] or "" for k in ("description", "company", "title", "location")))

    errors = []
    exp = {e["id"]: e for e in profile["experience"]}
    for e in t.get("experience", []):
        if e["id"] not in exp:
            errors.append(f"experience '{e['id']}' is not in the profile")
            continue
        bullets = {b["id"]: b for b in exp[e["id"]]["bullets"]}
        for b in e.get("bullets", []):
            src = bullets.get(b["id"])
            if src is None:
                errors.append(f"bullet '{b['id']}' is not in experience '{e['id']}'")
                continue
            if src.get("metric") == "TODO" and "TODO" in str(b.get("text", "")):
                errors.append(f"bullet '{b['id']}' uses a TODO metric")
            if b.get("text"):
                nums, terms = unknown(b["text"], corpus, num_corpus=norm(src["text"]))
                if nums:
                    errors.append(f"bullet '{b['id']}': numbers not in profile: {nums}")
                if terms:
                    errors.append(f"bullet '{b['id']}': terms not in profile: {terms}")
    for key, pool in (("projects", profile.get("projects", [])), ("achievements", profile.get("achievements", []))):
        ids = {p["id"] for p in pool}
        errors += [f"{key[:-1]} '{i}' is not in the profile" for i in t.get(key, []) if i not in ids]

    for key in ("headline", "summary"):
        nums, terms = unknown(t.get(key, ""), corpus)
        if nums or terms:
            errors.append(f"{key}: not in profile: {nums + terms}")
    for g in t.get("skills", []):
        missing = [s for s in g["items"] if not has(norm(s), corpus)]
        if missing:
            errors.append(f"skills '{g['group']}': not in profile: {missing}")

    letter = flatten(t.get("cover_letter", {})) + " " + flatten(t.get("answers", {})) + " " + str(t.get("outreach", ""))
    errors += misattributed(letter + " " + t.get("summary", ""), profile)
    nums, terms = unknown(letter, job_corpus)
    if nums or terms:
        errors.append(f"cover letter/answers/outreach: not in profile or posting: {nums + terms}")
    errors += style_issues("headline", t.get("headline", "")) + style_issues("summary", t.get("summary", ""))
    for e in t.get("experience", []):
        for b in e.get("bullets", []):
            text = b.get("text") or next((x["text"] for x in exp.get(e["id"], {}).get("bullets", []) if x["id"] == b["id"]), "")
            errors += style_issues(f"bullet '{b['id']}'", text)
    for k, v in (t.get("cover_letter") or {}).items():
        errors += style_issues(f"cover letter {k}", flatten(v))
    errors += style_issues("answers", flatten(t.get("answers", {}))) + style_issues("outreach", str(t.get("outreach", "")))
    if "TODO" in letter:
        errors.append("cover letter/answers contain TODO")
    return errors


def main():
    errors = check(Path(sys.argv[1]))
    if errors:
        print("GUARD FAILED — remove or fix these (only use facts from master_profile.yaml):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(2)
    print("guard: clean")


if __name__ == "__main__":
    main()
