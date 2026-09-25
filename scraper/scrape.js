// Scrape Uttarakhand GO MIS (go.uk.gov.in) for one department.
// Usage: ./run.sh scrape   (or: node scraper/scrape.js) [--dept 17] [--limit 20] [--out data]
// Chromium is required: the portal only supports legacy TLS renegotiation (curl/Node fetch fail).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const DEPT = opt('--dept', '17');           // 17 = Information Technology Department
const LIMIT = parseInt(opt('--limit', '0'), 10); // 0 = all
const OUT = path.resolve(opt('--out', 'data'));
const BASE = 'https://go.uk.gov.in';
fs.mkdirSync(path.join(OUT, 'pdf'), { recursive: true });
fs.mkdirSync(path.join(OUT, 'meta'), { recursive: true });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// GO MIS stores two shapes of FilePath: an absolute legacy URL (283/308 IT rows, /goentry/go_letters/...)
// and a relative path (/GOFolder/PDF/...). Normalise both, and force https so the in-page fetch stays
// same-origin (the site is https-only and mixed content would be blocked).
function pdfUrl(r) {
  let fp = r.FilePath ? String(r.FilePath).replace(/\\/g, '/').trim() : '';
  if (!fp) return null;
  if (/^https?:\/\//i.test(fp)) return fp.replace(/^http:\/\//i, 'https://');
  if (!fp.startsWith('/')) fp = '/' + fp;
  return BASE + fp;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(90000);
  await page.goto(`${BASE}/en/Search/`, { waitUntil: 'domcontentloaded' });

  // 1) metadata: one POST returns every row for the department
  const rows = await page.evaluate(async (dept) => {
    const payload = { DepartmentID: dept, SectionID: '', CategoryID: '', GONo: '', fromdate: '', todate: '', Subject: '', SearchText: '' };
    const r = await fetch('/en/Search/SearchGO', { method: 'POST', headers: { 'Content-Type': 'application/json; charset=utf-8' }, body: JSON.stringify(payload) });
    if (!r.ok) throw new Error('SearchGO HTTP ' + r.status);
    return await r.json();
  }, DEPT);

  // keep only the fields we need; drop the portal's user/password columns entirely
  const keep = ['GOID', 'GONo', 'GODate1678', 'Subject', 'DepartmentID', 'DepartmentNameE', 'SectionID', 'SectionNameE', 'CategoryID', 'CategoryNameE', 'G0Type', 'OldGORefrence_GOID', 'Amendment', 'AmendmentID', 'FilePath', 'FileName_PDF', 'FileName_DOC', 'File_Path_Word', 'SearchText'];
  const meta = rows.map(r => { const o = {}; for (const k of keep) o[k] = r[k] ?? null; o.pdf_url = pdfUrl(r); return o; });
  const metaFile = path.join(OUT, 'meta', `dept-${DEPT}.json`);
  fs.writeFileSync(metaFile, JSON.stringify({ scraped_at: new Date().toISOString(), department_id: DEPT, count: meta.length, rows: meta }, null, 1));
  console.log(`metadata: ${meta.length} rows -> ${metaFile}`);

  // 2) PDFs: fetch inside the page (same origin) and ship back as base64
  const todo = (LIMIT > 0 ? meta.slice(0, LIMIT) : meta).filter(m => m.pdf_url);
  const manifestFile = path.join(OUT, 'meta', `manifest-${DEPT}.json`);
  const manifest = fs.existsSync(manifestFile) ? JSON.parse(fs.readFileSync(manifestFile, 'utf8')) : {};
  let ok = 0, skipped = 0, failed = 0, missing = 0;
  for (const m of todo) {
    const dest = path.join(OUT, 'pdf', `${m.GOID}.pdf`);
    if (fs.existsSync(dest) && fs.statSync(dest).size > 1000) { skipped++; continue; }
    let done = false;
    for (let attempt = 1; attempt <= 3 && !done; attempt++) {
      try {
        const b64 = await page.evaluate(async (url) => {
          const r = await fetch(url);
          // 404 means the portal's index references a file it does not hold. Around 5% of one department's
          // orders are like this. Marked permanent so we do not retry a file that will never appear.
          if (r.status === 404) throw new Error('PERMANENT 404');
          if (!r.ok) throw new Error('HTTP ' + r.status);
          const blob = await r.blob();
          return await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(',')[1]); fr.onerror = rej; fr.readAsDataURL(blob); });
        }, m.pdf_url);
        const buf = Buffer.from(b64, 'base64');
        if (buf.slice(0, 5).toString() !== '%PDF-') throw new Error('not a PDF (' + buf.slice(0, 20).toString('hex') + ')');
        fs.writeFileSync(dest, buf);
        manifest[m.GOID] = { bytes: buf.length, url: m.pdf_url, fetched_at: new Date().toISOString() };
        ok++; done = true;
        console.log(`ok   ${m.GOID}  ${(buf.length / 1024).toFixed(0)} KB  ${m.GODate1678}  ${String(m.Subject).slice(0, 60)}`);
      } catch (e) {
        if (String(e.message).includes('PERMANENT 404')) {
          missing++;
          manifest[m.GOID] = { error: 'not on the portal (404)', url: m.pdf_url };
          console.log(`gone ${m.GOID}  (portal has no file for this order)`);
          break;
        }
        console.log(`retry ${attempt} ${m.GOID}: ${e.message}`);
        await sleep(1500 * attempt);
      }
    }
    if (!done && !manifest[m.GOID]) { failed++; manifest[m.GOID] = { error: 'failed after 3 attempts', url: m.pdf_url }; }
    await sleep(400); // be polite to a government server
  }
  fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 1));
  console.log(`pdfs: ok=${ok} skipped=${skipped} missing=${missing} failed=${failed} -> ${manifestFile}`);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
