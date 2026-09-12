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
            "found": r["found"], "n_quotes": len(r["quotes"]), "n_dropped": len(r.get("dropped_quotes", [])),
            "cited_expected_order": it["expect_goid"] in cited,
            "expect_goid": it["expect_goid"], "cited": sorted(cited), "seconds": secs,
            "answer": r["answer"][:200],
        })
        print(f"[{i}/{len(items)}] found={r['found']} quotes={len(r['quotes'])} "
              f"dropped={len(r.get('dropped_quotes', []))} right_order={it['expect_goid'] in cited} {secs}s",
              flush=True)

    ok = [r for r in rows if "error" not in r]
    n = len(ok) or 1
    out = {
        "ran": True, "ran_at": time.strftime("%d %b %Y"), "provider": a.provider,
        "model": a.model or (A.OLLAMA_MODEL if a.provider == "ollama" else A.ANTHROPIC_MODEL),
        "n": len(ok), "errors": len(rows) - len(ok),
        "answered": round(sum(r["found"] for r in ok) / n, 3),
        "cited_expected_order": round(sum(r["cited_expected_order"] for r in ok) / n, 3),
        "quotes_total": sum(r["n_quotes"] for r in ok),
        "quotes_dropped": sum(r["n_dropped"] for r in ok),
        "median_seconds": sorted(r["seconds"] for r in ok)[len(ok) // 2] if ok else None,
        "details": rows,
    }
    out["quote_verification_rate"] = round(
        out["quotes_total"] / max(out["quotes_total"] + out["quotes_dropped"], 1), 3)
    (DATA / "answer_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nquestions answered           : {out['answered']:.0%}")
    print(f"cited the expected order     : {out['cited_expected_order']:.0%}")
    print(f"quotes that passed verifying : {out['quote_verification_rate']:.0%} "
          f"({out['quotes_total']} kept, {out['quotes_dropped']} dropped)")
    print(f"median time per answer       : {out['median_seconds']}s")
    print(f"total wall time              : {round(time.time()-t0)}s")


if __name__ == "__main__":
    main()
