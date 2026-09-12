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


## Following subject hits into the order body: two attempts

The diagnosis was solid. The right order reached the answerer 69% of the time but was cited only 31%, and
the largest single cause was that a subject line matched while the order's body never arrived. "Regarding
setting criteria for purchasing ICT equipment" identifies the right order for "who approves computer
purchases?" while answering nothing.

**First attempt: append the body to the subject hit.** This raised the passages sent to the model from 6 to
10, and measurably hurt:

| | Baseline | Append body |
|---|---|---|
| Answered rather than declined | 65% | 58% |
| Cited the expected order | 31% | 31% |
| Quotes passing verification | 72% | 57% |
| Declined the unanswerable | 100% | **75%** |

The last row is the one that mattered. More context gave the model more garbled OCR to misquote, and more
plausible-looking administrative prose to latch onto when it should have refused. A change that trades a
perfect refusal record for nothing is not a trade worth making.

**Second attempt: swap the body in for the subject, keeping the budget at six passages.** Worse again, and
worse than the first attempt:

| | Baseline | Append body | Swap body in |
|---|---|---|---|
| Answered rather than declined | **65%** | 58% | 46% |
| Cited the expected order | **31%** | 31% | 23% |
| Quotes passing verification | **72%** | 57% | 47% |
| Declined the unanswerable | **100%** | 75% | 75% |

The second result explains the first, and the explanation is worth keeping. Subject lines are typed metadata,
not OCR. In a collection where page text averages 81% word confidence, they are the only passages a model can
quote and have the quote survive verification reliably. Removing them to make room for body text removed the
most quotable evidence in the corpus, and quote verification fell furthest of all.

So the diagnosis was right and the remedy was wrong. The subject line is doing more work than identifying an
order: it is carrying the grounding. Both variants are kept behind `EXPAND_SUBJECTS`, default off.

A better attack on the same problem, untried: keep the subject passage and also send the body, but shrink
what each passage contributes so the budget does not grow. That was not attempted because the budget is
already tight at a 4,096-token context on a 6 GB card.


## How much to trust these numbers

Running the identical baseline configuration twice gave noticeably different answer-side results:

| | Run 1 | Run 2 |
|---|---|---|
| Answered rather than declined | 65% | 65% |
| Cited the expected order | 31% | 35% |
| Quotes passing verification | 72% | 61% |
| Declined the unanswerable | 100% | 75% |

The refusal column moved 25 points because there were only four unanswerable questions, so each one was
worth 25 points. The quote column moved because there are around 30 quotes in total, so a few either way
swings it several points. A local model at temperature zero is also not perfectly reproducible in practice.

Two things follow. The unanswerable set was tripled to twelve, making each question worth 8 points instead
of 25. And the comparison between variants should be read with that spread in mind: the swap-body result
(46% answered, 47% of quotes verified) sits clearly below the baseline range, while the append-body result
is closer to the edge of it. Neither showed a benefit, which is why both are off by default, but only the
first is comfortably outside the noise.

Retrieval numbers do not have this problem. They involve no model and are identical across runs.
