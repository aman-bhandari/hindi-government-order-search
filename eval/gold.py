#!/usr/bin/env python3
"""Build and run a gold-set evaluation of retrieval quality.

`build` picks distinctive passages from the indexed corpus and writes a template the human fills in with
real questions. Questions must be written by a person: auto-generated questions tend to reuse the passage's
own wording, which flatters retrieval and measures nothing.

`run` reports how often the correct order and page appear in the top results.
"""
import argparse, json, random, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from db import connect, DATA  # noqa: E402
import search as S  # noqa: E402

GOLD = Path(__file__).resolve().parent / "gold.json"
DEV = re.compile(r"[ऀ-ॿ]")


def build(n=30, seed=7):
    con = connect()
    rows = con.execute("""
        SELECT c.chunk_id, c.goid, c.page, c.text, c.n_words, g.go_no, g.go_date, g.subject, g.category
        FROM chunks c JOIN gos g ON g.goid=c.goid
        WHERE c.n_words BETWEEN 25 AND 90""").fetchall()
    if not rows:
        sys.exit("no chunks — run the pipeline first")
    random.seed(seed)
    # spread across orders: at most two passages per order
    by_go, picked = {}, []
    for r in random.sample(rows, len(rows)):
        if by_go.get(r["goid"], 0) >= 2:
            continue
        by_go[r["goid"]] = by_go.get(r["goid"], 0) + 1
        picked.append(r)
        if len(picked) >= n:
            break
    items = [{
        "id": i + 1,
        "question": "",
        "language": "hi" if DEV.search(r["text"]) else "en",
        "expect_goid": r["goid"], "expect_page": r["page"], "expect_chunk_id": r["chunk_id"],
        "go_no": r["go_no"], "go_date": r["go_date"], "category": r["category"],
        "passage": r["text"],
    } for i, r in enumerate(picked)]
    GOLD.write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f"wrote {len(items)} templates -> {GOLD}\nFill in the 'question' field for each, then: python eval/gold.py run")


def run():
    items = json.loads(GOLD.read_text())
    ready = [i for i in items if i.get("question", "").strip()]
    if not ready:
        sys.exit(f"no questions filled in yet in {GOLD}")
    con = connect()
    hits1 = hits5 = page5 = 0
    details = []
    for it in ready:
        res = S.search(con, it["question"], limit=5)
        gos = [r["goid"] for r in res]
        h1 = bool(gos) and gos[0] == it["expect_goid"]
        h5 = it["expect_goid"] in gos
        p5 = any(r["goid"] == it["expect_goid"] and r["page"] == it["expect_page"] for r in res)
        hits1 += h1; hits5 += h5; page5 += p5
        details.append({"id": it["id"], "question": it["question"], "language": it["language"],
                        "expect_goid": it["expect_goid"], "got": gos,
                        "hit_at_1": h1, "hit_at_5": h5, "page_hit_at_5": p5})
    n = len(ready)
    out = {
        "ran": True, "ran_at": time.strftime("%d %b %Y"), "n": n,
        "n_hindi": sum(1 for i in ready if i["language"] == "hi"),
        "n_english": sum(1 for i in ready if i["language"] == "en"),
        "hit_at_1": round(hits1 / n, 3), "hit_at_5": round(hits5 / n, 3),
        "page_hit_at_5": round(page5 / n, 3),
        "embeddings_used": S.VEC_FILE.exists(), "details": details,
    }
    (DATA / "eval_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"questions: {n} (hi {out['n_hindi']}, en {out['n_english']})  embeddings: {out['embeddings_used']}")
    print(f"correct order ranked first : {out['hit_at_1']:.0%}")
    print(f"correct order in top 5     : {out['hit_at_5']:.0%}")
    print(f"correct page in top 5      : {out['page_hit_at_5']:.0%}")
    miss = [d for d in details if not d["hit_at_5"]]
    if miss:
        print(f"\nmissed ({len(miss)}):")
        for d in miss[:8]:
            print(f"  [{d['language']}] {d['question'][:70]}  expected GO {d['expect_goid']}, got {d['got'][:3]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "run"])
    ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args()
    build(a.n) if a.cmd == "build" else run()
