import React, { useMemo, useState } from "react";

/**
 * Panchatantra Exporter – Debroy‑style HTML/PDF
 * -------------------------------------------------
 * A single‑file React frontend that:
 * 1) Fetches Sanskrit + English passages from your API (FastAPI example below)
 * 2) Previews a clean, print‑ready HTML (side‑by‑side or stacked)
 * 3) Lets the user download the HTML or print to PDF (browser’s Save as PDF)
 *
 * Expected API:
 *   GET  {baseUrl}/api/passages?doc=panchatantra&page_from=1&page_to=10
 *        -> [{ page_no, idx, san, en } ...]
 *   POST {baseUrl}/api/export/html  (optional server export)
 *   POST {baseUrl}/api/export/pdf   (optional server PDF)
 */

const DEFAULT_BASE = "http://localhost:8000"; // your FastAPI base URL

export default function PanchatantraExporterApp() {
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE);
  const [doc, setDoc] = useState("panchatantra");
  const [pageFrom, setPageFrom] = useState(1);
  const [pageTo, setPageTo] = useState(10);
  const [includeSan, setIncludeSan] = useState(true);
  const [includeEn, setIncludeEn] = useState(true);
  const [sideBySide, setSideBySide] = useState(true);
  const [numberPages, setNumberPages] = useState(true);
  const [title, setTitle] = useState("Stories from Panchatantra – Export");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [passages, setPassages] = useState([]); // [{page_no, idx, san, en}]
  const [previewHTML, setPreviewHTML] = useState("");

  const pageRangeOK = pageFrom >= 1 && pageTo >= pageFrom;

  function groupByPage(items) {
    const map = new Map();
    for (const it of items) {
      const k = it.page_no;
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(it);
    }
    // sort inner by idx (if present)
    for (const [k, arr] of map) arr.sort((a, b) => (a.idx ?? 0) - (b.idx ?? 0));
    // return sorted by page_no
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }

  const cssBlock = useMemo(() => `
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif&family=Noto+Serif+Devanagari:wght@400;600&display=swap" rel="stylesheet">
    <style>
      :root { --fg:#0f172a; --muted:#475569; --rule:#e2e8f0; }
      html, body { margin:0; padding:0; }
      body { font-family: 'Noto Serif', serif; color:var(--fg); }
      .wrap { max-width: 960px; margin: 24px auto; padding: 0 16px; }
      h1.title { font-size: 22px; margin: 8px 0 16px; font-weight: 600; }
      .meta { color: var(--muted); font-size: 12px; margin-bottom: 16px; }
      .page { page-break-inside: avoid; margin: 16px 0 24px; }
      .page + .page { border-top: 1px solid var(--rule); padding-top: 16px; }

      .grid { display: grid; gap: 16px; }
      .grid.sb { grid-template-columns: 1fr 1fr; }
      .grid.stacked { grid-template-columns: 1fr; }

      .san { font-family: 'Noto Serif Devanagari', serif; font-size: 18px; line-height: 1.6; }
      .en  { font-size: 16px; line-height: 1.6; }
      .sec-title { font-size: 12px; color: var(--muted); letter-spacing: .04em; text-transform: uppercase; }

      .page-num { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
      .item { margin: 6px 0; }

      /* print CSS */
      @page { size: A4; margin: 18mm 14mm; }
      @media print {
        .page { page-break-inside: avoid; }
        .wrap { max-width: unset; margin: 0; padding: 0; }
      }
    </style>
  `, []);

  function buildHTML(items) {
    const pages = groupByPage(items);
    const gridClass = sideBySide ? "grid sb" : "grid stacked";
    const now = new Date().toLocaleString();

    const pageBlocks = pages.map(([pg, arr]) => {
      let left = ""; let right = ""; let stacked = "";
      const sanBlock = includeSan ? `
        <div>
          <div class="sec-title">SANSKRIT</div>
          ${arr.map(x => x.san ? `<div class="item san">${escapeHTML(x.san)}</div>`: "").join("")}
        </div>` : "";
      const enBlock = includeEn ? `
        <div>
          <div class="sec-title">ENGLISH</div>
          ${arr.map(x => x.en ? `<div class="item en">${escapeHTML(x.en)}</div>`: "").join("")}
        </div>` : "";

      if (sideBySide) {
        left = sanBlock; right = enBlock;
      } else {
        stacked = `${sanBlock}${enBlock}`;
      }

      return `
        <section class="page">
          ${numberPages ? `<div class="page-num">Page ${pg}</div>` : ""}
          <div class="${gridClass}">
            ${sideBySide ? `${left}${right}` : stacked}
          </div>
        </section>`;
    }).join("\n");

    return `<!doctype html>
      <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        ${cssBlock}
        <title>${escapeHTML(title)}</title>
      </head>
      <body>
        <main class="wrap">
          <h1 class="title">${escapeHTML(title)}</h1>
          <div class="meta">Doc: ${escapeHTML(doc)} · Pages ${pageFrom}–${pageTo} · Generated ${escapeHTML(now)}</div>
          ${pageBlocks}
        </main>
      </body>
      </html>`;
  }

  async function loadPassages() {
    setError("");
    if (!pageRangeOK) { setError("Invalid page range"); return; }
    setLoading(true);
    try {
      const url = `${baseUrl.replace(/\/$/, "")}/api/passages?doc=${encodeURIComponent(doc)}&page_from=${pageFrom}&page_to=${pageTo}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
      const data = await res.json();
      setPassages(data || []);
      const html = buildHTML(data || []);
      setPreviewHTML(html);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function openPreviewWindow() {
    if (!previewHTML) return;
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.open();
    w.document.write(previewHTML);
    w.document.close();
  }

  function downloadHTML() {
    if (!previewHTML) return;
    const blob = new Blob([previewHTML], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = sanitizeFilename(`${doc}_${pageFrom}-${pageTo}.html`);
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function printPDF() {
    if (!previewHTML) return;
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.open();
    // ensure print after fonts load
    const injected = previewHTML.replace(
      "</body>",
      `<script>window.addEventListener('load',()=>{setTimeout(()=>window.print(), 300);});<\/script></body>`
    );
    w.document.write(injected);
    w.document.close();
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto p-4 md:p-6">
        <h1 className="text-2xl font-semibold text-slate-900">Panchatantra Exporter</h1>
        <p className="text-slate-600 mb-4">Preview & export Sanskrit + English as clean HTML or print to PDF. (Server API optional.)</p>

        <div className="grid md:grid-cols-3 gap-4 mb-4">
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <label className="block text-sm text-slate-600 mb-1">API Base URL</label>
            <input className="w-full border rounded-xl px-3 py-2" value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} />

            <label className="block text-sm text-slate-600 mt-3 mb-1">Doc Code</label>
            <input className="w-full border rounded-xl px-3 py-2" value={doc} onChange={e=>setDoc(e.target.value)} />

            <label className="block text-sm text-slate-600 mt-3 mb-1">Title</label>
            <input className="w-full border rounded-xl px-3 py-2" value={title} onChange={e=>setTitle(e.target.value)} />

            <div className="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label className="block text-sm text-slate-600 mb-1">Page from</label>
                <input type="number" className="w-full border rounded-xl px-3 py-2" value={pageFrom} onChange={e=>setPageFrom(Number(e.target.value))} />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Page to</label>
                <input type="number" className="w-full border rounded-xl px-3 py-2" value={pageTo} onChange={e=>setPageTo(Number(e.target.value))} />
              </div>
            </div>

            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={includeSan} onChange={e=>setIncludeSan(e.target.checked)} /> Include Sanskrit
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={includeEn} onChange={e=>setIncludeEn(e.target.checked)} /> Include English
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={sideBySide} onChange={e=>setSideBySide(e.target.checked)} /> Side by side (else stacked)
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={numberPages} onChange={e=>setNumberPages(e.target.checked)} /> Show page numbers
              </label>
            </div>

            <div className="mt-4 flex gap-2">
              <button onClick={loadPassages} disabled={loading || !pageRangeOK} className="px-3 py-2 rounded-xl bg-slate-900 text-white">{loading ? "Loading…" : "Load & Preview"}</button>
              <button onClick={downloadHTML} disabled={!previewHTML} className="px-3 py-2 rounded-xl bg-white border">Download HTML</button>
              <button onClick={printPDF} disabled={!previewHTML} className="px-3 py-2 rounded-xl bg-white border">Print / Save PDF</button>
            </div>

            {!pageRangeOK && <div className="text-sm text-red-600 mt-2">Fix page range.</div>}
            {error && <div className="text-sm text-red-600 mt-2">{error}</div>}
          </div>

          <div className="md:col-span-2 bg-white rounded-2xl shadow-sm p-4 overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm text-slate-600">Preview</div>
              <button onClick={openPreviewWindow} disabled={!previewHTML} className="text-sm underline">Open in new tab</button>
            </div>
            <div className="border rounded-xl p-3 h-[70vh] overflow-auto bg-white">
              {/* sandboxed preview */}
              <iframe
                title="preview"
                className="w-full h-full border-0"
                srcDoc={previewHTML || emptyDoc(cssBlock)}
              />
            </div>
          </div>
        </div>

        <div className="text-xs text-slate-500">Tip: If server PDF isn’t configured, use the browser’s Print → Save as PDF. Fonts are embedded via Google Fonts for Devanagari clarity.</div>
      </div>
    </div>
  );
}

function sanitizeFilename(name) {
  return name.replace(/[^a-z0-9_\-\.]+/gi, "_");
}

function emptyDoc(css) {
  return `<!doctype html><html><head>${css}</head><body><main class="wrap"><div class="meta">No preview yet.</div></main></body></html>`;
}

function escapeHTML(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
