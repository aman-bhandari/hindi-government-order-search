#!/usr/bin/env bash
# One command to bring the whole thing up or to rebuild it from scratch.
#   ./run.sh serve     start the API (and UI if built)
#   ./run.sh build     scrape -> OCR -> chunk -> embed  (long; safe to re-run, it resumes)
#   ./run.sh ui        start the UI dev server
#   ./run.sh eval      run the gold-set evaluation
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate

case "${1:-serve}" in
  build)
    echo "1/4 metadata + PDFs"
    ~/.claude/browser/run.sh scraper/scrape.js --dept "${DEPT:-17}"
    echo "2/4 OCR (resumable; ~38 min for 892 pages with 12 workers)"
    python pipeline/ocr.py --engine "${ENGINE:-auto}" --workers "${WORKERS:-0}"
    echo "3/4 chunks + references"
    python pipeline/db.py
    python pipeline/chunk.py
    echo "4/4 embeddings"
    python pipeline/embed.py --quiet || echo "embeddings skipped; search will run keyword-only"
    ;;
  serve)
    exec uvicorn api.main:app --host 127.0.0.1 --port "${PORT:-8000}"
    ;;
  ui)
    cd ui && npm install && exec npm run dev
    ;;
  eval)
    python eval/gold.py run
    echo
    echo "answer grounding (slow: one local model call per question)"
    python eval/answer_eval.py --provider "${PROVIDER:-ollama}"
    ;;
  *)
    echo "usage: ./run.sh [build|serve|ui|eval]"; exit 1;;
esac
