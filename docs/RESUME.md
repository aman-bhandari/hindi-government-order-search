# Resuming after the break

Stopped 12 September 2026. Nothing was lost: every long job is resumable and re-running it skips finished work.

## Where things were left

| | |
|---|---|
| Committed | 20 commits, working tree clean |
| Indexed and searchable | 308 Information Technology orders, 892 pages, 4,345 passages |
| Metadata loaded | 1,383 orders across two departments |
| Social Welfare PDFs downloaded | 867 of 1,075, not yet OCR'd |
| Answer evaluation of the subject-expansion fix | reached question 5 of 30, incomplete, do not trust `data/answer_eval2.log` |
| Last trustworthy answer numbers | `data/answer_eval.json`, measured before the fix |

## Restart in this order

```bash
cd ~/workshop/ukis-p001

# 1. the local answer model (needed for answering, not for search)
~/.local/bin/ollama serve &

# 2. finish the Social Welfare download, then OCR it. Both skip completed work.
~/.claude/browser/run.sh scraper/scrape.js --dept 203        # resumes at 867 of 1,075
python pipeline/ocr.py --engine native --workers 12          # ~2 h for about 3,200 pages
python pipeline/db.py && python pipeline/chunk.py            # rebuild index over both departments
python pipeline/embed.py --quiet

# 3. the service and interface
./run.sh serve                                               # http://127.0.0.1:8000
```

## The one measurement still owed

The subject-expansion fix is committed but its effect on answers was never measured to completion. Re-run:

```bash
python eval/gold.py run                    # retrieval, about 2 minutes
python eval/answer_eval.py --provider ollama   # answers, about 20 minutes
```

Before the fix: 65% answered, 31% cited the expected order, 72% of quotes verified, 100% of unanswerable
questions declined. Note that once Social Welfare is indexed, these numbers are measured against a larger
and harder collection, so a drop does not necessarily mean the fix failed. If you want a clean comparison,
run the evaluation before rebuilding the index with the second department.

## Notes

- The Playwright browser server was stopped along with the scraper. It reconnects on demand; if browser tools
  are needed in a session and fail, restarting the session restores them.
- Ollama lives at `~/.local/opt/ollama` with a symlink at `~/.local/bin/ollama`. No system packages were
  changed except `tesseract-ocr`, `tesseract-ocr-hin` and `poppler-utils`.
- Disk in use: about 2.1 GB of page images and PDFs under `data/`, all gitignored and all regenerable.


## Update after the second session

Done: Social Welfare fully downloaded (1,058 of 1,075; 17 are absent from the portal). Subject expansion
tried twice and reverted, both measured worse. Unanswerable question set tripled to twelve after finding
large run-to-run variance. Topical-fit gate added.

Owed, in order:

1. **Score the topical-fit gate.** `python eval/answer_eval.py --provider ollama` on all 38 questions,
   roughly 40 minutes on a quiet machine. The last attempt died at 6 of 38 when swap filled.
2. **OCR Social Welfare**, about 3,100 pages. Stop Ollama first, it holds 5 GB, and use fewer workers than
   12 on this machine: `python pipeline/ocr.py --engine native --workers 6`.
3. Rebuild and re-embed across both departments, then re-measure retrieval on the larger collection.

**Memory is the binding constraint on this laptop.** With the answer model loaded, plus the Next.js server
and two dotnet processes belonging to other work, 11 GB of RAM and 8 GB of swap were exhausted and load
average reached 146. Run one heavy job at a time.


## Update after the third session (13 September 2026)

The system is finished and both departments are indexed. Nothing is mid-flight.

| | |
|---|---|
| Departments indexed | Social Welfare (1,057) and Information Technology (308) |
| Pages read, passages | 3,943 and 20,677 |
| Correct order in top five | 65%, unchanged after the collection grew 4.75-fold |
| Unanswerable questions declined | 83% |

To bring it back up:

```bash
cd ~/workshop/ukis-p001
./run.sh serve                 # http://127.0.0.1:8000, browsing and search work without a model
~/.local/bin/ollama serve &    # only needed for "Answer with citations"; holds about 5 GB
```

Nothing is owed. If you want to go further, the honest ranking of what would pay:

1. **Try a stronger answer model.** The measured weakness is a 7B model picking the right passage from six
   once the collection is large. `PROVIDER=anthropic ./run.sh eval` scores it with the same harness.
2. **Add more departments.** About 3.5 hours of OCR per 1,300 orders; stop Ollama first and use six workers,
   because memory is the binding constraint on this laptop.
3. Leave retrieval alone. Four ideas were built and measured against it; none improved on what is there.
