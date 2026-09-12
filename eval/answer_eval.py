#!/usr/bin/env python3
"""Measure whether answers stay grounded: do the model's quotes survive verification?

This is the claim that matters most for a government tool. Retrieval accuracy (eval/gold.py) says whether
the right order was found; this says whether the answer built on it can be trusted.
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from db import connect, DATA  # noqa: E402
import answer as A  # noqa: E402

GOLD = Path(__file__).resolve().parent / "gold.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="ollama")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=0, help="number of questions (0 = all)")
    a = ap.parse_args()

    items = [i for i in json.loads(GOLD.read_text()) if i.get("question", "").strip()]
    if a.limit:
        items = items[:a.limit]
    con = connect()
    rows, t0 = [], time.time()
    for i, it in enumerate(items, 1):
        t = time.time()
        try:
            r = A.answer(con, it["question"], provider=a.provider, limit=6, model=a.model)
            err = None
        except Exception as e:
            r, err = None, f"{type(e).__name__}: {e}"
        secs = round(time.time() - t, 1)
        if err:
            rows.append({"id": it["id"], "error": err, "seconds": secs})
            print(f"[{i}/{len(items)}] ERROR {err}", flush=True)
            continue
        cited = {q["goid"] for q in r["quotes"]}
        rows.append({
            "id": it["id"], "question": it["question"], "language": it["language"],
            "unanswerable": bool(it.get("unanswerable")),
            "found": r["found"], "n_quotes": len(r["quotes"]), "n_dropped": len(r.get("dropped_quotes", [])),
            "cited_expected_order": it["expect_goid"] in cited,
            "expect_goid": it["expect_goid"], "cited": sorted(cited), "seconds": secs,
            "answer": r["answer"][:200],
        })
        print(f"[{i}/{len(items)}] found={r['found']} quotes={len(r['quotes'])} "
              f"dropped={len(r.get('dropped_quotes', []))} right_order={it['expect_goid'] in cited} {secs}s",
              flush=True)

    ok = [r for r in rows if "error" not in r]
    # Answerable and unanswerable questions measure opposite things and must never be averaged together:
    # answering is success for one group and failure for the other.
    ansable = [r for r in ok if not r.get("unanswerable")]
    unans = [r for r in ok if r.get("unanswerable")]
    na = len(ansable) or 1
    quotes = sum(r["n_quotes"] for r in ansable)
    dropped = sum(r["n_dropped"] for r in ansable)
    out = {
        "ran": True, "ran_at": time.strftime("%d %b %Y"), "provider": a.provider,
        "model": a.model or (A.OLLAMA_MODEL if a.provider == "ollama" else A.ANTHROPIC_MODEL),
        "n": len(ansable), "n_unanswerable": len(unans), "errors": len(rows) - len(ok),
        "answered": round(sum(r["found"] for r in ansable) / na, 3),
        "cited_expected_order": round(sum(r["cited_expected_order"] for r in ansable) / na, 3),
        "declined_unanswerable": round(sum(1 for r in unans if not r["found"]) / len(unans), 3) if unans else None,
        "quotes_total": quotes, "quotes_dropped": dropped,
        "quote_verification_rate": round(quotes / max(quotes + dropped, 1), 3),
        "median_seconds": sorted(r["seconds"] for r in ok)[len(ok) // 2] if ok else None,
        "details": rows,
    }
    (DATA / "answer_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nof {out['n']} answerable questions")
    print(f"  answered rather than declined : {out['answered']:.0%}")
    print(f"  cited the expected order      : {out['cited_expected_order']:.0%}")
    print(f"  quotes passing verification   : {out['quote_verification_rate']:.0%} "
          f"({quotes} kept, {dropped} dropped)")
    if out["declined_unanswerable"] is not None:
        print(f"of {out['n_unanswerable']} questions with no answer in the corpus")
        print(f"  correctly declined            : {out['declined_unanswerable']:.0%}")
    print(f"median time per answer          : {out['median_seconds']}s")
    print(f"total wall time                 : {round(time.time()-t0)}s")


if __name__ == "__main__":
    main()
