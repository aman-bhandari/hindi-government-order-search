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

## Answering from what was found

The same 30 questions, each sent through the full pipeline with the local model (Qwen2.5 7B, on the laptop
GPU). Median 20 seconds per answer. Re-run with `./run.sh eval`.

| Of the 26 questions answerable from this collection | |
|---|---|
| Answered rather than declined | 65% |
| Cited the order the question was written from | 31% |
| Quotes that survived verbatim verification | 72% (18 kept, 7 dropped) |

| Of the 4 questions with no answer in this collection | |
|---|---|
| Correctly declined | **100%** |

The last number is the one that matters most for a government tool, and it is worth being precise about
where it comes from. It is not produced by a confidence threshold, which was measured and found incapable of
the job. It comes from two things working together: the model is given only the retrieved passages and told
to say when they do not answer the question, and every quote it produces is then checked word for word
against the passage it cited. A question about forest fire compensation, pension eligibility, Char Dham
registration or hospital beds retrieved plausible-looking administrative prose in all four cases, and was
refused in all four.

The cost of that strictness is visible too: of the 9 answerable questions it declined, 6 declined because the
model's only quote failed verification. Those are answers a looser system would have given, some of them
correct. The trade was made deliberately in favour of never presenting an unverifiable claim as sourced.

## A third thing that did not work: phonetic matching

Transliterated subject lines are the largest measured cause of retrieval misses, so a phonetic bridge was
built to close them. At the word level it works well. Devanagari is transliterated to Latin and both sides
reduced to a consonant skeleton under rules that absorb the usual spelling differences (English soft c and g,
c/k, v/w, nasal m/n, aspirates, doubled letters). On 20 word pairs drawn from this corpus, 19 match:

| Devanagari | key | English | key |
|---|---|---|---|
| पोर्ट्ल | prtl | portal | prtl |
| सिस्ट्म | stn | system | stn |
| मैंनेजमैंट | njnt | management | njnt |
| कम्प्यूटर | knptr | computer | knptr |

Unrelated Hindi and English words do not collide. And on the specific failing case, four of six tokens bridge
between "उत्तराखंड गर्वमेंट एसेट मैंनेजमैंट सिस्ट्म पोर्ट्ल" and "Government Asset Management System Portal".

Despite that, **using it for retrieval made results worse**, in both forms tried.

As a fused third channel, swept across key length and weight:

| Minimum key length | Weight | Order first | Order in top five |
|---|---|---|---|
| — | 0 (off) | **42%** | **65%** |
| 2 | 0.6 | 38% | 50% |
| 4 | 0.3 | 31% | 58% |
| 5 | 0.3 | 31% | 65% |
| 6 | 0.6 | 31% | 65% |

As targeted query expansion, adding corpus words that sound like the query's rare words: 27% and 62%.

The reason is that the key discards vowels, so most words in a question match many passages. The expansions
it produces are often genuinely useful, catching OCR misspellings like "सराकर" for "सरकार" and "chaampawat"
for "champawat", but the noise outweighs them and dilutes the keyword scoring.

The capability is kept, indexed and off by default behind `PHONETIC_WEIGHT`, because on a collection with
heavier transliteration it may pay. On this one it does not, and shipping a change that lowers the measured
result would be the wrong call.
