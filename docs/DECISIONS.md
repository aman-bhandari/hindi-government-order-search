# Decisions log
- 2026-09-12 Objective locked: P-001 first, P-003 fallback (see ../../documents/objective.md).
- 2026-09-12 Stack: Playwright (Chromium via ~/.claude/browser/run.sh, needed for go.uk.gov.in legacy TLS) -> pdftoppm +
  Tesseract hin+eng (native apt) -> SQLite (metadata + FTS5) + numpy embeddings (bge-m3) -> Ollama (qwen2.5:7b) with
  Anthropic API switch -> FastAPI -> Vite React + Tailwind. No vector DB (corpus ~10k chunks).
- 2026-09-12 Corpus scope for core: IT Department only (308 GOs). Metadata (GO no., date, category) always from the
  portal API, never from OCR.
