#!/usr/bin/env bash
# Government Order Knowledge Repository — one entry point for everything.
#   ./run.sh serve            API + interface on http://127.0.0.1:8000 (needs ui/dist: run ./run.sh ui once)
#   ./run.sh build            scrape -> OCR -> chunk -> embed. Long; safe to re-run, every stage resumes.
#                             LIMIT=20 ./run.sh build     quick start: 20 orders of one department, about 10 minutes
#                             DEPT=203 ./run.sh build     another department (17 = Information Technology, 203 = Social Welfare)
#   ./run.sh scrape           metadata + PDFs only (Chromium via Playwright: npm install && npx playwright install chromium)
#   ./run.sh ui               build the interface into ui/dist
#   ./run.sh dev              Vite dev server on http://127.0.0.1:5173 (proxies /api to 8000)
#   ./run.sh eval             retrieval scoring, then answer grounding (PROVIDER=ollama|anthropic)
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate

# Playwright scripts run with the repo's own node_modules; a global launcher is used only as a fallback.
pw() {
  if [ -d node_modules/playwright ]; then node "$@"
  else echo "Playwright is not installed here. Run:  npm install && npx playwright install chromium"; exit 1; fi
}

case "${1:-serve}" in
  scrape)
    pw scraper/scrape.js --dept "${DEPT:-17}" --limit "${LIMIT:-0}" ;;
  build)
    echo "1/4 metadata + PDFs"
    pw scraper/scrape.js --dept "${DEPT:-17}" --limit "${LIMIT:-0}"
    echo "2/4 OCR (resumable; ~38 min for 892 pages with 12 workers)"
    python pipeline/ocr.py --engine "${ENGINE:-auto}" --workers "${WORKERS:-0}"
    echo "3/4 chunks + references"
    python pipeline/db.py
    python pipeline/chunk.py
    echo "4/4 embeddings"
    python pipeline/embed.py --quiet || echo "embeddings skipped; search will run keyword-only"
    ;;
  serve)
    [ -d ui/dist ] || echo "ui/dist missing: the API will run without the interface (./run.sh ui builds it)"
    exec uvicorn api.main:app --host 127.0.0.1 --port "${PORT:-8000}"
    ;;
  ui)
    (cd ui && npm install --silent && npm run build) ;;
  dev)
    (cd ui && npm install --silent && exec npm run dev) ;;
  eval)
    python eval/gold.py run
    echo
    echo "answer grounding (slow: one local model call per question)"
    python eval/answer_eval.py --provider "${PROVIDER:-ollama}"
    ;;
  *)
    echo "usage: ./run.sh [serve|build|scrape|ui|dev|eval]"; exit 1;;
esac
