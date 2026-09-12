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
- 2026-09-12 Quote verification compares words only, ignoring punctuation and markup. Observed: OCR of a budget
  table renders a row number as "|[6. |", and the model reading that excerpt tidied it to "6." — a faithful quote
  rejected over punctuation. Word-only comparison still requires the same words in the same order, so a paraphrase
  with changed wording is refused (verified with three test cases).
- 2026-09-12 Semantic threshold for answering set to 0.42 from measurement, not intuition. With bge-m3, questions
  answerable from these orders scored 0.469-0.607 against the correct passage; off-topic questions (longest river,
  old age pension, forest fire compensation) peaked at 0.371. The initial guess of 0.50 sat above the answerable
  minimum and would have refused legitimate questions.
- 2026-09-12 Refusal cannot be decided by a retrieval threshold on this corpus, and the attempt to do so was
  abandoned after measurement. Across 26 answerable and 4 unanswerable questions, best-passage cosine similarity
  was 0.453-0.697 for answerable and 0.478-0.571 for unanswerable: overlapping. The best possible single cutoff
  kept 22/26 real questions while refusing only 2/4 bogus ones. A corpus-vocabulary check failed the same way
  (answerable from 0.62 of terms present, unanswerable up to 1.00), because administrative Hindi shares its
  common vocabulary regardless of subject. The similarity gate is therefore only a cheap filter to avoid a slow
  model call on something with no footing at all; refusal is decided by the model reading the passages, with
  every quote verified against them. That end-to-end refusal rate is what eval/answer_eval.py measures.
- 2026-09-12 The order's subject line is indexed as a passage of its own, flagged 'subject' rather than 'ocr'.
  Many one-page orders OCR to little more than letterhead while the portal's subject line states plainly what the
  order is about, and it is clean human-entered metadata that OCR cannot corrupt. Measured effect on retrieval:
  correct order ranked first rose from 27% to 42%, correct order in the top five from 50% to 58%.
- 2026-09-12 Search returns at most two passages per order. Three long policy documents hold 458 of 4,345 passages
  (one 38-page order alone contributes 236), so on broad queries they filled every result slot and short one-page
  orders were unreachable. Measured effect: correct order in the top five rose from 58% to 65%.
- 2026-09-12 The query encoder runs on CPU by default (EMBED_DEVICE=cuda overrides). Observed failure: with the
  answer model, the API's encoder and an evaluation run all holding GPU memory, the card sat at 5806 of 6144 MiB
  and vector search stalled for 60 seconds rather than failing. Indexing all 4,345 passages was a one-time GPU
  job; a query encodes one short string, which CPU does in tens of milliseconds. The API also warms the encoder
  at startup so the first search is not the request that pays for loading it.
