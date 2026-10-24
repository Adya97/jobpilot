"""SQLite store for the pipeline. Run directly to initialise data/jobs.db."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,          -- source:external_id
    source        TEXT NOT NULL,             -- arbeitsagentur | greenhouse | lever | linkedin | ...
    url           TEXT NOT NULL,
    apply_url     TEXT,
    company       TEXT NOT NULL,
    title         TEXT NOT NULL,
    location      TEXT,
    work_mode     TEXT,                      -- onsite | hybrid | remote
    description   TEXT,
    posted_at     TEXT,
    found_at      TEXT DEFAULT (datetime('now')),
    fingerprint   TEXT UNIQUE,               -- normalised company+title, dedupes across sources
    score         INTEGER,                   -- 0-100
    score_reasons TEXT,                      -- JSON
    track         TEXT,                      -- devops | ai_ml | qa
    status        TEXT DEFAULT 'found'
    -- found -> scored -> rejected_auto | ready -> approved | rejected -> applied -> interview | offer | closed
);
CREATE TABLE IF NOT EXISTS applications (
    job_id        TEXT PRIMARY KEY REFERENCES jobs(id),
    cv_path       TEXT,
    cover_path    TEXT,
    answers_json  TEXT,
    outreach      TEXT,
    applied_at    TEXT,
    followup_due  TEXT,
    notes         TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id  TEXT,
    at      TEXT DEFAULT (datetime('now')),
    kind    TEXT,
    detail  TEXT
);
CREATE TABLE IF NOT EXISTS companies (
    name    TEXT PRIMARY KEY,
    ats     TEXT,                            -- greenhouse | lever | personio | workday | ...
    board   TEXT,                            -- ATS board slug
    policy  TEXT DEFAULT 'normal'            -- normal | always | never
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "easy_apply" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN easy_apply INTEGER")  # LinkedIn only
    return conn


if __name__ == "__main__":
    connect().close()
    print(f"initialised {DB_PATH}")
