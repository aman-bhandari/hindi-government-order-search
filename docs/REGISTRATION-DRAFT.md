# UKIS 2026 registration text — DRAFT, not submitted

Nothing is submitted yet; the team decides. Form: https://www.axocom.in/UKISHackathon/register/solution?problem=P-001
Fields: problem (P-001), solution title, description, prototype URL (optional, must start https://),
name, email, phone/WhatsApp, consent checkbox.

## Solution title
शासनादेश खोज — evidence-first search for Uttarakhand Government Orders

## Description (draft)

Uttarakhand's Government Orders are scanned Hindi letters going back to 2002. The official portal can filter
them by department, category, date and order number, which means an officer must already know which order
they need. The knowledge stays with people rather than in the system.

This makes the contents searchable in Hindi and English, and answers questions using only quoted text from
the orders themselves. What separates it from a general chatbot over PDFs is that every claim is provable:
each quote is shown highlighted on the original scanned page, so the officer verifies with their eyes rather
than trusting the machine.

Three design decisions follow from one measured fact. OCR of these scans reads words well (83% mean word
confidence across 52 sampled pages) but misreads digits constantly. So: order numbers, dates, departments and
categories are taken from the portal's own metadata and never from OCR, which keeps citations exact. Related
orders are found through section, category and date rather than through cited order numbers, because those
numbers cannot be read reliably. And every quote a model produces is checked word for word against the
indexed passage before it is displayed; quotes that fail are dropped, and if none survive the system says it
did not find an answer instead of guessing.

It runs entirely on one machine with no internet, using a local model, which matters for records that
government may not wish to send to an external service. An API model can be switched on where quality
matters more than isolation.

Built and indexed: all Information Technology Department orders from the official GO MIS portal.
Extending to the portal's other 59 departments is a matter of running time, not new work.
Retrieval quality is measured against hand-written questions from these orders and shown inside the tool.

## Notes for filling the form
- Prototype URL: leave blank unless a hosted demo exists. A GitHub repository link may be used instead if the
  form accepts it, since the rules allow source code or a video in place of a hosted link (T&C 6.3).
- Third-party components are disclosed in the README, as required by T&C 6.2.
- Consent checkbox confirms solo participation and one entry per person (T&C 5.3).
