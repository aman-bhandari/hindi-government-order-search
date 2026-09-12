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

Every Information Technology and Social Welfare Department order on [go.uk.gov.in](https://go.uk.gov.in),
2001 to 2025. The same pipeline covers the portal's other 59 departments by changing one flag.

| | |
|---|---|
| Departments | 2 of the portal's 61 |
| Orders indexed | 1,365 (Social Welfare 1,057, Information Technology 308) |
| Pages read | 3,943 |
| Passages indexed | 20,677 |
| Mean OCR word confidence | 79% |
| Time to OCR the collection | about 3.5 hours total |
| Time to embed all passages | 158 seconds on a laptop GPU |

The same pipeline covers any of the portal's 60 departments by changing one flag. See `docs/CORPUS.md` for
what these orders are about, and what they cannot answer.

## Measured, not claimed

Full results, including what did not work, are in `docs/RESULTS.md`. Headline retrieval numbers, against 26
questions written by reading the orders plus 4 with no answer in the collection:

| | |
|---|---|
| Correct order ranked first | 35% |
| Correct order within five results | 65% |
| Unanswerable questions correctly declined | 83% |

Top-five accuracy held at 65% when a second department grew the collection 4.75-fold, which is the test of
whether any of this was fitted to the collection it was built on.

`./run.sh eval` re-runs both the retrieval scoring and the slower answer-grounding check, and the interface
shows the result behind the accuracy badge. The OCR assessment that decided this whole approach is in
`docs/gate.md`; the reasoning behind each design choice is in `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`.

## Third-party components

Tesseract OCR (Apache 2.0), Poppler (GPL, invoked as a binary), FastAPI, SQLite FTS5, sentence-transformers
with BAAI/bge-m3 (MIT), React, Vite, Tailwind, Playwright. Optional: Ollama with Qwen2.5, or the Anthropic API.
No order text is sent anywhere unless the Claude API provider is explicitly selected.

## Limitations

Stated plainly, because a government tool that oversells itself is worse than one that underperforms honestly.

- **Two departments of 61.** Extending is running time, not new work: about 3.5 hours of OCR per 1,300 orders.
- **A local 7B model struggles to pick the right passage from six** once the collection is large. It answered
  44% of answerable questions on two departments against 58-65% on one. The provider switch exists for this,
  and the same harness measures a stronger model with `PROVIDER=anthropic ./run.sh eval`.
- **OCR averages 81% word confidence**, worst page 29%. Digits are misread constantly, which is why nothing
  that must be exact comes from OCR.
- **Transliterated subjects are the biggest source of misses.** Many subject lines are English spelled
  phonetically in Devanagari, and nothing bridges that to the same question asked in real Hindi.
- **Budget release orders are mostly tables**, which OCR reads poorly. They are indexed but answer badly.
- **Extractive by design.** It quotes or declines. It will not summarise across many orders, because a
  summary cannot be checked against a page, which is the whole point.
- **A local 7B model takes tens of seconds** per answer on a 6 GB laptop GPU. An API model is faster and
  better, at the cost of sending passages off the machine.
