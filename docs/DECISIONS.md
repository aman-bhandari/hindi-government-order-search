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
- 2026-09-12 Search collapses passages sharing (order number, page). The portal republishes 9 of 308 IT department
  orders under the same number, sometimes as a poorer scan; without collapsing, one query returned 4 results that
  were only 2 distinct pages.
- 2026-09-12 Ollama installed under ~/.local/opt (no sudo, no system change), model qwen2.5:7b-instruct, running on
  the RTX 3050 with CUDA. Default context 4096 tokens on 6 GB VRAM, which is why the answer prompt caps retrieval at
  6 passages.
- 2026-09-12 Abstention is decided by semantic similarity and term overlap, not by the fused ranking score.
  Measured: reciprocal-rank fusion gives the top result an identical score (0.01639) whether the question is
  answerable or nonsense, so the original threshold refused only when there were literally zero matches.
  "Which river is the longest" and "what is the forest fire compensation" both scored the same as a real query.
  Term overlap separates them cleanly (0% versus 50-67%), and cosine similarity takes over once embeddings exist,
  which is what allows a question phrased in different words than the order uses to still be answered.
