#!/usr/bin/env python3
"""Gate report: is Hindi OCR on real Uttarakhand GOs good enough to build on?"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEV = re.compile(r"[ऀ-ॿ]")
GO_REF = re.compile(r"(?:संख्या|सं0|सं\.|No\.?|Number)\s*[-:–]?\s*([0-9०-९][0-9०-९/A-Za-zऀ-ॿ()\-.]{4,60})")
DATE_RE = re.compile(r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})|दिनांक")

meta = json.loads((DATA / "meta" / "dept-17.json").read_text())
by_id = {str(r["GOID"]): r for r in meta["rows"]}
summary = json.loads((DATA / "ocr" / "summary.json").read_text())

rows, all_conf, low_pages = [], [], 0
for s in summary:
    ok = [p for p in s["pages"] if "chars" in p]
    if not ok:
        continue
    conf = [p["mean_conf"] for p in ok if p["mean_conf"] is not None]
    text = "\n".join((DATA / "ocr" / s["goid"] / f"page-{p['page']}.txt").read_text(encoding="utf-8", errors="ignore")
                     for p in ok if (DATA / "ocr" / s["goid"] / f"page-{p['page']}.txt").exists())
    dev = sum(1 for c in text if DEV.match(c))
    latin = sum(1 for c in text if "a" <= c.lower() <= "z")
    letters = dev + latin
    m = by_id.get(s["goid"], {})
    c = round(sum(conf) / len(conf), 1) if conf else None
    all_conf += conf
    low_pages += sum(1 for p in ok if p["mean_conf"] is not None and p["mean_conf"] < 70)
    rows.append({
        "goid": s["goid"], "date": m.get("GODate1678"), "category": m.get("CategoryNameE"),
        "pages_ocrd": len(ok), "pages_total": s["pages_total"],
        "chars": sum(p["chars"] for p in ok), "words": sum(p["words"] for p in ok),
        "mean_conf": c, "devanagari_pct": round(100 * dev / letters) if letters else 0,
        "go_refs_found": len(set(GO_REF.findall(text))), "has_date_token": bool(DATE_RE.search(text)),
        "secs_per_page": round(sum(p["seconds"] for p in ok) / len(ok), 1),
        "subject": (m.get("Subject") or "")[:70],
    })

print(f"{'GOID':<7}{'date':<12}{'pg':<7}{'words':<7}{'conf':<7}{'देव%':<6}{'refs':<6}{'s/pg':<6}subject")
for r in sorted(rows, key=lambda r: r["mean_conf"] or 0):
    print(f"{r['goid']:<7}{str(r['date']):<12}{str(r['pages_ocrd'])+'/'+str(r['pages_total']):<7}"
          f"{r['words']:<7}{str(r['mean_conf']):<7}{r['devanagari_pct']:<6}{r['go_refs_found']:<6}"
          f"{r['secs_per_page']:<6}{r['subject']}")

n = len(rows)
mean_conf = round(sum(all_conf) / len(all_conf), 1) if all_conf else 0
hindi_docs = sum(1 for r in rows if r["devanagari_pct"] >= 50)
empty = sum(1 for r in rows if r["words"] < 20)
print(f"\nGOs OCR'd: {n} | pages: {sum(r['pages_ocrd'] for r in rows)} | mean word confidence: {mean_conf}%")
print(f"pages below 70% confidence: {low_pages} | GOs with <20 words (OCR failure): {empty}")
print(f"predominantly Devanagari GOs: {hindi_docs}/{n} | GOs with an internal GO reference found: "
      f"{sum(1 for r in rows if r['go_refs_found'] > 0)}/{n}")
print(f"mean seconds per page: {round(sum(r['secs_per_page'] for r in rows)/n,1)} "
      f"-> full 308-GO corpus estimate: see gate.md")
(DATA / "ocr" / "gate_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
