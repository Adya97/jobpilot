"""Render a tailored application to PDF (after the guard passes).

    python3 scripts/render.py <job_id | application dir>

Reads output/applications/<slug>/tailor.yaml and writes cv.pdf and cover_letter.pdf next to it.
"""
import json
import shutil
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import db  # noqa: E402
import guard  # noqa: E402

TEX_ESCAPE = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
              "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
              "→": r"$\rightarrow$", "×": r"$\times$"}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def slug(job_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", job_id)


def app_dir(job_id: str) -> Path:
    return ROOT / "output" / "applications" / slug(job_id)


def fmt(ym) -> str:
    if ym == "present":
        return "Present"
    y, m = str(ym).split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


def tex(value) -> str:
    return "".join(TEX_ESCAPE.get(c, c) for c in str(value))


def to_pdf(tex_path: Path) -> None:
    r = subprocess.run(["tectonic", "--chatter", "minimal", "--keep-logs", tex_path.name], cwd=tex_path.parent,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        sys.exit(f"LaTeX failed for {tex_path}:\n{r.stderr[-3000:]}")


def page_count(pdf: Path) -> int:
    m = re.search(r"\((\d+) pages?", pdf.with_suffix(".log").read_text(errors="ignore"))
    return int(m.group(1)) if m else 0


def upload_stem(p: dict) -> str:
    """'Alex M. Example' -> 'Alex_Example' (first and last name), used for the files recruiters see."""
    parts = (p.get("display_name") or p["name"]).split()
    return re.sub(r"[^A-Za-z0-9_-]", "", "_".join([parts[0], parts[-1]] if len(parts) > 1 else parts))


def main():
    arg = sys.argv[1]
    d = Path(arg) if Path(arg).is_dir() else app_dir(arg)
    tailor_path = d / "tailor.yaml"
    errors = guard.check(tailor_path)
    if errors:
        print("GUARD FAILED:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        sys.exit(2)

    t = yaml.safe_load(tailor_path.read_text())
    profile = yaml.safe_load((ROOT / "profile/master_profile.yaml").read_text())
    p = profile["personal"]
    exp_by_id = {e["id"]: e for e in profile["experience"]}

    experience = []
    for e in t["experience"]:
        src = exp_by_id[e["id"]]
        by_id = {b["id"]: b["text"] for b in src["bullets"]}
        experience.append({
            "title": src["title"], "company": src["company"], "location": src["location"],
            "dates": f"{fmt(src['start'])} – {fmt(src['end'])}", "topic": src.get("topic"),
            "bullets": [b.get("text") or by_id[b["id"]] for b in e["bullets"]],
        })
    projects = [x for x in profile.get("projects", []) if x["id"] in t.get("projects", [])]
    achievements = [x for x in profile.get("achievements", []) if x["id"] in t.get("achievements", [])]

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), block_start_string="((*",
                      block_end_string="*))", variable_start_string="(((", variable_end_string=")))",
                      comment_start_string="((=", comment_end_string="=))", trim_blocks=True, lstrip_blocks=True)
    env.filters["tex"] = tex
    (d / "cv.tex").write_text(env.get_template("cv.tex").render(
        p=p, summary=t["summary"], skills=t["skills"], experience=experience,
        education=profile["education"], projects=projects, achievements=achievements))
    to_pdf(d / "cv.tex")

    conn = db.connect()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (t["job_id"],)).fetchone()
    if t.get("cover_letter"):
        (d / "cover_letter.tex").write_text(env.get_template("cover_letter.tex").render(
            p=p, letter=t["cover_letter"], company=job["company"], title=job["title"],
            today=date.today().strftime("%d %B %Y")))
        to_pdf(d / "cover_letter.tex")

    # recruiters see the uploaded filename, so keep named copies next to the working files
    stem = upload_stem(p)
    shutil.copy(d / "cv.pdf", d / f"{stem}_CV.pdf")
    if (d / "cover_letter.pdf").exists():
        shutil.copy(d / "cover_letter.pdf", d / f"{stem}_Cover_Letter.pdf")
    conn.execute("""INSERT INTO applications (job_id, cv_path, cover_path, answers_json, outreach)
                    VALUES (?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET cv_path=excluded.cv_path,
                    cover_path=excluded.cover_path, answers_json=excluded.answers_json, outreach=excluded.outreach""",
                 (t["job_id"], str(d / "cv.pdf"), str(d / "cover_letter.pdf"),
                  json.dumps(t.get("answers", {}), ensure_ascii=False), t.get("outreach", "")))
    conn.execute("UPDATE jobs SET status='ready_for_review' WHERE id=?", (t["job_id"],))
    conn.execute("INSERT INTO events (job_id, kind, detail) VALUES (?, 'tailored', ?)", (t["job_id"], str(d)))
    conn.commit()
    print(json.dumps({"cv": str(d / "cv.pdf"), "cv_pages": page_count(d / "cv.pdf"),
                      "cover_letter": str(d / "cover_letter.pdf")}))


if __name__ == "__main__":
    main()
