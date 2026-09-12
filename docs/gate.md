# OCR gate report — PASS (12 Sep 2026)

Question: can we read real, scanned, Hindi Government Orders well enough to build an evidence-first search on them?

## Method
20 Information Technology Department GOs pulled from the official GO MIS portal (go.uk.gov.in), dates 2023-10 to
2025-05, up to 3 pages each = 52 pages. Rasterised at 300 dpi, OCR'd with Tesseract 5.5 `hin+eng`, word boxes kept.

## Result
| Measure | Value |
|---|---|
| Mean word confidence | 83.1% |
| Range across GOs | 75.8% - 87.1% |
| Pages below 70% confidence | 4 of 52 |
| GOs that failed to OCR | 0 of 20 |
| Predominantly Devanagari | 20 of 20 |
| GOs where an internal GO reference was found | 14 of 20 |
| Speed (Docker) | 7.6 s/page |

Readability check on GO 35580 (state-level drone committee): the Hindi body text is clean and quotable, including
department names, committee composition and policy references. Word boxes carry per-word confidence and pixel
coordinates, so the evidence panel can highlight the exact supporting lines on the scanned page.

## Known weaknesses and how the design handles them
| Weakness | Handling |
|---|---|
| Digits mangled (dates, GO numbers, serial numbers: "24.11.2023" read as "24.42023", "1." as "4.") | GO number, date, department and category always come from the portal API, never from OCR. Citations stay exact. |
| Page furniture (e-office header lines) mixed into text | Strip known header patterns during chunking. |
| Tables in budget GOs interleave columns | Budget-release GOs are low-value for search; flag table pages and keep them out of the answer path. |
| Lowest-confidence GOs are scans of scans (75-79%) | Retrieval is hybrid, so a weak page still matches on the strong words around it. |
| Docker writes files as root | Native install fixes it: `sudo apt install -y tesseract-ocr tesseract-ocr-hin poppler-utils`. |

## Corpus estimate
Average 3.3 pages per GO -> about 1,020 pages for all 308 IT Department GOs.
Roughly 2.2 h unattended in Docker, about 0.7 h with a native install.

## Verdict
Gate passed. P-001 continues. P-003 stays as the documented fallback but is not needed.
