# Decisions log
- 2026-09-12 Objective locked: P-001 first, P-003 fallback (see ../../documents/objective.md).
- 2026-09-12 Stack: Playwright (Chromium via ~/.claude/browser/run.sh, needed for go.uk.gov.in legacy TLS) -> pdftoppm +
  Tesseract hin+eng (native apt) -> SQLite (metadata + FTS5) + numpy embeddings (bge-m3) -> Ollama (qwen2.5:7b) with
  Anthropic API switch -> FastAPI -> Vite React + Tailwind. No vector DB (corpus ~10k chunks).
- 2026-09-12 Corpus scope for core: IT Department only (308 GOs). Metadata (GO no., date, category) always from the
  portal API, never from OCR.
- 2026-09-12 OCR uses `--psm 3` (automatic page segmentation), not `--psm 6`. Measured on a real GO page: psm 3 yields
  25 paragraph blocks vs 1 for psm 6, at identical confidence (84.3% vs 84.4%). Paragraph blocks are what make
  chunk-level evidence highlighting possible.
- 2026-09-12 GO cross-reference mining from OCR text is DEMOTED from a core feature. Measured: 9 references extracted
  from 20 GOs, 0 resolvable to a known GO number, because OCR mangles exactly the digits a GO number consists of
  ("777||7772(2)/2076/30(72)/2078"). Core "related GOs" will instead use embedding similarity plus shared
  section/category/date proximity, which does not depend on digit accuracy. Extracted references are kept in the
  `refs` table and may be shown as an unverified hint, never as a link.
