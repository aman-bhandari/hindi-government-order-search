# शासनादेश खोज — Government Order Knowledge Repository

**UKIS 2026 · Problem P-001 · Information Technology Development Agency, Uttarakhand**

Ask a question in Hindi or English about Uttarakhand Government Orders and get an answer built only from
quoted text, with each quote shown highlighted on the original scanned page.

The orders are scanned Hindi letters going back to 2002. They are searchable on the official portal only by
department, category, date or order number — you must already know which order you want. This makes the
contents searchable, and keeps every claim traceable to an image of the page it came from.

## What makes the answers trustworthy

| Problem with AI over scanned records | What this does |
|---|---|
| A model can fabricate a plausible order number or date | Order number, date, department and category come from the portal's own metadata, never from OCR |
| A model can paraphrase a quote until it says something the page does not | Every quote is checked word for word against the indexed passage after generation; quotes that fail are dropped |
| OCR of a scanned page is never perfect | The officer sees the scan itself, cropped to the exact lines quoted, and can verify in a glance |
| A model will answer even when it should not | If no passage supports an answer, it says so instead of guessing |
| Digits in scans are misread constantly | Nothing depends on OCR digits: related orders come from section, category and date, not from cited numbers |

## Running it

Everything runs on one machine. No cloud service is required, including for the answer model.

```bash
./run.sh build     # scrape, OCR, chunk, embed. Long, resumable.
./run.sh serve     # API on http://127.0.0.1:8000
./run.sh ui        # UI on http://127.0.0.1:5173
```

Prerequisites: Python 3.12+, Node 20+, and either a native OCR install
(`sudo apt install -y tesseract-ocr tesseract-ocr-hin poppler-utils`) or Docker.
For local answers, install [Ollama](https://ollama.com) and `ollama pull qwen2.5:7b-instruct`.
To use Claude instead, set `ANTHROPIC_API_KEY` and pick "Claude API" in the interface.

## How it works

```
GO MIS portal ──► scraper/scrape.js ──► PDFs + metadata
                                          │
                    pipeline/ocr.py ──────┤  300 dpi render, Tesseract hin+eng,
                                          │  word boxes kept for highlighting
                  pipeline/chunk.py ──────┤  paragraph passages, tight bounding boxes
                  pipeline/embed.py ──────┤  bge-m3 multilingual vectors
                                          ▼
                 pipeline/search.py ──►  FTS5 keyword + vectors, fused by reciprocal rank
                 pipeline/answer.py ──►  local or API model, quotes verified before display
                      api/main.py ──────►  search, answer, page images, highlighted crops
                            ui/ ────────►  ask, cite, prove
```

The scraper needs Chromium: the portal only supports legacy TLS renegotiation, which command-line tools refuse.

## Corpus

Information Technology Department orders from [go.uk.gov.in](https://go.uk.gov.in), June 2002 to May 2025.
The same pipeline works for any of the portal's 60 departments by changing one flag.

## Measured, not claimed

`./run.sh eval` scores retrieval against questions written by hand from real orders in the corpus, and the
interface shows the result. The OCR quality assessment that decided this approach is in `docs/gate.md`.

## Third-party components

Tesseract OCR (Apache 2.0), Poppler (GPL, invoked as a binary), FastAPI, SQLite FTS5, sentence-transformers
with BAAI/bge-m3 (MIT), React, Vite, Tailwind, Playwright. Optional: Ollama with Qwen2.5, or the Anthropic API.
No order text is sent anywhere unless the Claude API provider is explicitly selected.

## Limitations

- One department is indexed. Extending to all 60 is a matter of running time, not new work.
- OCR confidence averages 83%; digits inside scans are frequently misread, which is why nothing depends on them.
- Budget release orders are mostly tables, which OCR reads poorly. They are indexed but rank low.
- Answers are extractive by design. It will not summarise across many orders or draft new text.
