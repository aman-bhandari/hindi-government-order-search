# Architecture

## The problem this shape solves

Uttarakhand Government Orders are scanned images of Hindi letters. Two facts drive every decision here:

1. **OCR gets words right and digits wrong.** Measured at 83% mean word confidence, with dates and order
   numbers frequently misread. So nothing that must be exact may come from OCR.
2. **An officer cannot act on an answer they cannot verify.** A citation that says "order 430/2019" is
   worthless if the number was hallucinated or misread. The verification must be visual.

Everything below follows from those two.

## Data flow

| Stage | File | What it does | Why it is like this |
|---|---|---|---|
| Fetch | `scraper/scrape.js` | One POST returns every order for a department with metadata; PDFs fetched same-origin | The portal only supports legacy TLS renegotiation, so command-line tools cannot reach it. Chromium can. The portal also stores two different path shapes; both are normalised |
| Read | `pipeline/ocr.py` | 300 dpi render, Tesseract `hin+eng`, `--psm 3`, word boxes kept | `--psm 3` yields real paragraph blocks (25/page vs 1 at `--psm 6`, same confidence). Boxes are what make visual verification possible. Parallel single-threaded processes beat Tesseract's internal threading |
| Split | `pipeline/chunk.py` | Paragraph passages, split on line boundaries, tight bounding boxes | Page-level passages are too coarse to quote; line-level lose context. Page furniture is dropped because it repeats across thousands of pages and pollutes ranking |
| Index | `pipeline/db.py` | SQLite: orders, pages, passages, FTS5 | No server to run. Metadata columns come from the portal, never OCR |
| Embed | `pipeline/embed.py` | bge-m3 vectors, GPU fp16 | Multilingual in one vector space, so a Hindi question can match English text. An English-only model would break the corpus in half |
| Retrieve | `pipeline/search.py` | FTS5 and vectors fused by reciprocal rank | Officers type both exact administrative phrases and descriptive questions. Reciprocal rank needs no score calibration between BM25 and cosine, which are not comparable |
| Answer | `pipeline/answer.py` | Quote-first JSON, every quote verified verbatim, abstains otherwise | The verification step is what makes citations trustworthy over OCR text |
| Serve | `api/main.py` | Search, answer, page images, highlighted crops | The crop endpoint composites a tint over the passage's box, then crops with padding |
| Show | `ui/` | Ask, cite, prove | Each citation has one button: show me on the scanned page |

## Deliberate omissions

**No vector database.** The corpus is around 10,000 passages. A numpy array and cosine similarity are faster
than a database round trip at this size and add nothing to install.

**No cross-reference graph.** Orders cite each other by number, and this was built and then removed: 9
references extracted from 20 orders, 0 resolvable, because OCR mangles exactly the digits an order number is
made of. Related orders instead come from section, category and date proximity, which OCR cannot corrupt.
Extracted references are still shown, labelled as unverified.

**No summarisation across orders.** The system answers from quoted passages or declines. A summary of many
orders cannot be verified against a page, which would defeat the point.

## Failure behaviour

| If | Then |
|---|---|
| Embeddings have not been built | Search runs keyword-only rather than failing |
| The local model is not running | The interface says so and offers the API provider |
| No passage scores above threshold | It answers "not found" without calling a model |
| A quote cannot be found in its cited passage | That quote is dropped; if none survive, the answer becomes "not found" |
| One PDF is corrupt | That order is skipped with an error recorded; the batch continues |
