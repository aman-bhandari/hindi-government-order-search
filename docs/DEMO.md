# Demo script (3 minutes)

Setup: `./run.sh ui` once, then `./run.sh serve`; browser at http://127.0.0.1:8000; Ollama running. No internet needed.

**0:00 — The problem, in one screen.**
Open the official portal (go.uk.gov.in), pick Information Technology Department, press search: 308 orders,
searchable only by department, category, date or order number. Open one: a scanned Hindi letter.
Say: "To find what a rule says, you must already know which order says it. The knowledge is in the building,
not in the system."

**0:30 — Ask a question a real officer would ask.**
In the tool, type in Hindi: ड्रोन प्रशासन हेतु समिति में कौन कौन हैं?
Answer appears with quoted lines. Point at the citation: order number, date, page.

**1:00 — The part that matters: prove it.**
Click "Show me on the scanned page". The original scan appears with the quoted lines highlighted.
Say: "The text came from OCR, so the officer does not have to trust it. They see the page."

**1:30 — Ask in English against Hindi documents.**
Type: Which criteria apply to purchasing ICT and networking equipment?
Same evidence, cross-language retrieval. Say: "The question was English, the order is Hindi."

**2:00 — Show it refusing.**
Ask something the corpus cannot answer, for example a question about forest fire compensation.
It says not found instead of inventing an answer. Say: "In government, a confident wrong answer is worse
than no answer."

**2:20 — Show the accuracy page.**
Click the accuracy badge. Two tables: whether the right order is found, and whether the answers built on it
stay grounded. Both measured on questions written by reading these orders, not generated from them.
Say: "Measured, not claimed. And the number that matters is the second one: not whether it found something,
but whether what it told you can be traced to a page."

**2:40 — Close on deployability.**
Say: "This ran with no internet, on a laptop. 308 orders, 892 scanned pages, 4,345 passages. The same
pipeline covers all sixty departments by changing one flag. Order numbers and dates come from the portal,
never from OCR, so a citation cannot drift even when the scan is poor."

**What to say if asked about the numbers.**
Be straight about them. Retrieval finds the right order first 42% of the time and within five results 65%.
The biggest remaining cause of misses is that many subject lines are English spelled phonetically in
Devanagari, which nothing bridges to the same question asked in Hindi. That is a property of the records,
it is documented, and the fix is known rather than hidden.
