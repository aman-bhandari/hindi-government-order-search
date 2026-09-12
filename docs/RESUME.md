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
