# Government Order Knowledge Repository (शासनादेश खोज)

UKIS 2026, problem P-001 (Information Technology Development Agency, Uttarakhand).

Search and question answering over scanned Hindi Government Orders from go.uk.gov.in. A question in Hindi or
English returns quoted passages with order number, date and page, and shows the quoted lines highlighted on the
scanned page. Runs on one machine; no cloud service required.

## What is in this repository

| Path | Contents |
|---|---|
| `scraper/scrape.js` | Downloads order metadata and PDFs from the portal (Playwright + Chromium; the portal only speaks legacy TLS) |
| `pipeline/ocr.py` | Renders pages at 300 dpi, Tesseract hin+eng, keeps word boxes |
| `pipeline/db.py`, `chunk.py`, `embed.py` | SQLite store with FTS5, paragraph passages, bge-m3 vectors |
| `pipeline/search.py` | Keyword + vector search fused by reciprocal rank; filters by category, date, order number |
| `pipeline/answer.py` | Answer from retrieved passages via Ollama or the Anthropic API; quotes verified against the passage; "not found" when unsupported |
| `api/main.py` | FastAPI: search, ask, page image, evidence crop, eval results; serves `ui/dist` |
| `ui/` | React + Vite interface, Hindi and English |
| `eval/` | Gold question set, retrieval scorer, answer-grounding scorer |
| `data/meta/` | Portal metadata for both departments (committed) |
| `docs/` | STATUS, RESULTS, ARCHITECTURE, DECISIONS, CORPUS, DEMO, REGISTRATION-DRAFT, OBJECTIVE, PLAN, gate |
| `docker/ocr.Dockerfile` | Tesseract + Poppler image for hosts without them |

## Status (25 September 2026)

| Item | State |
|---|---|
| Corpus | 2 of 61 departments: Social Welfare 1,057 orders, Information Technology 308; 3,943 pages; 20,677 passages |
| Search | Done: Hindi or English query, filters, related orders |
| Answers | Done: local Qwen2.5-7B via Ollama or Anthropic API; quotes verified; refusal when unsupported |
| Interface | Done: ask, results, scanned-page crop with highlighted lines, accuracy page |
| Evaluation | Done: 26 answerable + 12 unanswerable questions, `./run.sh eval` |
| Unit tests | None; the evaluation harness is the check |
| Demo video, hosted demo, registration | Not done |

Acceptance table: `docs/STATUS.md`. Design decisions: `docs/DECISIONS.md`.

## Results

| Measure | Value |
|---|---|
| Correct order within top 5 | 65% |
| Correct order ranked first | 35% |
| Unanswerable questions refused | 83% |
| Answerable questions answered, local 7B model, two departments | 44% |
| Mean OCR word confidence | 79% |
| OCR time, both departments | about 3.5 h |
| Embedding time | 158 s on a laptop GPU |

Top-5 stayed at 65% when the corpus grew from one department to two. Four retrieval ideas (phonetic matching,
subject expansion twice, topical gate) were built and measured; none improved results. Details: `docs/RESULTS.md`.

## Run

Tested on Ubuntu (WSL2), 16 GB RAM, RTX 3050 6 GB. The GPU is optional.

| Requirement | Note |
|---|---|
| Python 3.12+ | tested 3.14 |
| Node 20+ | tested 24; interface and scraper |
| tesseract-ocr, tesseract-ocr-hin, poppler-utils | or `docker build -t ukis-ocr-spike -f docker/ocr.Dockerfile .` |
| Playwright Chromium | scraper only |
| Ollama with `qwen2.5:7b-instruct` (5 GB), or `ANTHROPIC_API_KEY` | answers only; search works without |
| Disk | quick start under 1 GB; full corpus about 12 GB |
| Internet | portal scrape; bge-m3 download (about 2 GB) on first build |

Quick start, 20 orders, about 10 minutes:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
npm install && npx playwright install chromium
sudo apt install -y tesseract-ocr tesseract-ocr-hin poppler-utils
LIMIT=20 ./run.sh build
./run.sh ui
./run.sh serve            # http://127.0.0.1:8000
```

Full corpus:

```bash
DEPT=17  ./run.sh build   # Information Technology, about 1 h
DEPT=203 ./run.sh build   # Social Welfare, about 3.5 h
./run.sh eval             # retrieval 2 min; answers 20-40 min with the local model
```

Every stage resumes. On 16 GB run one heavy job at a time and stop Ollama before OCR. `WORKERS=6` caps OCR
processes. Generated, not committed: `data/pdf/`, `data/ocr/`, `data/gos.db`, `data/chunk_vectors.npy`.

## Design rules

- Order number, date, department and category come from portal metadata, never from OCR.
- Each quote is checked word for word against the indexed passage; failing quotes are dropped.
- The scanned page crop is shown for every quote.
- No supporting passage: the answer is "not found".
- Related orders come from section, category and date, not from OCR digits.
- Extractive only: it quotes or refuses; no summaries across orders.

## Third-party components

Tesseract OCR (Apache-2.0), Poppler (GPL, run as a binary), FastAPI, SQLite FTS5, sentence-transformers with
BAAI/bge-m3 (MIT), React, Vite, Tailwind, Playwright. Optional: Ollama with Qwen2.5, Anthropic API. Order text
leaves the machine only when the Anthropic provider is selected.

## Limits

- 2 of 61 departments; about 3.5 h of OCR per 1,300 orders to add one.
- Local 7B model: 44% of answerable questions on two departments (58-65% on one); tens of seconds per answer on a 6 GB GPU.
- OCR word confidence 79% mean, 29% on the worst page; digits are often misread.
- Subject lines written as English in Devanagari script are the main cause of retrieval misses.
- Table-heavy budget orders OCR poorly.
