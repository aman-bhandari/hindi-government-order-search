# Demo script (3 minutes)

Setup: `./run.sh serve` and `./run.sh ui`, browser at the UI, Ollama running. No internet needed.

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
Click the accuracy badge: hit rates measured on hand-written questions from these orders.
Say: "Measured, not claimed."

**2:40 — Close on deployability.**
Say: "This ran with no internet. One department is indexed; the same pipeline covers all sixty by changing
one flag. Order numbers and dates come from the portal, never from OCR, so citations cannot drift."
