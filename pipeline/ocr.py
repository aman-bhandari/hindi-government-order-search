#!/usr/bin/env python3
"""OCR scanned Government Order PDFs to text + word boxes.

Works with native tesseract/pdftoppm, or transparently through a Docker image
(--engine docker) when the tools are not installed on the host.

Output per GO:  data/ocr/<GOID>/page-<n>.png  (300 dpi image, kept for evidence crops)
                data/ocr/<GOID>/page-<n>.txt  (plain text)
                data/ocr/<GOID>/page-<n>.tsv  (tesseract TSV: word, conf, left/top/width/height)
                data/ocr/<GOID>/ocr.json      (per-page stats)
Resumable: a page with all three files present is skipped.
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKER_IMAGE = "ukis-ocr-spike"
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def have(cmd): return shutil.which(cmd) is not None


def pick_engine(requested):
    if requested == "native":
        missing = [c for c in ("pdftoppm", "tesseract") if not have(c)]
        if missing:
            sys.exit(f"native engine missing: {', '.join(missing)}. "
                     f"Install with: sudo apt install -y tesseract-ocr tesseract-ocr-hin poppler-utils")
        return "native"
    if requested == "docker":
        return "docker"
    if have("pdftoppm") and have("tesseract"):
        out = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
        if "hin" in out:
            return "native"
    return "docker"


def run(engine, workdir: Path, argv):
    """Run a command with workdir as cwd (native) or as /d (docker)."""
    if engine == "native":
        return subprocess.run(argv, cwd=workdir, capture_output=True, text=True)
    return subprocess.run(
        ["docker", "run", "--rm", "-v", f"{workdir}:/d", "-w", "/d", DOCKER_IMAGE] + argv,
        capture_output=True, text=True)


def page_count(pdf: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except Exception:
        return 0


def ocr_go(goid: str, pdf: Path, outdir: Path, engine: str, dpi: int, lang: str, max_pages: int):
    outdir.mkdir(parents=True, exist_ok=True)
    n = page_count(pdf)
    pages = min(n, max_pages) if max_pages else n
    stats = {"goid": goid, "pdf": pdf.name, "pages_total": n, "pages_done": 0, "engine": engine,
             "dpi": dpi, "lang": lang, "pages": []}
    work = outdir  # rasterise and OCR in place
    shutil.copy(pdf, work / "src.pdf")
    for p in range(1, pages + 1):
        png, txt, tsv = work / f"page-{p}.png", work / f"page-{p}.txt", work / f"page-{p}.tsv"
        t0 = time.time()
        if not png.exists():
            r = run(engine, work, ["pdftoppm", "-r", str(dpi), "-f", str(p), "-l", str(p), "-png", "src.pdf", "pg"])
            if r.returncode != 0:
                stats["pages"].append({"page": p, "error": r.stderr[:200]}); continue
            produced = sorted(work.glob("pg-*.png"))
            if not produced:
                stats["pages"].append({"page": p, "error": "no image produced"}); continue
            produced[0].rename(png)
        if not txt.exists() or not tsv.exists():
            for mode, ext in (("txt", "txt"), ("tsv", "tsv")):
                r = run(engine, work, ["tesseract", png.name, f"page-{p}", "-l", lang, "--psm", "6", mode])
                if r.returncode != 0:
                    stats["pages"].append({"page": p, "error": f"tesseract {mode}: {r.stderr[:200]}"}); break
        if txt.exists():
            text = txt.read_text(encoding="utf-8", errors="ignore")
            words = [w for w in text.split() if w.strip()]
            dev = sum(1 for ch in text if DEVANAGARI.match(ch))
            letters = sum(1 for ch in text if ch.isalpha())
            confs = []
            if tsv.exists():
                for line in tsv.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
                    parts = line.split("\t")
                    if len(parts) >= 12 and parts[11].strip() and parts[10] not in ("-1", "conf"):
                        try:
                            c = float(parts[10])
                            if c >= 0: confs.append(c)
                        except ValueError: pass
            stats["pages"].append({
                "page": p, "chars": len(text), "words": len(words),
                "devanagari_ratio": round(dev / letters, 3) if letters else 0.0,
                "mean_conf": round(sum(confs) / len(confs), 1) if confs else None,
                "low_conf_words": sum(1 for c in confs if c < 60),
                "seconds": round(time.time() - t0, 1)})
            stats["pages_done"] += 1
    (work / "src.pdf").unlink(missing_ok=True)
    (outdir / "ocr.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--engine", choices=["auto", "native", "docker"], default="auto")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--lang", default="hin+eng")
    ap.add_argument("--limit", type=int, default=0, help="number of GOs (0 = all downloaded)")
    ap.add_argument("--max-pages", type=int, default=0, help="cap pages per GO (0 = all)")
    ap.add_argument("--only", default="", help="comma-separated GOIDs")
    a = ap.parse_args()

    data = Path(a.data); pdfs = sorted((data / "pdf").glob("*.pdf"), key=lambda p: int(p.stem))
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        pdfs = [p for p in pdfs if p.stem in want]
    if a.limit: pdfs = pdfs[:a.limit]
    engine = pick_engine(a.engine)
    print(f"engine={engine} dpi={a.dpi} lang={a.lang} gos={len(pdfs)}", flush=True)
    t0 = time.time(); allstats = []
    for i, pdf in enumerate(pdfs, 1):
        s = ocr_go(pdf.stem, pdf, data / "ocr" / pdf.stem, engine, a.dpi, a.lang, a.max_pages)
        allstats.append(s)
        ok = [p for p in s["pages"] if "chars" in p]
        conf = [p["mean_conf"] for p in ok if p["mean_conf"] is not None]
        print(f"[{i}/{len(pdfs)}] GO {pdf.stem}: {s['pages_done']}/{s['pages_total']} pages, "
              f"mean_conf={round(sum(conf)/len(conf),1) if conf else '-'}, "
              f"chars={sum(p['chars'] for p in ok)}", flush=True)
    (Path(a.data) / "ocr" / "summary.json").write_text(json.dumps(allstats, ensure_ascii=False, indent=1))
    print(f"done in {round(time.time()-t0)}s -> {Path(a.data)/'ocr'/'summary.json'}")


if __name__ == "__main__":
    main()
