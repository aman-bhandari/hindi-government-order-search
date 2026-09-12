#!/usr/bin/env python3
"""Hybrid retrieval over Government Order chunks: FTS5 keyword search fused with dense vectors.

Why hybrid: officers type both exact administrative phrases ("ग्लोबल बजटिंग", "grant number 23") where
keyword search wins, and descriptive questions ("who chairs the drone committee") where embeddings win.
Reciprocal-rank fusion needs no score calibration between the two, which matters because BM25 scores and
cosine similarities are not comparable.

Embeddings are optional: if the vector file is absent, search degrades to keyword-only rather than failing,
so the pipeline is usable before the (slow) embedding step has run.
"""
import json, re, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect, DATA  # noqa: E402

VEC_FILE = DATA / "chunk_vectors.npy"
VEC_IDS = DATA / "chunk_vector_ids.json"
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
MODEL_NAME = "BAAI/bge-m3"

_model = None
_vecs = None
_ids = None


def normalise(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().translate(DEV_DIGITS))


def fts_query(q: str) -> str:
    """Build a safe FTS5 MATCH expression: quote every token, OR them, so partial matches still rank."""
    toks = [t for t in re.split(r"[^\wऀ-ॿ]+", normalise(q)) if len(t) > 1]
    if not toks:
        return None
    return " OR ".join(f'"{t}"' for t in toks)


def _terms(q):
    return [t for t in re.split(r"[^\w\u0900-\u097F]+", normalise(q).lower()) if len(t) > 2]


def _coverage(q, text):
    """Share of the query's substantive terms that actually appear in this passage."""
    terms = _terms(q)
    if not terms:
        return 0.0
    low = text.lower()
    return round(sum(1 for t in terms if t in low) / len(terms), 3)


def keyword_search(con, q, limit=50, filters=None):
    expr = fts_query(q)
    if not expr:
        return []
    where, params_pre = ["chunks_fts MATCH ?"], []
    if filters:
        if filters.get("category"):
            where.append("g.category = ?"); params_pre.append(filters["category"])
        if filters.get("date_from"):
            where.append("g.go_date_iso >= ?"); params_pre.append(filters["date_from"])
        if filters.get("date_to"):
            where.append("g.go_date_iso <= ?"); params_pre.append(filters["date_to"])
        if filters.get("go_no"):
            where.append("g.go_no LIKE ?"); params_pre.append(f"%{filters['go_no']}%")
        if filters.get("goid"):
            where.append("c.goid = ?"); params_pre.append(filters["goid"])
    sql = f"""
      SELECT c.chunk_id, c.goid, c.page, c.ord, c.text, bm25(chunks_fts) AS bm25
      FROM chunks_fts
      JOIN chunks c ON c.chunk_id = chunks_fts.rowid
      JOIN gos g ON g.goid = c.goid
      WHERE {' AND '.join(where)}
      ORDER BY bm25 LIMIT ?"""
    rows = con.execute(sql, [expr] + params_pre + [limit]).fetchall()
    return [dict(r) for r in rows]


def _load_vectors():
    global _vecs, _ids
    if _vecs is not None:
        return _vecs, _ids
    if not VEC_FILE.exists() or not VEC_IDS.exists():
        return None, None
    import numpy as np
    _vecs = np.load(VEC_FILE)
    _ids = json.loads(VEC_IDS.read_text())
    return _vecs, _ids


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME, device="cuda" if _cuda() else "cpu")
    return _model


def _cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def vector_search(con, q, limit=50, filters=None):
    vecs, ids = _load_vectors()
    if vecs is None:
        return []
    import numpy as np
    qv = _load_model().encode([normalise(q)], normalize_embeddings=True)[0]
    sims = vecs @ qv
    allowed = None
    if filters and any(filters.get(k) for k in ("category", "date_from", "date_to", "go_no", "goid")):
        allowed = {r["chunk_id"] for r in keyword_filter_ids(con, filters)}
    order = np.argsort(-sims)
    out = []
    for i in order:
        cid = ids[int(i)]
        if allowed is not None and cid not in allowed:
            continue
        out.append({"chunk_id": cid, "cosine": float(sims[int(i)])})
        if len(out) >= limit:
            break
    return out


def keyword_filter_ids(con, filters):
    where, params = ["1=1"], []
    if filters.get("category"):
        where.append("g.category = ?"); params.append(filters["category"])
    if filters.get("date_from"):
        where.append("g.go_date_iso >= ?"); params.append(filters["date_from"])
    if filters.get("date_to"):
        where.append("g.go_date_iso <= ?"); params.append(filters["date_to"])
    if filters.get("go_no"):
        where.append("g.go_no LIKE ?"); params.append(f"%{filters['go_no']}%")
    if filters.get("goid"):
        where.append("c.goid = ?"); params.append(filters["goid"])
    return con.execute(f"""SELECT c.chunk_id FROM chunks c JOIN gos g ON g.goid=c.goid
                          WHERE {' AND '.join(where)}""", params).fetchall()


