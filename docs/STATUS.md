# Status: core complete

The definition of done was set before any code. Against it:

| Core requirement | State |
|---|---|
| Real corpus: orders from the portal, metadata from the portal, OCR with word boxes, page images kept | Done. Two departments, 1,365 orders, 3,943 pages, 20,677 passages |
| Retrieval: keyword and vector hybrid, filters by category, date and order number, related orders | Done |
| Answering: quote-first with citations, local model, provider switch for an API, refusal when unsupported | Done. Refuses most questions it cannot answer; the exact rate is being re-measured on a larger set after run-to-run variance was found |
| Interface: ask in Hindi or English, scanned page crop with supporting lines highlighted, related orders, accuracy page | Done |
| Ship: README with architecture and third-party disclosure, demo script, registration text ready | README, architecture, results, demo script and registration draft written |

## If you want to go further

In rough order of value per hour:

- **Index a second department.** Change one flag. Finance or Social Welfare would show the approach is not
  tuned to one collection. Roughly 40 minutes of OCR per 300 orders.
- **Improve the transliteration problem**, the largest measured cause of retrieval misses. Indexing a
  romanised form of each subject line alongside the original would likely help, and is cheap to test.
- **Try a stronger answer model** through the API switch. The verification harness already exists, so the
  effect on grounding can be measured rather than guessed: `PROVIDER=anthropic ./run.sh eval`.
- **Expand the question set** beyond 30. The current numbers have wide error bars at this size.

## Running it right now

```bash
cd hindi-government-order-search
./run.sh serve       # http://127.0.0.1:8000  (interface is served from the same port)
```
Ollama must be running for local answers: `ollama serve`.
