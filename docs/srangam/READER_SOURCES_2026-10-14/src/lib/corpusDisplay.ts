/**
 * Corpus display helpers - TEXTS_READER_2026_09_27.
 *
 * Pure functions, so the reader's presentation rules are testable without a
 * browser or a database. Nothing here changes stored text: the Sanskrit and the
 * translation are shown exactly as published, apart from the verse-end mark.
 */

/**
 * The automaton's English prompt ends every verse with "//" (the house stand-in
 * for the danda). In a reader that mark is noise at the end of a passage and a
 * line break inside one. Nothing else in the translation is touched.
 */
export function displayTranslation(t: string | null | undefined): string {
  if (!t) return '';
  return t
    .replace(/\s*\/\/\s*$/, '')
    .replace(/\s+\/\/(?:\s+|$)/g, '\n')   // only a spaced mark; 'http://' is not one
    .trim();
}

/**
 * READER_MARKS_2026_10_07: the OCR writes an ornamental rule of the printed page as a line reading
 * "<decorative line>". It is not text: the reader draws a short rule instead. Only lines that are
 * exactly that marker are removed; everything else is returned as published.
 */
const DECORATIVE_LINE = /^\s*<decorative line>\s*$/i;

export function splitDecoration(s: string | null | undefined): { text: string; rule: boolean } {
  const lines = (s ?? '').split('\n');
  const kept = lines.filter((l) => !DECORATIVE_LINE.test(l));
  return { text: kept.join('\n').trim(), rule: kept.length !== lines.length };
}

/** "p12.3", with the edition's own verse reference when the source has one. */
export function passageLabel(p: { page_no: number; idx: number; verse_ref?: string | null }): string {
  const base = `p${p.page_no}.${p.idx}`;
  return p.verse_ref ? `${base} · ${p.verse_ref}` : base;
}

/**
 * OCR confidence below this is shown to the reader. The automaton refuses to
 * translate below 0.35, so anything published sits at or above that; 0.5 marks
 * the band where a reader should know the scan was hard to read.
 */
export const LOW_OCR_QUALITY = 0.5;

export function isLowQuality(q: number | null | undefined): boolean {
  return typeof q === 'number' && q > 0 && q < LOW_OCR_QUALITY;
}

export const PASSAGES_PER_PAGE = 50;

/** 1-based page from a query-string value; anything invalid is page 1. */
export function pageFromQuery(v: string | null, totalPassages: number): number {
  const n = Number.parseInt(v ?? '', 10);
  const last = Math.max(1, Math.ceil(totalPassages / PASSAGES_PER_PAGE));
  if (!Number.isFinite(n) || n < 1) return 1;
  return Math.min(n, last);
}

// ---- READER_NAV_2026_10_08: navigation and layout of the two readers -------------------------
// Pure, like everything above: they decide how stored text is shown, and never change it.

// Devanagari letters and signs; the danda, the double danda and the digits are not letters.
const DEVANAGARI = /[\u0900-\u0963\u0971-\u097F]/;
const LATIN_LETTER = /[A-Za-z]/g;

/** A line with no Devanagari letter and at least three Latin letters ("ay Trae: ।"). */
export function isMisreadLine(line: string | null | undefined): boolean {
  const s = line ?? '';
  if (!s.trim() || DEVANAGARI.test(s)) return false;
  return (s.match(LATIN_LETTER) ?? []).length >= 3;
}

export interface SourceLine {
  text: string;
  /** The scanner misread this line: it is shown as read, muted, with a note. */
  misread: boolean;
}

/**
 * The Sanskrit and its IAST, line by line. A Sanskrit line is marked misread only when the same
 * passage has Devanagari elsewhere (a passage with none may be the book's own English, such as a
 * preface). An IAST line is marked when the two have the same number of lines and the Sanskrit
 * line beside it is misread: it transliterates the same misreading.
 */
export function sourceLines(
  sanskrit: string | null | undefined,
  iast: string | null | undefined,
): { sa: SourceLine[]; ia: SourceLine[] } {
  const sa = sanskrit ? sanskrit.split('\n') : [];
  const ia = iast ? iast.split('\n') : [];
  const anyDevanagari = sa.some((l) => DEVANAGARI.test(l));
  const marks = sa.map((l) => anyDevanagari && isMisreadLine(l));
  const paired = sa.length === ia.length;
  return {
    sa: sa.map((text, i) => ({ text, misread: marks[i] })),
    ia: ia.map((text, i) => ({ text, misread: paired && marks[i] })),
  };
}

