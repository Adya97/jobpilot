"""Smoke test with the fictional example profile: insert a demo job, then guard + render it.

    python3 scripts/demo.py

Uses profile/*.example.yaml only if your own profile files do not exist yet.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import db  # noqa: E402

JOB_ID = "example:demo-1"


def main():
    for name in ("master_profile", "answer_bank"):
        real, example = ROOT / f"profile/{name}.yaml", ROOT / f"profile/{name}.example.yaml"
        if not real.exists():
            shutil.copy(example, real)
            print(f"copied {example.name} -> {real.name} (replace it with your own facts)")
    conn = db.connect()
    conn.execute(
        """INSERT OR REPLACE INTO jobs (id, source, url, apply_url, company, title, location, description,
           fingerprint, status) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (JOB_ID, "example", "https://example.com/job", "https://example.com/job", "Acme Robotics",
         "Platform Engineer (m/f/d)", "Berlin, Germany",
         "We run Kubernetes on AWS and want a Platform Engineer for Helm, Terraform and GitHub Actions. "
         "English required, German a plus.", "demo-1", "ready_to_tailor"))
    conn.commit()
    d = ROOT / "output/applications/example_demo-1"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "examples/tailor.example.yaml", d / "tailor.yaml")
    subprocess.run([sys.executable, str(ROOT / "scripts/render.py"), JOB_ID], check=True)
    print(f"open {d}/cv.pdf and {d}/cover_letter.pdf")


if __name__ == "__main__":
    main()
