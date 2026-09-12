#!/usr/bin/env python3
"""SQLite store for GO metadata, OCR pages, chunks and full-text search.

Metadata (GO number, date, department, category) always comes from the portal API — never from OCR —
so citations stay exact even where OCR mangles digits.
"""
import json, sqlite3, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = DATA / "gos.db"

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS gos (
  goid INTEGER PRIMARY KEY,
  go_no TEXT, go_date TEXT, go_date_iso TEXT,
  subject TEXT, department_id INTEGER, department TEXT,
  section TEXT, category_id INTEGER, category TEXT,
  pdf_url TEXT, pdf_file TEXT, pages INTEGER, ocr_ok INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pages (
  goid INTEGER, page INTEGER, text TEXT, words INTEGER, mean_conf REAL,
  img_w INTEGER, img_h INTEGER,
  PRIMARY KEY (goid, page)
);
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
  goid INTEGER, page INTEGER, ord INTEGER,
  text TEXT, n_words INTEGER,
  box_x INTEGER, box_y INTEGER, box_w INTEGER, box_h INTEGER,
  word_ids TEXT,
  -- 'ocr'     text read from the scanned page, fallible, has a bounding box
  -- 'subject' the order's subject line as recorded on the portal: clean, human-entered, no box
  kind TEXT DEFAULT 'ocr'
);
CREATE INDEX IF NOT EXISTS chunks_goid ON chunks(goid, page);
CREATE TABLE IF NOT EXISTS refs (
  goid INTEGER, page INTEGER, ref_text TEXT, ref_year TEXT, target_goid INTEGER
);
CREATE INDEX IF NOT EXISTS refs_goid ON refs(goid);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text, content='chunks', content_rowid='chunk_id', tokenize='unicode61 remove_diacritics 0'
);
-- Phonetic keys, so a question in either script can reach a subject line that spells English words in
-- Devanagari. Standalone rather than external-content because the indexed text is derived, not stored.
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_phon USING fts5(
  phon, tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, text) VALUES (new.chunk_id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.chunk_id, old.text);
END;
"""


def connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def iso_date(d):
    """'14-05-2025' -> '2025-05-14' (sortable); returns None when unparseable."""
    if not d:
        return None
    m = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})", str(d).strip())
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def load_metadata(con, meta_file):
    meta = json.loads(Path(meta_file).read_text())
    n = 0
    for r in meta["rows"]:
        con.execute(
            """INSERT INTO gos (goid, go_no, go_date, go_date_iso, subject, department_id, department,
                                section, category_id, category, pdf_url, pdf_file)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(goid) DO UPDATE SET go_no=excluded.go_no, go_date=excluded.go_date,
                 go_date_iso=excluded.go_date_iso, subject=excluded.subject, category=excluded.category,
                 section=excluded.section, pdf_url=excluded.pdf_url, pdf_file=excluded.pdf_file""",
            (r["GOID"], r["GONo"], r["GODate1678"], iso_date(r["GODate1678"]), r["Subject"],
             r["DepartmentID"], r["DepartmentNameE"], r["SectionNameE"], r["CategoryID"],
             r["CategoryNameE"], r["pdf_url"], r["FileName_PDF"]))
        n += 1
    con.commit()
    return n


if __name__ == "__main__":
    con = connect()
    files = sorted((DATA / "meta").glob("dept-*.json"))
    if not files:
        raise SystemExit(f"no metadata in {DATA/'meta'} — run the scraper first")
    total = 0
    for f in files:
        n = load_metadata(con, f)
        print(f"loaded {n:>5} orders from {f.name}")
        total += n
    row = con.execute("SELECT COUNT(*) c, MIN(go_date_iso) a, MAX(go_date_iso) b FROM gos").fetchone()
    print(f"in db: {row['c']} orders, dates {row['a']} .. {row['b']}  ->  {DB_PATH}")
    for d in con.execute("""SELECT department, COUNT(*) c, SUM(ocr_ok) o FROM gos
                            GROUP BY 1 ORDER BY c DESC"""):
        print(f"  {d['c']:>5} orders ({d['o'] or 0} indexed)  {d['department']}")
