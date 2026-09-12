# Status: core complete

Definition of done was set in `../../documents/objective.md` before any code. Against it:

| Core requirement | State |
|---|---|
| Real corpus: all IT Department orders, metadata from the portal, OCR with word boxes, page images kept | Done. 308 orders, 892 pages, 4,345 passages |
| Retrieval: keyword and vector hybrid, filters by category, date and order number, related orders | Done |
| Answering: quote-first with citations, local model, provider switch for an API, refusal when unsupported | Done. Refuses 100% of unanswerable questions |
| Interface: ask in Hindi or English, scanned page crop with supporting lines highlighted, related orders, accuracy page | Done |
| Ship: README with architecture and third-party disclosure, demo script, registration text ready | README, architecture, results, demo script and registration draft written |

## What is left for Aman

1. **Record the three-minute demo video.** Script is in `docs/DEMO.md`. This needs a screen recording, which
   is the one step that cannot be automated here.
2. **Decide whether to register**, and when. Draft text is in `docs/REGISTRATION-DRAFT.md`. No hackathon stage
   dates have been published anywhere; the WhatsApp community is the only announcement channel.
3. **Optional: host a read-only demo** so the registration form's prototype URL can be filled. The rules also
   accept source code or a video instead.

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
cd ~/workshop/ukis-p001
./run.sh serve       # http://127.0.0.1:8000  (interface is served from the same port)
```
Ollama must be running for local answers: `~/.local/bin/ollama serve`.