def hydrate(con, chunk_ids):
    if not chunk_ids:
        return {}
    qs = ",".join("?" * len(chunk_ids))
    rows = con.execute(f"""
        SELECT c.chunk_id, c.goid, c.page, c.ord, c.text, c.n_words, c.kind,
               c.box_x, c.box_y, c.box_w, c.box_h,
               g.go_no, g.go_date, g.go_date_iso, g.subject, g.category, g.section, g.department, g.pdf_url
        FROM chunks c JOIN gos g ON g.goid = c.goid WHERE c.chunk_id IN ({qs})""", chunk_ids).fetchall()
    return {r["chunk_id"]: dict(r) for r in rows}


def search(con, q, limit=10, filters=None, k=60, per_go=2):
    """Reciprocal-rank fusion of keyword and vector results, diversified across orders.

    A few long policy documents hold a large share of the corpus (one 38-page order alone contributes 236
    of 4,345 passages), so without a cap they occupy every result slot on broad queries and short one-page
    orders become unreachable. `per_go` limits how many passages one order may contribute.
    """
    kw = keyword_search(con, q, limit=50, filters=filters)
    vec = vector_search(con, q, limit=50, filters=filters)
    fused, bm25_by, cos_by = {}, {}, {}
    for rank, r in enumerate(kw):
        fused[r["chunk_id"]] = fused.get(r["chunk_id"], 0) + 1.0 / (k + rank + 1)
        bm25_by[r["chunk_id"]] = r["bm25"]
    for rank, r in enumerate(vec):
        fused[r["chunk_id"]] = fused.get(r["chunk_id"], 0) + 1.0 / (k + rank + 1)
        cos_by[r["chunk_id"]] = r["cosine"]
    ranked = sorted(fused.items(), key=lambda kv: -kv[1])[: limit * 10]
    meta = hydrate(con, [cid for cid, _ in ranked])
    kw_ids = {r["chunk_id"] for r in kw}
    vec_ids = {r["chunk_id"] for r in vec}
    out, seen_pages, per_go_count = [], set(), {}
    for cid, score in ranked:
        if cid not in meta:
            continue
        d = dict(meta[cid])
        # The portal republishes some orders under the same number (9 of 308 in the IT department),
        # so the same page can appear as several passages. Keep only the best-scoring one per
        # (order number, page); a second scan of the same page is never new information.
        key = (re.sub(r"\W", "", (d["go_no"] or "")).lower(), d["page"])
        if key in seen_pages:
            continue
        go_key = re.sub(r"\W", "", (d["go_no"] or "")).lower() or str(d["goid"])
        if per_go and per_go_count.get(go_key, 0) >= per_go:
            continue
        seen_pages.add(key)
        per_go_count[go_key] = per_go_count.get(go_key, 0) + 1
        d["score"] = round(score, 5)
        # Reciprocal-rank fusion deliberately ignores how good a match is: the top result always scores
        # the same whether the query was answerable or nonsense. Carry the underlying signals so callers
        # can decide whether anything here is actually relevant.
        d["bm25"] = round(bm25_by[cid], 3) if cid in bm25_by else None
        d["cosine"] = round(cos_by[cid], 4) if cid in cos_by else None
        d["lexical_coverage"] = _coverage(q, d["text"])
        tags = []
        if cid in kw_ids:
            tags.append("keyword")
        if cid in vec_ids:
            tags.append("vector")
        d["matched_by"] = "+".join(tags) or "none"
        out.append(d)
        if len(out) >= limit:
            break
    return out


def related_gos(con, goid, limit=5):
    """Related orders without relying on OCR digits: same section/category, nearest in time,
    plus vector similarity of their text when embeddings exist."""
    g = con.execute("SELECT * FROM gos WHERE goid=?", (goid,)).fetchone()
    if not g:
        return []
    rows = con.execute("""
        SELECT goid, go_no, go_date, go_date_iso, subject, category, section,
               ABS(julianday(COALESCE(go_date_iso,'2000-01-01')) - julianday(COALESCE(?,'2000-01-01'))) AS day_gap
        FROM gos
        WHERE goid != ? AND ocr_ok = 1
          AND (category = ? OR section = ?)
          AND COALESCE(go_no,'') != COALESCE(?,'')
        ORDER BY day_gap ASC LIMIT ?""",
        (g["go_date_iso"], goid, g["category"], g["section"], g["go_no"], limit * 4)).fetchall()
    # the portal republishes some orders under one number; show each number once
    seen, out = set(), []
    for r in rows:
        key = re.sub(r"\W", "", (r["go_no"] or "")).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(r))
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    con = connect()
    qs = sys.argv[1:] or ["ड्रोन समिति", "global budgeting", "grant number 23", "लैब ऑन व्हील्स"]
    for q in qs:
        print(f"\n### {q}")
        for r in search(con, q, limit=3):
            print(f"  [{r['matched_by']}] GO {r['go_no']} ({r['go_date']}) p{r['page']} — {r['category']}")
            print(f"      {r['text'][:130]}")
