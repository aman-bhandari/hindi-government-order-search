# Project objective (12 Sep 2026)

Build the best possible solution for UKIS 2026 problem P-001 (AI-Powered Government Knowledge Repository) on one
laptop. Registration is not part of the objective. Fallback/next problem: P-003.

Improvements agreed after core completion (12 Sep 2026): (1) index a second department, (2) fix the
transliteration misses, (3) improve answer accuracy.

Constraints: solo entry; runtime LLM local (Ollama) with an API-key switch; no paid services assumed; every plan
step under one hour; core scope only until it is demoable end to end.

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
