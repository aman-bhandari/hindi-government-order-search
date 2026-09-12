import React, { useEffect, useMemo, useState } from 'react'
import * as api from './api.js'
import { Badge, Citation, ResultRow, GoPanel } from './components.jsx'

const EXAMPLES = [
  'ड्रोन प्रशासन हेतु समिति में कौन कौन हैं?',
  'What is the rule for paying salary arrears through IFMS?',
  'ई-डिस्ट्रिक्ट परियोजना के लिए क्या स्वीकृति दी गई?',
  'Which criteria apply to purchasing ICT and networking equipment?',
]

export default function App() {
  const [q, setQ] = useState('')
  const [mode, setMode] = useState('ask')          // 'ask' = grounded answer, 'search' = passages
  const [provider, setProvider] = useState('ollama')
  const [filters, setFilters] = useState({ category: '', date_from: '', date_to: '', department: '' })
  const [state, setState] = useState({ loading: false, error: null, answer: null, results: null })
  const [meta, setMeta] = useState({ health: null, facets: null })
  const [openGo, setOpenGo] = useState(null)
  const [evalData, setEvalData] = useState(null)
  const [showEval, setShowEval] = useState(false)

  useEffect(() => {
    api.health().then((h) => setMeta((m) => ({ ...m, health: h }))).catch(() => {})
    api.facets().then((f) => setMeta((m) => ({ ...m, facets: f }))).catch(() => {})
    api.evalResults().then(setEvalData).catch(() => {})
  }, [])

  const activeFilters = useMemo(
    () => Object.entries(filters).filter(([, v]) => v).length, [filters])

  async function run(question = q) {
    const text = question.trim()
    if (!text) return
    setState({ loading: true, error: null, answer: null, results: null })
    try {
      if (mode === 'ask') {
        const a = await api.ask({ question: text, provider, limit: 6, ...filters })
        setState({ loading: false, error: null, answer: a, results: a.chunks })
      } else {
        const r = await api.search(text, { limit: 15, ...filters })
        setState({ loading: false, error: null, answer: null, results: r.results })
      }
    } catch (e) {
      setState({ loading: false, error: String(e.message || e), answer: null, results: null })
    }
  }

  async function openGoPanel(goid) {
    try { setOpenGo(await api.go(goid)) } catch (e) { /* ignore */ }
  }

  const h = meta.health
  return (
    <div className="min-h-screen">
      <header className="border-b border-paper-edge bg-paper-card">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <div className="min-w-0">
            <h1 className="font-serif text-xl leading-tight">शासनादेश खोज</h1>
            <p className="text-xs text-ink-soft">
              Government Order search ·{' '}
              {meta.health?.departments?.length
                ? meta.health.departments.map((d) => d.department.replace(/ Department$/, '')).join(' and ')
                : 'Uttarakhand'}
              , Uttarakhand
            </p>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-1.5 text-xs">
            {h && <>
              <Badge>{h.gos_indexed} of {h.gos} orders indexed</Badge>
              <Badge>{h.chunks} passages</Badge>
              <Badge tone={h.embeddings ? 'seal' : 'plain'}>
                {h.embeddings ? 'hybrid search' : 'keyword only'}
              </Badge>
            </>}
            {evalData?.ran && (
              <button onClick={() => setShowEval(!showEval)}
                className="rounded border border-paper-edge px-1.5 py-0.5 font-medium hover:bg-paper">
                accuracy {Math.round(evalData.hit_at_5 * 100)}%
              </button>
            )}
          </div>
        </div>
      </header>

      {showEval && evalData?.ran && (
        <div className="border-b border-paper-edge bg-paper">
          <div className="mx-auto max-w-5xl px-4 py-3 text-xs">
            <p className="mb-2 max-w-3xl text-ink-soft">
              Measured on {evalData.n} questions written by reading real orders in this collection
              ({evalData.n_hindi} Hindi, {evalData.n_english} English), plus {evalData.n_unanswerable} with no
              answer here. Last run {evalData.ran_at}.
              {evalData.declined_correctly === 0 && evalData.answers?.declined_unanswerable === 1 && (
                <> Note the contrast on the unanswerable ones: the retrieval score alone declined none of
                them, while the full pipeline declined all of them. That is why refusal is decided by the
                model with every quote verified, not by a similarity threshold.</>
              )}
            </p>
            <div className="grid gap-6 sm:grid-cols-2">
              <table className="w-full">
                <caption className="pb-1 text-left font-semibold">Finding the right order</caption>
                <tbody>
                  {[['Correct order ranked first', evalData.hit_at_1],
                    ['Correct order in top 5', evalData.hit_at_5],
                    ['Correct page in top 5', evalData.page_hit_at_5],
                    ['Unanswerable refused by score alone', evalData.declined_correctly]].map(([k, v]) => (
                    <tr key={k} className="border-b border-paper-edge last:border-0">
                      <td className="py-1 pr-4">{k}</td>
                      <td className="py-1 font-semibold">{Math.round(v * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {evalData.answers && (
                <table className="w-full">
                  <caption className="pb-1 text-left font-semibold">
                    Answers staying grounded ({evalData.answers.model})
                  </caption>
                  <tbody>
                    {[['Answered rather than declined', evalData.answers.answered],
                      ['Cited the expected order', evalData.answers.cited_expected_order],
                      ['Quotes that passed verification', evalData.answers.quote_verification_rate],
                      [`Declined the ${evalData.answers.n_unanswerable} questions with no answer here`,
                       evalData.answers.declined_unanswerable]].map(([k, v]) => (
                      <tr key={k} className="border-b border-paper-edge last:border-0">
                        <td className="py-1 pr-4">{k}</td>
                        <td className="py-1 font-semibold">{v == null ? '—' : Math.round(v * 100) + '%'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-5xl px-4 py-6">
        <div className="rounded-xl border border-paper-edge bg-paper-card p-4 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="flex rounded-lg border border-paper-edge p-0.5 text-sm">
              {[['ask', 'Answer with citations'], ['search', 'Browse passages']].map(([k, label]) => (
                <button key={k} onClick={() => setMode(k)}
                  className={`rounded-md px-3 py-1.5 font-medium ${mode === k ? 'bg-seal text-white' : 'text-ink-soft hover:bg-paper'}`}>
                  {label}
                </button>
              ))}
            </div>
            {mode === 'ask' && (
              <select value={provider} onChange={(e) => setProvider(e.target.value)}
                className="rounded-lg border border-paper-edge bg-paper-card px-2 py-1.5 text-sm">
                <option value="ollama">Local model (offline)</option>
                <option value="anthropic">Claude API</option>
              </select>
            )}
          </div>

          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
              placeholder="Ask in Hindi or English…  हिंदी या अंग्रेज़ी में पूछें"
              className="min-w-0 flex-1 rounded-lg border border-paper-edge bg-paper px-3 py-2.5 text-[15px] outline-none focus:border-seal/50" />
            <button onClick={() => run()} disabled={state.loading}
              className="rounded-lg bg-seal px-5 py-2.5 font-medium text-white disabled:opacity-50">
              {state.loading ? 'Searching…' : 'Search'}
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            {meta.facets?.departments?.length > 1 && (
              <select value={filters.department}
                onChange={(e) => setFilters({ ...filters, department: e.target.value })}
                className="rounded border border-paper-edge bg-paper-card px-2 py-1">
                <option value="">All departments</option>
                {meta.facets.departments.map((d) => (
                  <option key={d.department} value={d.department}>
                    {d.department.replace(/ Department$/, '')} ({d.n})
                  </option>
                ))}
              </select>
            )}
            <select value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}
              className="rounded border border-paper-edge bg-paper-card px-2 py-1">
              <option value="">All categories</option>
              {meta.facets?.categories?.map((c) => (
                <option key={c.category} value={c.category}>{c.category} ({c.n})</option>
              ))}
            </select>
            <input type="date" value={filters.date_from} aria-label="From date"
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              className="rounded border border-paper-edge bg-paper-card px-2 py-1" />
            <input type="date" value={filters.date_to} aria-label="To date"
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              className="rounded border border-paper-edge bg-paper-card px-2 py-1" />
            {activeFilters > 0 && (
              <button onClick={() => setFilters({ category: '', date_from: '', date_to: '' })}
                className="text-seal hover:underline">clear {activeFilters} filter(s)</button>
            )}
          </div>

          {!state.results && !state.loading && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => { setQ(e); run(e) }}
                  className="rounded-full border border-paper-edge px-3 py-1 text-xs text-ink-soft hover:bg-paper">
                  {e}
                </button>
              ))}
            </div>
          )}
        </div>

        {state.error && (
          <div className="mt-4 rounded-lg border border-seal/30 bg-seal/5 p-4 text-sm">
            <p className="font-medium text-seal">Could not complete that request</p>
            <p className="mt-1 text-ink-soft">{state.error}</p>
            {state.error.includes('provider') && (
              <p className="mt-1 text-xs text-ink-soft">
                The local model may not be running. Start it with <code>ollama serve</code>, or switch to the Claude API.
              </p>
            )}
          </div>
        )}

        {state.answer && (
          <section className="mt-5">
            {state.answer.found ? (
              <>
                <div className="rounded-xl border border-paper-edge bg-paper-card p-5">
                  <p className="text-[17px] leading-relaxed">{state.answer.answer}</p>
                  <p className="mt-3 text-[11px] text-ink-soft">
                    Answered by {state.answer.model} from {state.answer.quotes.length} verified quote(s), out of
                    {' '}{meta.health?.departments?.map((d) => d.department.replace(/ Department$/, '')).join(' and ')
                      || 'the indexed'} orders only. Every quote below was checked word for word against the
                    indexed page before being shown. Check that the orders cited are about the matter you asked about.
                  </p>
                </div>
                <div className="mt-3 space-y-3">
                  {state.answer.quotes.map((qt, i) => (
                    <Citation key={i} quote={qt} onOpenGo={openGoPanel} />
                  ))}
                </div>
              </>
            ) : (
              <div className="rounded-xl border border-paper-edge bg-paper-card p-5">
                <p className="font-medium">Not found in the indexed orders</p>
                <p className="mt-1 text-sm text-ink-soft">{state.answer.answer}</p>
                {state.answer.reason && (
                  <p className="mt-2 text-xs text-ink-soft">Why: {state.answer.reason}.</p>
                )}
                {state.results?.length > 0 && (
                  <p className="mt-1 text-xs text-ink-soft">
                    The closest passages are listed below so you can judge for yourself.
                  </p>
                )}
              </div>
            )}
          </section>
        )}

        {state.results?.length > 0 && (
          <section className="mt-5">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
              {mode === 'ask' ? 'Passages considered' : `${state.results.length} passages`}
            </h2>
            <ul className="space-y-2">
              {state.results.map((r) => (
                <ResultRow key={r.chunk_id} r={r} onOpenGo={openGoPanel} />
              ))}
            </ul>
          </section>
        )}

        {state.results?.length === 0 && !state.loading && (
          <p className="mt-6 text-center text-sm text-ink-soft">
            No passages matched. Try fewer words, or clear the filters.
          </p>
        )}
      </main>

      {openGo && <GoPanel data={openGo} onClose={() => setOpenGo(null)} onOpenGo={openGoPanel} />}

      <footer className="border-t border-paper-edge px-4 py-6 text-center text-xs text-ink-soft">
        Built for UKIS 2026, problem P-001. Orders and metadata come from the official
        GO MIS portal (go.uk.gov.in). Text is extracted by OCR from scanned pages and may contain errors;
        order numbers and dates are taken from the portal, not from OCR.
      </footer>
    </div>
  )
}
