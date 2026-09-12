# What is in this corpus

Every Government Order published by the Information Technology Department of Uttarakhand on the official
GO MIS portal: 308 orders, June 2002 to May 2025.

## Shape of the collection

| Category | Orders |
|---|---|
| Others (sanctions, committees, policy, procedure) | 206 |
| Budget Release Plan | 92 |
| Budget Release Non-Plan | 4 |
| Pay, Pension, DA, LTC | 3 |
| Nodal Officers | 2 |
| Rules | 1 |

Roughly half the orders are in Hindi, half in English, and many mix both. Older orders (2002 to 2008) are
frequently transliterated Hindi written in Latin script, which is why search must tolerate both.

## What the orders are actually about

The department's recurring subjects, useful for knowing what this corpus can and cannot answer:

- Financial sanctions and budget releases to its autonomous bodies: UCOST (Uttarakhand State Council for
  Science and Technology), USERC (Uttarakhand State Council for Science, Education and Research), and USAC
  (Uttarakhand Space Application Centre)
- Buildings and infrastructure: the IT Parks at Dehradun and Bhimtal, the USAC administrative building
- Committees and their composition: the apex committee for the national e-governance plan, departmental
  project selection committees, the state-level empowered committee for drone administration
- Policy and standards: the Uttarakhand Drone Promotion and Usage Policy 2023, criteria for purchasing ICT
  and networking equipment, rate contracts for computers and peripherals
- Projects: e-District, the state asset management portal, lab-on-wheels for schools

## What it cannot answer

Anything owned by another department. A question about forest fire compensation, pension eligibility or road
contracts has no answer here, and the system will say so rather than stretch. Adding those departments is a
configuration change, not new work: the portal exposes 60 of them through the same interface.

## Provenance

Metadata (order number, date, department, section, category, file path) comes from the portal's own search
service. Page text comes from optical character recognition of the scanned PDFs. The two are never mixed:
anything that must be exact is metadata, anything that is read from an image is treated as fallible and shown
alongside the image it came from.

## A property worth knowing about: transliterated subjects

Many subject lines are English written in Devanagari script rather than Hindi. "उत्तराखंड गर्वमेंट एसेट
मैंनेजमैंट सिस्ट्म पोर्ट्ल" is "Uttarakhand Government Asset Management System Portal" spelled phonetically.
Neither keyword search nor a multilingual embedding bridges that reliably to a question asked in real Hindi
("सरकारी परिसंपत्तियों का ब्यौरा रखने वाला पोर्टल"), and it is the largest single cause of retrieval misses
measured on this corpus. Asking in English, or using the transliterated words, finds those orders.
