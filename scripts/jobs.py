"""Small CLI over the jobs DB, used by skills.

    python3 scripts/jobs.py list --status to_score [--limit 20] [--full]
    python3 scripts/jobs.py show <job_id>
    python3 scripts/jobs.py score <job_id> <0-100> <devops|ai_ml|qa> '<reasons json>'
    python3 scripts/jobs.py status <job_id> <new_status> [note]
    python3 scripts/jobs.py applied <job_id>     # only works for approved jobs
    python3 scripts/jobs.py stats
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

READY_THRESHOLD = 65
DESC_LIMIT = 6000


def row_dict(r, full=False):
    d = dict(r)
    if not full:
        d.pop("description", None)
    elif d.get("description"):
        d["description"] = d["description"][:DESC_LIMIT]
    return d


def main(argv):
    conn = db.connect()
    cmd = argv[0] if argv else "stats"
    if cmd == "list":
        status = argv[argv.index("--status") + 1] if "--status" in argv else "to_score"
        limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 50
        rows = conn.execute("SELECT * FROM jobs WHERE status=? ORDER BY score DESC, found_at LIMIT ?",
                            (status, limit))
        print(json.dumps([row_dict(r, "--full" in argv) for r in rows], indent=1, ensure_ascii=False))
    elif cmd == "show":
        print(json.dumps(row_dict(conn.execute("SELECT * FROM jobs WHERE id=?", (argv[1],)).fetchone(), True),
                         indent=1, ensure_ascii=False))
    elif cmd == "score":
        job_id, score, track, reasons = argv[1], int(argv[2]), argv[3], json.loads(argv[4])
        status = "ready_to_tailor" if score >= READY_THRESHOLD else "rejected_auto"
        conn.execute("UPDATE jobs SET score=?, track=?, score_reasons=?, status=? WHERE id=?",
                     (score, track, json.dumps(reasons, ensure_ascii=False), status, job_id))
        conn.execute("INSERT INTO events (job_id, kind, detail) VALUES (?, 'scored', ?)", (job_id, f"{score} {status}"))
        conn.commit()
        print(f"{job_id}: {score} -> {status}")
    elif cmd == "status":
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (argv[2], argv[1]))
        conn.execute("INSERT INTO events (job_id, kind, detail) VALUES (?, 'status', ?)",
                     (argv[1], " ".join(argv[2:])))
        conn.commit()
        print(f"{argv[1]} -> {argv[2]}")
    elif cmd == "applied":
        job = conn.execute("SELECT status FROM jobs WHERE id=?", (argv[1],)).fetchone()
        if job is None or job["status"] != "approved":
            sys.exit(f"{argv[1]} is not approved; refusing to mark it applied")
        conn.execute("UPDATE jobs SET status='applied' WHERE id=?", (argv[1],))
        conn.execute("""UPDATE applications SET applied_at=datetime('now'), followup_due=date('now','+7 days')
                        WHERE job_id=?""", (argv[1],))
        conn.execute("INSERT INTO events (job_id, kind, detail) VALUES (?, 'applied', '')", (argv[1],))
        conn.commit()
        print(f"{argv[1]} -> applied (follow up in 7 days)")
    elif cmd == "stats":
        print(json.dumps(dict(conn.execute("SELECT status, count(*) FROM jobs GROUP BY status").fetchall())))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
