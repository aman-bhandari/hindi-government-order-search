# Project objective (approved by Aman, 12 Sep 2026)

**Build the best possible solution for UKIS 2026 problem P-001 (AI-Powered Government Knowledge Repository) on
this laptop.** Confirmed by Aman 12 Sep 2026: "first build then we'll discuss entry" — so registration is NOT
part of the objective and is not to be raised again until he opens it. The Devbhoomi AI Summit is context only,
no action. Fallback/next problem: P-003 (core already approved).

Approved improvements after core completion (12 Sep 2026): (1) index a second department, (2) fix the
transliteration misses, (3) improve answer accuracy.

Constraints: solo (Aman is lead and only member); Claude Code Max + Cursor Pro are build tools; runtime LLM local
(Ollama) with an API-key switch; no paid services assumed; sessions are unpredictable so every plan step is under
one hour; core scope only until it is demoable end to end; no registration until Aman says so; no subagents.

Core (definition of done):
1. Real corpus: all 308 IT Department GOs from go.uk.gov.in, metadata from the portal API, PDFs OCR'd (Hindi+English)
   with word boxes, page images kept.
2. Retrieval: hybrid BM25 + bge-m3 vectors; filters by category, date, GO number; related GOs from GO-number mentions.
3. Answering: quote-first answers with citations (GO no., date, page) from a local model, provider switch for an API;
   "not found" abstention.
4. UI: ask in Hindi or English; results with the scanned page crop and highlighted supporting lines; related GOs;
   an accuracy page showing hit-rate on a 30-question gold set.
5. Ship: README with architecture and third-party disclosure, 3-minute demo video, registration text ready.

Gate: after the first 20 GOs are scraped and OCR'd (under one hour), if OCR quality is poor we switch to P-003.