// ---- PROVISIONAL_EN_2026_10_14: English made from a misread reading --------------------------
// The automaton's own test (scripts/redeem.py, repair_text.JUNK): a verse with eight or more
// Devanagari signs that also carries a Latin word (a letter, then a letter or a stray ' ! ") was
// read by the scanner with debris, and its English was made from that reading. It is provisional:
// it is translated again once the scan is repaired. Nothing stored is changed.
const DEVANAGARI_SIGN = /[\u0900-\u097F]/g;
const LATIN_WORD = /(^|[^A-Za-z])[A-Za-z][A-Za-z'!"]+/;

/** True when the verse's Sanskrit carries the scanner's Latin-letter debris. */
export function madeFromMisread(sanskrit: string | null | undefined): boolean {
  const s = sanskrit ?? '';
  return (s.match(DEVANAGARI_SIGN) ?? []).length >= 8 && LATIN_WORD.test(s);
}

/** The reader's note on such an English, for its chip and its "About" line. */
export const PROVISIONAL_NOTE =
  'The scanner misread letters of this verse (Latin letters among the Devanagari), and the English ' +
  'was made from that reading. It is provisional: it will be translated again once the scan is repaired.';

// ---- READER_SOURCES_2026_10_14 (S2): where a passage's Sanskrit comes from --------------------
// The mirror keeps the automaton's passages.ocr_engine. An e-text (the BORI Critical Edition's own
// text of the Mahabharata, from GRETIL) was typed from the edition, not read from a scan: the OCR
// formula's quality score means nothing for it. So an e-text is not called "OCR", and is never marked
// a hard-to-read scan. A passage whose engine is not recorded is shown as before.

export interface Reading {
  kind: 'etext' | 'vision' | 'tesseract' | 'resegment' | 'other';
  /** How the reader names it: "the BORI Critical Edition e-text (from GRETIL)". */
  label: string;
  /** True when the Sanskrit was read from a scan (its OCR confidence then means something). */
  scan: boolean;
}

/** The reading behind a passage's Sanskrit, from its ocr_engine; null when none is recorded. */
export function readingOf(engine: string | null | undefined): Reading | null {
  const e = (engine ?? '').trim().toLowerCase();
  if (!e) return null;
  if (e === 'gretil-bori-etext') return { kind: 'etext', label: 'the BORI Critical Edition e-text (from GRETIL)', scan: false };
  if (e.startsWith('gretil') || e.includes('etext')) return { kind: 'etext', label: 'an e-text, typed from the edition', scan: false };
  if (e.includes('vision')) return { kind: 'vision', label: 'read from the scan by a vision model', scan: true };
  if (e.startsWith('tesseract')) return { kind: 'tesseract', label: 'read from the scan by Tesseract OCR', scan: true };
  if (e.startsWith('resegment')) return { kind: 'resegment', label: 'read from the scan, then cut into verses again', scan: true };
  return { kind: 'other', label: `read by ${(engine ?? '').trim()}`, scan: true };
}

/** One page's engines, as public.corpus_reader_sources returns them (C17). */
export interface SourceRow {
  page_no: number;
  ocr_engine: string | null;
  passages: number;
}

/** page -> the engine of most of its passages (a page whose engine is not recorded is left out). */
export function readingsByPage(rows: SourceRow[] | null | undefined): Map<number, string> {
  const best = new Map<number, { engine: string | null; n: number }>();
  for (const r of rows ?? []) {
    if (!r || typeof r.page_no !== 'number') continue;
    const n = Number(r.passages) || 0;
    const cur = best.get(r.page_no);
    if (!cur || n > cur.n) best.set(r.page_no, { engine: r.ocr_engine ?? null, n });
  }
  const out = new Map<number, string>();
  best.forEach((v, page) => { if (v.engine) out.set(page, v.engine); });
  return out;
}

/** The stored title, or the document code made readable when no title was recorded. */
export function displayTitle(title: string | null | undefined, docCode: string): string {
  const t = (title ?? '').trim();
  if (t && t !== docCode) return t;
  return docCode
    .replace(/_+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/(^|\s)([a-z])/g, (_m, sp: string, c: string) => sp + c.toUpperCase());
}

/** The margin reference: scan page and passage, "18.3". */
export function gutterRef(p: { page_no: number; idx: number }): string {
  return `${p.page_no}.${p.idx}`;
}

/** Where a passage sits, in words, for its tooltip. */
export function passageWhere(p: { page_no: number; idx: number; verse_ref?: string | null }): string {
  const base = `Scan page ${p.page_no}, passage ${p.idx}`;
  return p.verse_ref ? `${base}; the edition numbers it ${p.verse_ref}` : base;
}

/** The reader page (1-based) that holds the passage at reading position `ord`. */
export function readerPageOf(ord: number): number {
  return Math.max(1, Math.ceil((Number(ord) || 1) / PASSAGES_PER_PAGE));
}

export interface PageStart {
  reader_page: number;
  /** Scan page of the reader page's first passage. */
  page_no: number;
  idx: number;
  /** Last scan page the reader page reaches. */
  last_page_no: number | null;
}

/** Reader pages from the keys of a whole text in reading order (the public reader's contents). */
export function outlineFromKeys(keys: { page_no: number; idx: number }[]): PageStart[] {
  const out: PageStart[] = [];
  for (let i = 0; i < keys.length; i += PASSAGES_PER_PAGE) {
    const chunk = keys.slice(i, i + PASSAGES_PER_PAGE);
    out.push({
      reader_page: i / PASSAGES_PER_PAGE + 1,
      page_no: chunk[0].page_no,
      idx: chunk[0].idx,
      last_page_no: chunk[chunk.length - 1].page_no,
    });
  }
  return out;
}

/**
 * The first reader page that holds a scan page. A scan page with no passages (a blank or a plate)
 * goes to the next reader page that has a later one; past the end, to the last; before the first
 * passage, to page 1. null when there is nothing to go to.
 */
export function readerPageForScan(pages: PageStart[], scan: number): number | null {
  if (!pages.length || !Number.isFinite(scan)) return null;
  for (const p of pages) {
    if (scan >= p.page_no && scan <= (p.last_page_no ?? p.page_no)) return p.reader_page;
  }
  const after = pages.find((p) => p.page_no > scan);
  return after ? after.reader_page : pages[pages.length - 1].reader_page;
}

/** "scan page 4" or "scan pages 4-9", for the contents list. */
export function scanRange(p: { page_no: number; last_page_no: number | null }): string {
  const last = p.last_page_no ?? p.page_no;
  return last === p.page_no ? `scan page ${p.page_no}` : `scan pages ${p.page_no}–${last}`;
}
