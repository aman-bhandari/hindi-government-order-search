import React, { useState } from 'react'
import { cropUrl, pageUrl } from './api.js'

export function Badge({ children, tone = 'plain' }) {
  const tones = {
    plain: 'bg-paper border-paper-edge text-ink-soft',
    seal: 'bg-seal/8 border-seal/25 text-seal',
    mark: 'bg-mark/20 border-mark/50 text-ink',
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-medium ${tones[tone]}`}>
      {children}
    </span>
  )
}

/** A citation: the quoted words, where they come from, and the scanned proof. */
export function Citation({ quote, onOpenGo }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-lg border border-paper-edge bg-paper-card">
      <blockquote className="border-l-[3px] border-mark px-4 py-3 text-[15px] leading-relaxed">
        &ldquo;{quote.text}&rdquo;
      </blockquote>
      <div className="flex flex-wrap items-center gap-2 border-t border-paper-edge px-4 py-2 text-xs">
        <button onClick={() => onOpenGo(quote.goid)} className="font-medium text-seal hover:underline">
          GO {quote.go_no}
        </button>
        <span className="text-ink-soft">{quote.go_date}</span>
        <Badge>page {quote.page}</Badge>
        <button onClick={() => setOpen(!open)}
          className="ml-auto rounded border border-paper-edge px-2 py-1 font-medium hover:bg-paper">
          {open ? 'Hide the scanned page' : 'Show me on the scanned page'}
        </button>
      </div>
      {open && (
        <figure className="border-t border-paper-edge bg-paper p-3">
          <img src={cropUrl(quote.chunk_id)} alt={`Scanned excerpt from Government Order ${quote.go_no}, page ${quote.page}`}
            className="mx-auto max-h-[420px] w-auto rounded border border-paper-edge bg-white shadow-sm" loading="lazy" />
          <figcaption className="mt-2 text-center text-[11px] text-ink-soft">
            Original scan, highlighted where this quote was read. Text was extracted by OCR, so verify against the image.
          </figcaption>
        </figure>
      )}
    </div>
  )
}

export function ResultRow({ r, onOpenGo }) {
  const [proof, setProof] = useState(false)
  const isSubject = r.kind === 'subject'
  return (
    <li className="rounded-lg border border-paper-edge bg-paper-card p-4">
      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
        <button onClick={() => onOpenGo(r.goid)} className="font-semibold text-seal hover:underline">
          GO {r.go_no}
        </button>
        <span className="text-ink-soft">{r.go_date}</span>
        <Badge>{r.category}</Badge>
        {isSubject ? <Badge tone="seal">subject line</Badge> : <Badge>page {r.page}</Badge>}
        <Badge tone={r.matched_by.includes('vector') ? 'seal' : 'plain'}>{r.matched_by}</Badge>
      </div>
      {!isSubject && r.subject && <p className="mb-2 text-xs text-ink-soft">{r.subject}</p>}
      <p className="text-[15px] leading-relaxed">{r.text}</p>
      {isSubject ? (
        <p className="mt-2 text-[11px] text-ink-soft">
          This is the order&rsquo;s subject as recorded on the portal, not text read from the scan.
          Open the order to read its pages.
        </p>
      ) : (
        <>
          <button onClick={() => setProof(!proof)}
            className="mt-2 text-xs font-medium text-seal hover:underline">
            {proof ? 'Hide scan' : 'View on scanned page'}
          </button>
          {proof && (
            <img src={cropUrl(r.chunk_id)} alt={`Scanned excerpt, Government Order ${r.go_no} page ${r.page}`}
              className="mt-2 max-h-80 rounded border border-paper-edge bg-white" loading="lazy" />
          )}
        </>
      )}
    </li>
  )
}

export function GoPanel({ data, onClose, onOpenGo }) {
  const g = data.go
  return (
    <aside className="fixed inset-y-0 right-0 z-30 w-full max-w-xl overflow-y-auto border-l border-paper-edge bg-paper-card shadow-2xl">
      <header className="sticky top-0 flex items-start gap-3 border-b border-paper-edge bg-paper-card/95 px-5 py-4 backdrop-blur">
        <div className="min-w-0">
          <h2 className="font-serif text-lg leading-tight">GO {g.go_no}</h2>
          <p className="mt-0.5 text-xs text-ink-soft">{g.go_date} · {g.category} · {g.department}</p>
        </div>
        <button onClick={onClose} aria-label="Close"
          className="ml-auto rounded border border-paper-edge px-2 py-1 text-sm hover:bg-paper">✕</button>
      </header>
      <div className="space-y-5 px-5 py-4">
        {g.subject && <p className="text-sm leading-relaxed">{g.subject}</p>}
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge>{data.pages.length} pages indexed</Badge>
          <Badge>{data.chunks.length} passages</Badge>
          {g.pdf_url && <a href={g.pdf_url} target="_blank" rel="noreferrer"
            className="rounded border border-paper-edge px-1.5 py-0.5 font-medium text-seal hover:bg-paper">
            Original PDF on go.uk.gov.in
          </a>}
        </div>

        {data.related?.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">Related orders</h3>
            <ul className="space-y-1.5">
              {data.related.map((r) => (
                <li key={r.goid}>
                  <button onClick={() => onOpenGo(r.goid)}
                    className="w-full rounded border border-paper-edge px-3 py-2 text-left text-xs hover:bg-paper">
                    <span className="font-medium text-seal">GO {r.go_no}</span>
                    <span className="text-ink-soft"> · {r.go_date}</span>
                    <span className="block truncate text-ink-soft">{r.subject}</span>
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-1.5 text-[11px] text-ink-soft">
              Same section or category, nearest in time. Not derived from OCR text.
            </p>
          </section>
        )}

        {data.mentions?.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
              Order numbers mentioned inside
            </h3>
            <ul className="flex flex-wrap gap-1.5">
              {data.mentions.map((m, i) => (
                <li key={i}><Badge>{m.ref_text}</Badge></li>
              ))}
            </ul>
            <p className="mt-1.5 text-[11px] text-ink-soft">
              Read by OCR and shown unverified. Digits in scans are often misread, so check against the page.
            </p>
          </section>
        )}

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">Scanned pages</h3>
          <div className="space-y-3">
            {data.pages.map((p) => (
              <figure key={p.page}>
                <img src={pageUrl(g.goid, p.page)} alt={`Government Order ${g.go_no}, page ${p.page}`}
                  className="w-full rounded border border-paper-edge bg-white" loading="lazy" />
                <figcaption className="mt-1 text-[11px] text-ink-soft">
                  Page {p.page} · {p.words} words read · OCR confidence {p.mean_conf}%
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      </div>
    </aside>
  )
}
