#!/usr/bin/env python3
"""HTTP API for the Government Order knowledge repository.

Serves search, grounded answers, order details, page images, and — the piece that makes the citations
checkable — a crop of the original scanned page with the supporting lines highlighted.
"""
import io, json, os, sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from db import connect, DATA  # noqa: E402
import search as S  # noqa: E402
import answer as A  # noqa: E402

app = FastAPI(title="Uttarakhand GO Knowledge Repository", version="0.1.0")


@app.on_event("startup")
def warm():
    """Load the query encoder before serving, so the first search is fast rather than a 60-second wait."""
    if S.VEC_FILE.exists():
        try:
            S.vector_search(connect(), "warm up", limit=1)
            print("query encoder ready")
        except Exception as e:  # search still works keyword-only
            print(f"query encoder unavailable, keyword-only search: {type(e).__name__}: {e}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def db():
    return connect()


@app.get("/api/health")
def health():
    con = db()
    g = con.execute("SELECT COUNT(*) c, SUM(ocr_ok) o FROM gos").fetchone()
    c = con.execute("SELECT COUNT(*) c FROM chunks").fetchone()
    depts = con.execute("""SELECT department, COUNT(*) n, SUM(ocr_ok) indexed FROM gos
                           GROUP BY 1 HAVING indexed > 0 ORDER BY n DESC""").fetchall()
    return {"status": "ok", "gos": g["c"], "gos_indexed": g["o"] or 0, "chunks": c["c"],
            "departments": [dict(d) for d in depts],
            "embeddings": S.VEC_FILE.exists(),
            "providers": {"ollama": bool(os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")),
                          "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY"))}}


@app.get("/api/facets")
def facets():
    con = db()
    cats = con.execute("""SELECT category, COUNT(*) n FROM gos WHERE ocr_ok=1
                          GROUP BY 1 ORDER BY n DESC""").fetchall()
    depts = con.execute("""SELECT department, COUNT(*) n FROM gos WHERE ocr_ok=1
                           GROUP BY 1 ORDER BY n DESC""").fetchall()
    yrs = con.execute("""SELECT substr(go_date_iso,1,4) y, COUNT(*) n FROM gos
                         WHERE ocr_ok=1 AND go_date_iso IS NOT NULL GROUP BY 1 ORDER BY y""").fetchall()
    return {"categories": [dict(r) for r in cats], "years": [dict(r) for r in yrs],
            "departments": [dict(r) for r in depts]}


@app.get("/api/search")
def api_search(q: str, limit: int = 10, category: str | None = None,
               date_from: str | None = None, date_to: str | None = None, go_no: str | None = None,
               department: str | None = None):
    con = db()
    filters = {"category": category, "date_from": date_from, "date_to": date_to, "go_no": go_no,
               "department": department}
    return {"query": q, "results": S.search(con, q, limit=limit, filters=filters)}


class AskBody(BaseModel):
    question: str
    provider: str = "ollama"
    model: str | None = None
    limit: int = 6
    category: str | None = None
    date_from: str | None = None
    date_to: str | None = None


@app.post("/api/ask")
def api_ask(b: AskBody):
    con = db()
    filters = {"category": b.category, "date_from": b.date_from, "date_to": b.date_to}
    try:
        r = A.answer(con, b.question, provider=b.provider, limit=b.limit, filters=filters, model=b.model)
    except Exception as e:
        raise HTTPException(503, f"answer provider failed: {type(e).__name__}: {e}")
    return r


@app.get("/api/go/{goid}")
def api_go(goid: int):
    con = db()
    g = con.execute("SELECT * FROM gos WHERE goid=?", (goid,)).fetchone()
    if not g:
        raise HTTPException(404, "unknown Government Order")
    pages = con.execute("SELECT page, words, mean_conf FROM pages WHERE goid=? ORDER BY page",
                        (goid,)).fetchall()
    chunks = con.execute("""SELECT chunk_id, page, ord, text, n_words, box_x, box_y, box_w, box_h
                            FROM chunks WHERE goid=? ORDER BY page, ord""", (goid,)).fetchall()
    refs = con.execute("SELECT ref_text, ref_year, page FROM refs WHERE goid=?", (goid,)).fetchall()
    return {"go": dict(g), "pages": [dict(r) for r in pages], "chunks": [dict(r) for r in chunks],
            "mentions": [dict(r) for r in refs], "related": S.related_gos(con, goid)}


@app.get("/api/page/{goid}/{page}.png")
def api_page(goid: int, page: int):
    p = DATA / "ocr" / str(goid) / f"page-{page}.png"
    if not p.exists():
        raise HTTPException(404, "page image not found")
    return FileResponse(p, media_type="image/png")


@app.get("/api/crop/{chunk_id}.png")
def api_crop(chunk_id: int, pad: int = 24, highlight: bool = True):
    """Crop the scanned page around one chunk and tint the exact region it came from."""
    from PIL import Image, ImageDraw
    con = db()
    c = con.execute("""SELECT c.*, g.go_no, g.go_date FROM chunks c JOIN gos g ON g.goid=c.goid
                       WHERE chunk_id=?""", (chunk_id,)).fetchone()
    if not c:
        raise HTTPException(404, "unknown passage")
    if c["kind"] == "subject" or c["box_x"] is None:
        raise HTTPException(409, "this passage is the order's subject line from the portal, "
                                 "not text read from a scanned page, so there is nothing to highlight")
    src = DATA / "ocr" / str(c["goid"]) / f"page-{c['page']}.png"
    if not src.exists():
        raise HTTPException(404, "page image not found")
    img = Image.open(src).convert("RGB")
    x, y, w, h = c["box_x"], c["box_y"], c["box_w"], c["box_h"]
    if highlight:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        d.rectangle([x, y, x + w, y + h], fill=(255, 214, 0, 60), outline=(214, 158, 0, 220), width=4)
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    box = (max(0, x - pad), max(0, y - pad), min(img.width, x + w + pad), min(img.height, y + h + pad))
    out = io.BytesIO()
    img.crop(box).save(out, format="PNG", optimize=True)
    return Response(out.getvalue(), media_type="image/png")


@app.get("/api/eval")
def api_eval():
    """Retrieval accuracy and answer grounding, as last measured."""
    out = {"ran": False}
    r = DATA / "eval_results.json"
    if r.exists():
        out = json.loads(r.read_text())
        out.pop("details", None)
    a = DATA / "answer_eval.json"
    if a.exists():
        ans = json.loads(a.read_text())
        ans.pop("details", None)
        out["answers"] = ans
    return out


# static UI (built by `npm run build` in ui/)
UI_DIST = ROOT / "ui" / "dist"
if UI_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="ui")
