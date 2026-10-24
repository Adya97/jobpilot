"""Local approval dashboard (localhost only).

    python3 scripts/dashboard.py      # http://127.0.0.1:8765
"""
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import db  # noqa: E402

PORT = 8765
APPS = ROOT / "output" / "applications"
PAGE = ROOT / "templates" / "dashboard.html"
# Status changes a person may make from the dashboard.
ALLOWED = {"approved", "rejected", "ready_for_review", "applied", "interview", "offer", "closed"}


def slug(job_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", job_id)


def jobs(status: str | None):
    conn = db.connect()
    q = """SELECT j.id, j.company, j.title, j.location, j.work_mode, j.url, j.apply_url, j.source, j.score,
                  j.track, j.score_reasons, j.status, j.found_at, a.answers_json, a.outreach, a.applied_at
           FROM jobs j LEFT JOIN applications a ON a.job_id = j.id"""
    args = ()
    if status and status != "all":
        q += " WHERE j.status = ?"
        args = (status,)
    else:
        q += " WHERE j.status NOT IN ('filtered')"
    out = []
    for r in conn.execute(q + " ORDER BY j.score DESC, j.found_at DESC", args):
        d = dict(r)
        d["reasons"] = json.loads(d.pop("score_reasons") or "{}")
        d["answers"] = json.loads(d.pop("answers_json") or "{}")
        s = slug(d["id"])
        for key, name in (("cv", "cv.pdf"), ("cover", "cover_letter.pdf")):
            f = APPS / s / name
            # the mtime in the URL makes the browser fetch a re-rendered PDF instead of a cached one
            d[key] = f"/files/{s}/{name}?v={int(f.stat().st_mtime)}" if f.exists() else None
        out.append(d)
    return out


def stats():
    conn = db.connect()
    counts = dict(conn.execute("SELECT status, count(*) FROM jobs GROUP BY status").fetchall())
    today = conn.execute("SELECT count(*) FROM applications WHERE date(applied_at) = date('now')").fetchone()[0]
    return {"counts": counts, "applied_today": today}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/jobs":
            return self._send(200, jobs(parse_qs(u.query).get("status", ["ready_for_review"])[0]))
        if u.path == "/api/stats":
            return self._send(200, stats())
        m = re.fullmatch(r"/files/([A-Za-z0-9_-]+)/(cv|cover_letter)\.pdf", u.path)
        if m:
            f = APPS / m.group(1) / f"{m.group(2)}.pdf"
            if f.exists():
                return self._send(200, f.read_bytes(), "application/pdf")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        m = re.fullmatch(r"/api/jobs/(.+)/status", urlparse(self.path).path)
        if not m:
            return self._send(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
        status, note = body.get("status"), body.get("note", "")
        if status not in ALLOWED:
            return self._send(400, {"error": f"status must be one of {sorted(ALLOWED)}"})
        job_id = unquote(m.group(1))
        conn = db.connect()
        if conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id)).rowcount == 0:
            return self._send(404, {"error": "unknown job"})
        conn.execute("INSERT INTO events (job_id, kind, detail) VALUES (?, 'status', ?)",
                     (job_id, f"{status} (dashboard) {note}".strip()))
        conn.commit()
        self._send(200, {"ok": True, "id": job_id, "status": status})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"JobPilot dashboard: http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
