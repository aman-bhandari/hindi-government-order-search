const J = async (r) => {
  if (!r.ok) throw new Error((await r.text().catch(() => '')) || `HTTP ${r.status}`)
  return r.json()
}
const qs = (o) => Object.entries(o).filter(([, v]) => v !== '' && v != null)
  .map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')

export const health = () => fetch('/api/health').then(J)
export const facets = () => fetch('/api/facets').then(J)
export const search = (q, f = {}) => fetch(`/api/search?${qs({ q, ...f })}`).then(J)
export const ask = (body) => fetch('/api/ask', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then(J)
export const go = (id) => fetch(`/api/go/${id}`).then(J)
export const evalResults = () => fetch('/api/eval').then(J)
export const cropUrl = (chunkId) => `/api/crop/${chunkId}.png`
export const pageUrl = (goid, page) => `/api/page/${goid}/${page}.png`
