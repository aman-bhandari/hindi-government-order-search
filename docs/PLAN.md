# P-001 execution plan — every step under one hour (12 Sep 2026)

Repo: this repository. Python 3.14 venv for pipeline + API; Node 24 for scraper and UI.
Stack (pragmatic, all local): Playwright (Chromium, needed for go.uk.gov.in legacy TLS) -> pdftoppm + Tesseract
hin+eng (hOCR/TSV word boxes) -> SQLite (metadata + FTS5 BM25) + numpy embeddings from bge-m3 (GPU) -> Ollama
qwen2.5:7b-instruct (or gemma3:4b) with Anthropic API switch -> FastAPI -> Vite React UI.
No vector DB: ~10k chunks fit in memory; keeps setup to zero servers.

## Phase 0 — Setup and gate (4 steps)
| Step | Do | Output | Est |
|---|---|---|---|
| 0.1 | git init, venv, requirements (pypdf, pytesseract, sentence-transformers, fastapi, uvicorn, numpy), package.json (playwright) | repo skeleton, README stub | 30 min |
| 0.2 | OCR engine: either `sudo apt install tesseract-ocr tesseract-ocr-hin poppler-utils` or the Docker image | `tesseract --list-langs` shows hin | 15 min |
| 0.3 | Playwright scraper: POST SearchGO for IT Dept, save `data/meta.json` (308 rows), download first 20 PDFs to `data/pdf/` | 20 PDFs + metadata | 45 min |
| 0.4 | OCR the 20: 300 dpi pages -> text + TSV boxes -> `data/ocr/<GOID>/page-N.{txt,tsv,png}`; quality report (chars/page, Devanagari ratio, 5 eyeballed pages) | **GATE report** | 45 min |

## Phase 1 — Full corpus (4 steps)
| 1.1 | Download remaining 288 PDFs with retries and a manifest | data/pdf complete | 30 min |
| 1.2 | Batch OCR runner (resumable, 2 workers, logs) — start it, let it run unattended | OCR for all pages | 30 min to start; ~2-3 h wall unattended |
| 1.3 | Chunker: page -> paragraphs (Hindi danda/newline aware), keep page no. + box spans; write `chunks` table | SQLite `chunks` | 45 min |
| 1.4 | ~~GO-number reference extractor~~ **demoted** (OCR digits unreliable: 0/9 refs resolvable). Replaced by 2.5 below | refs kept as unverified hint | done |

## Phase 2 — Retrieval (4 steps)
| 2.1 | bge-m3 embeddings for all chunks (GPU fp16), save `.npy` + ids | embeddings | 45 min |
| 2.2 | FTS5 BM25 index; hybrid scorer (reciprocal rank fusion); `search(query, filters)` function | search() | 45 min |
| 2.3 | Filters: category, date range, GO number, year; cross-lingual check (English query -> Hindi chunk) | filtered search | 30 min |
| 2.5 | Related GOs by embedding similarity + shared section/category/date window | related-GO panel | 30 min |
| 2.4 | Gold set: 30 questions with expected GOID/page written from real GOs (15 Hindi, 15 English); `eval.py` hit@1/hit@5 | baseline numbers | 60 min (2 x 30) |

## Phase 3 — Answering (4 steps)
| 3.1 | Install Ollama and pull qwen2.5:7b-instruct (and gemma3:4b as backup) | `ollama run` works | 20 min |
| 3.2 | Quote-first prompt: model must return JSON {answer, quotes:[{chunk_id, text}], confidence}; cite only retrieved chunks | answer() | 45 min |
| 3.3 | Provider switch: `LLM_PROVIDER=ollama|anthropic`; same JSON contract | switchable | 30 min |
| 3.4 | Abstention: if top score below threshold or quotes not grounded -> "not found in IT Dept GOs" | failure path | 30 min |

## Phase 4 — UI (6 steps)
| 4.1 | FastAPI: /search, /answer, /go/{id}, /page/{id}/{n}.png, /crop (boxes -> highlighted PNG) | API | 45 min |
| 4.2 | Vite React + Tailwind shell: ask box (Hindi/English), filters, results list | UI skeleton | 45 min |
| 4.3 | Answer card: quotes with GO no./date/page badges; click -> evidence panel | evidence flow | 45 min |
| 4.4 | Evidence panel: page image with highlighted supporting words (from TSV boxes), zoom | the differentiator | 60 min |
| 4.5 | Related GOs panel (references table) + GO detail page (metadata, all pages) | navigation | 45 min |
| 4.6 | Accuracy page: gold-set results table, last run date | trust signal | 30 min |

## Phase 5 — Ship (4 steps)
| 5.1 | README: problem, architecture diagram, how to run offline, third-party components disclosed (T&C 6.2) | README | 30 min |
| 5.2 | Demo script + 3-minute screen recording (Hindi query, English query, not-found, related GOs, accuracy page) | video | 45 min |
| 5.3 | Registration text: title, description (approach, differentiators, limits), prototype URL if any — **not submitted** | draft | 30 min |
| 5.4 | Optional: free-tier hosting of a read-only demo (stretch) | URL | stretch |

Core total: 26 steps, roughly 20-24 working hours plus unattended OCR time.
Stretch (only after 5.3): add Finance + Social Welfare departments; Hindi-language answers; reranker; officer feedback
loop; role-based access.

## Decisions taken before step 0.1
1. OCR engine: native apt install; Docker image as the fallback.
2. UI stack: Vite React + Tailwind.
3. Repo location and name: ukis-p001.
