#!/usr/bin/env python3
"""Turn OCR pages into retrievable chunks with pixel boxes, and mine GO cross-references.

Design notes
------------
* A chunk is a paragraph-sized block of one page. Government Orders are short letters, so page-level
  chunks are too coarse to quote and line-level chunks lose context; paragraphs are the natural unit.
* Every chunk carries the bounding box of its words, so the UI can highlight exactly the lines that
  support an answer on the original scanned image.
* Page furniture (the e-office header/footer lines the portal stamps on every page) is dropped: it is
  identical across thousands of pages and would pollute retrieval.
* Devanagari digits are normalised to ASCII so a query typed either way matches.
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect, DATA  # noqa: E402
from translit import phonetic_text  # noqa: E402

DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# e-office furniture stamped on scanned pages, plus OCR noise lines
FURNITURE = [
    re.compile(r"^[A-Z]{2,}-[A-Z0-9/]+-[A-Z]+--?[A-Za-z ]+Department\s*$"),  # IT-POL/2/2022-XXXIV--Information Technology Department
    re.compile(r"^[A-Z]?/?\d{3,}/\d{4}\s*$"),                                 # I/8534/2024
    re.compile(r"^[\W_]{0,6}$"),                                              # punctuation-only
]

# "संख्या-1159/XXXIV-1/2021-23/2021", "शासनादेश संख्या 430/XXVII(6)/...", "No. 4875"
GO_REF = re.compile(
    r"(?:शासनादेश\s*)?(?:संख्या|सं0|सं\.|क्रमांक|No\.?|Number)\s*[-:–—]?\s*"
    r"([0-9][0-9A-Za-zऀ-ॿ()/\-.]{5,60})")
YEAR = re.compile(r"(19\d{2}|20\d{2})")


def clean_line(s: str) -> str:
    s = s.replace("​", "").strip()
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s


def is_furniture(line: str) -> bool:
    return any(p.match(line) for p in FURNITURE)


def load_boxes(tsv_path: Path):
    """Return list of word dicts from a tesseract TSV."""
    out = []
    if not tsv_path.exists():
        return out
    for ln in tsv_path.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
        p = ln.split("\t")
        if len(p) < 12:
            continue
        text = p[11].strip()
        if not text:
            continue
        try:
            conf = float(p[10])
            left, top, w, h = int(p[6]), int(p[7]), int(p[8]), int(p[9])
            block, par, line, word = int(p[2]), int(p[3]), int(p[4]), int(p[5])
        except ValueError:
            continue
        out.append({"text": text, "conf": conf, "x": left, "y": top, "w": w, "h": h,
                    "block": block, "par": par, "line": line, "word": word})
    return out


def _box(words):
    xs = [w["x"] for w in words]; ys = [w["y"] for w in words]
    x2 = [w["x"] + w["w"] for w in words]; y2 = [w["y"] + w["h"] for w in words]
    return (min(xs), min(ys), max(x2) - min(xs), max(y2) - min(ys))


def _mk(words, lines_text):
    text = " ".join(lines_text).strip().translate(DEV_DIGITS)
    return {
        "text": text, "n_words": len(text.split()), "box": _box(words),
        "word_ids": [f"{w['block']}.{w['par']}.{w['line']}.{w['word']}" for w in words],
        "mean_conf": round(sum(w["conf"] for w in words) / len(words), 1),
    }


def chunks_from_boxes(words, min_words=6, max_words=110):
    """Group tesseract words into chunks that are quotable and tightly boxed.

    With --psm 3 tesseract reports real paragraph blocks, so a chunk starts as one paragraph.
    A paragraph longer than max_words is split on line boundaries, so every chunk keeps a tight
    bounding box around only the lines it contains — that box is what the UI highlights.
    """
    paras = {}
    for w in words:
        paras.setdefault((w["block"], w["par"]), []).append(w)

    out = []
    for key in sorted(paras):
        ws = paras[key]
        lines = {}
        for w in ws:
            lines.setdefault(w["line"], []).append(w)
        # ordered list of (line_no, words, text), dropping furniture and empty lines
        seq = []
        for ln in sorted(lines):
            lw = sorted(lines[ln], key=lambda w: w["word"])
            text = clean_line(" ".join(w["text"] for w in lw))
            if text and not is_furniture(text):
                seq.append((lw, text))
        if not seq:
            continue
        buf_w, buf_t, count = [], [], 0
        for lw, text in seq:
            n = len(text.split())
            if count and count + n > max_words:
                out.append(_mk(buf_w, buf_t))
                buf_w, buf_t, count = [], [], 0
            buf_w += lw; buf_t.append(text); count += n
        if buf_w:
            out.append(_mk(buf_w, buf_t))
    return [c for c in out if c["n_words"] >= min_words]


def merge_small(chunks, target_words=35, max_words=110):
    """Merge adjacent small chunks (headers, single lines) into the next block."""
    out = []
    for c in chunks:
        if out and out[-1]["n_words"] < target_words and out[-1]["n_words"] + c["n_words"] <= max_words:
            prev = out[-1]
            bx = min(prev["box"][0], c["box"][0]); by = min(prev["box"][1], c["box"][1])
            bx2 = max(prev["box"][0] + prev["box"][2], c["box"][0] + c["box"][2])
            by2 = max(prev["box"][1] + prev["box"][3], c["box"][1] + c["box"][3])
            prev["text"] += " " + c["text"]
            prev["n_words"] += c["n_words"]
            prev["box"] = (bx, by, bx2 - bx, by2 - by)
            prev["word_ids"] += c["word_ids"]
            prev["mean_conf"] = round((prev["mean_conf"] + c["mean_conf"]) / 2, 1)
        else:
            out.append(dict(c))
    return out


def extract_refs(text, self_go_no):
    """Find references to other Government Orders inside the text."""
    refs = []
    norm_self = re.sub(r"\W", "", (self_go_no or "")).lower()
    for m in GO_REF.finditer(text):
        raw = m.group(1).strip(" .,:;-")
        if len(re.sub(r"\D", "", raw)) < 3:      # needs real digits, not just letters
            continue
        if re.sub(r"\W", "", raw).lower() == norm_self:
            continue                              # a GO citing its own number
        y = YEAR.search(raw)
        window = text[max(0, m.start() - 40):m.end() + 40]
        refs.append({"ref_text": raw, "ref_year": y.group(1) if y else None, "context": window})
    # de-duplicate on normalised form
    seen, uniq = set(), []
    for r in refs:
        k = re.sub(r"\W", "", r["ref_text"]).lower()
        if k not in seen:
            seen.add(k); uniq.append(r)
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--rebuild", action="store_true", help="clear chunks/refs/pages first")
    a = ap.parse_args()
    data = Path(a.data)
    con = connect()
    if a.rebuild:
        con.executescript("DELETE FROM chunks; DELETE FROM refs; DELETE FROM pages; "
                          "DELETE FROM chunks_phon; "
                          "INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');")
        con.commit()

    go_meta = {r["goid"]: r for r in con.execute("SELECT goid, go_no, subject FROM gos")}
    done_gos = {r[0] for r in con.execute("SELECT DISTINCT goid FROM chunks")}
    dirs = sorted((data / "ocr").glob("*/"), key=lambda p: p.name)
    n_go = n_pages = n_chunks = n_refs = 0
    for d in dirs:
        if not d.name.isdigit():
            continue
        goid = int(d.name)
        if goid in done_gos and not a.rebuild:
            continue
        pages = sorted(d.glob("page-*.tsv"), key=lambda p: int(p.stem.split("-")[1]))
        if not pages:
            continue
        go_no = go_meta.get(goid, {})["go_no"] if goid in go_meta else None
        for tsv in pages:
            page = int(tsv.stem.split("-")[1])
            words = load_boxes(tsv)
            if not words:
                continue
            paras = merge_small(chunks_from_boxes(words))
            page_text = "\n".join(p["text"] for p in paras)
            mean_conf = round(sum(w["conf"] for w in words) / len(words), 1)
            con.execute("INSERT OR REPLACE INTO pages (goid,page,text,words,mean_conf) VALUES (?,?,?,?,?)",
                        (goid, page, page_text, len(words), mean_conf))
            for i, p in enumerate(paras):
                cur = con.execute(
                    """INSERT INTO chunks (goid,page,ord,text,n_words,box_x,box_y,box_w,box_h,word_ids,kind)
                       VALUES (?,?,?,?,?,?,?,?,?,?,'ocr')""",
                    (goid, page, i, p["text"], p["n_words"], *p["box"], json.dumps(p["word_ids"])))
                con.execute("INSERT INTO chunks_phon (rowid, phon) VALUES (?,?)",
                            (cur.lastrowid, phonetic_text(p["text"])))
                n_chunks += 1
            for r in extract_refs(page_text, go_no):
                con.execute("INSERT INTO refs (goid,page,ref_text,ref_year,target_goid) VALUES (?,?,?,?,?)",
                            (goid, page, r["ref_text"], r["ref_year"], None))
                n_refs += 1
            n_pages += 1
        # Index the subject line too. Many one-page orders OCR to little more than letterhead: the body is
        # faint, handwritten or garbled, while the portal's own subject line states plainly what the order is
        # about. It is clean, human-entered metadata, so it cannot be corrupted by OCR, and without it those
        # orders are effectively unfindable. Flagged 'subject' so the interface never claims it came from a scan.
        subj = (go_meta.get(goid, {})["subject"] if goid in go_meta else None) or ""
        subj = re.sub(r"\s+", " ", subj).strip()
        if len(subj.split()) >= 3:
            cur = con.execute(
                """INSERT INTO chunks (goid,page,ord,text,n_words,box_x,box_y,box_w,box_h,word_ids,kind)
                   VALUES (?,0,0,?,?,NULL,NULL,NULL,NULL,NULL,'subject')""",
                (goid, subj.translate(DEV_DIGITS), len(subj.split())))
            con.execute("INSERT INTO chunks_phon (rowid, phon) VALUES (?,?)",
                        (cur.lastrowid, phonetic_text(subj)))
            n_chunks += 1
        n_go += 1
        con.commit()

    # resolve references to GOIDs where the cited number matches a known GO number
    con.execute("""UPDATE refs SET target_goid = (
        SELECT g.goid FROM gos g
        WHERE replace(replace(replace(replace(lower(g.go_no),'/',''),'-',''),'.',''),' ','')
              = replace(replace(replace(replace(lower(refs.ref_text),'/',''),'-',''),'.',''),' ','')
        LIMIT 1) WHERE target_goid IS NULL""")
    con.commit()
    resolved = con.execute("SELECT COUNT(*) FROM refs WHERE target_goid IS NOT NULL").fetchone()[0]
    con.execute("UPDATE gos SET ocr_ok=1 WHERE goid IN (SELECT DISTINCT goid FROM chunks)")
    con.commit()
    tot = con.execute("SELECT COUNT(*) c, AVG(n_words) w FROM chunks").fetchone()
    print(f"chunked {n_go} GOs, {n_pages} pages -> {n_chunks} new chunks, {n_refs} refs")
    print(f"db totals: {tot['c']} chunks, avg {tot['w']:.0f} words/chunk, refs resolved to a known GO: {resolved}")


if __name__ == "__main__":
    main()
