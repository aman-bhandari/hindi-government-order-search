# Results

Everything here was measured on this laptop against the real corpus. Where a number is poor it is stated as
it is, because a government tool that overstates itself is worse than one that underperforms honestly.

## The corpus

| | |
|---|---|
| Orders indexed | 308 of 308 published for the department |
| Date range | 24 June 2002 to 14 May 2025 |
| Scanned pages read | 892 |
| Passages indexed | 4,345 |
| Mean OCR word confidence | 81% (worst page 29%) |
| OCR time | 38 minutes, 12 parallel workers, native Tesseract |
| Embedding time | 34 seconds, laptop GPU |
| Query latency | under 3 seconds, encoder on CPU |

## Finding the right order

26 questions written by reading the orders (15 Hindi, 11 English), plus 4 with no answer in this collection.
Method and rules in `eval/questions_seed.md`. Re-run with `./run.sh eval`.

| Measure | Result |
|---|---|
| Correct order ranked first | 42% |
| Correct order within five results | 65% |
| Correct page within five results | 46% |

How it got there, each step measured rather than assumed:

| Change | Order first | Order in top five |
|---|---|---|
| OCR text only | 27% | 50% |
| Accept duplicate-subject orders as correct | 27% | 54% |
| Index the portal's subject line as a passage | 42% | 58% |
| Cap results at two passages per order | 42% | 65% |

## Why the remaining misses happen

The largest single cause is transliteration. Many subject lines are English spelled phonetically in
Devanagari: "उत्तराखंड गर्वमेंट एसेट मैंनेजमैंट सिस्ट्म पोर्ट्ल" is "Uttarakhand Government Asset Management
System Portal". Neither keyword matching nor a multilingual embedding reliably bridges that to the same
question asked in real Hindi. Asking in English finds those orders.

## What could not be made to work

Two approaches were built, measured, and removed. Both are recorded because knowing what fails on scanned
Hindi records is worth as much as knowing what works.

**Cross-references between orders.** Orders cite each other by number, which would make a citation graph.
Of 9 references extracted from 20 orders, 0 could be resolved: OCR mangles precisely the digits an order
number consists of, rendering one as "777||7772(2)/2076/30(72)/2078". Related orders are found through
section, category and date instead, which OCR cannot corrupt.

**Deciding refusal from retrieval scores.** Answerable questions scored 0.453 to 0.697 in similarity to the
best passage; unanswerable ones scored 0.478 to 0.571. The distributions overlap, and the best possible
single cutoff kept 22 of 26 real questions while refusing only 2 of 4 bogus ones. A corpus-vocabulary test
failed the same way, because administrative Hindi shares its common words whatever the subject. Refusal is
therefore decided by the model reading the passages, with every quote verified against them.
