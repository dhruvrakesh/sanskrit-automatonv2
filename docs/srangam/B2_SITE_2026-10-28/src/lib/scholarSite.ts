/**
 * The scholarly English as the desk has it - SCHOLAR_SITE_2026_10_25.
 *
 * The desk (127.0.0.1:5057) has /scholar, every text with a scholarly English and its counts, and
 * /scholar/<doc>/prose, the text read as a book. The site now has both, for signed-in readers, from the mirror's own
 * rows (corpus_sync.py SCHOLAR_MIRROR_2026_10_18) through two reader functions (docs/cloud/C22 in the automaton repo):
 *   corpus_reader_scholar_docs()                      every live text with a scholarly English, with its counts;
 *   corpus_reader_scholar_prose(doc, page, idx, n)    one text's scholarly rows in reading order, n at a time.
 * The chapters are made as the edition makes them (export_html.py _ref_chapters, _section_key): by the verses' own
 * two-part references (81.18) when half or more of the verses that show Sanskrit carry one, a line without one going
 * with the next verse and a colophon (iti ...) with the one before; else by a numeric chapter; else by the scan page.
 * A sentence over verses stands whole after its range; a paragraph begins where a speaker does, or after eight; each
 * note is numbered after its anchor's first appearance, the translator's doubt about the reading last; a verse flagged
 * by the judge and not yet read by a person is marked. Nothing from the database is rendered as HTML.
 *
 * X1C_SITE_2026_10_28: and a search over it (docs/cloud/C24):
 *   corpus_reader_scholar_search(q, k, p_doc)        the words in the scholarly English (stemmed, and as written),
 *                                                    live verses of live texts, with corpus_reader_search's rows.
 */
import {
  callMirror, functionMissing, MAX_QUERY, MIN_WORDS, type MirrorHit, type MirrorResult,
} from '@/lib/corpusMirror';
import { emphasisParts, parseScholar, scholarStatus } from '@/lib/scholarReading';

export interface ScholarDoc {
  doc_code: string;
  title: string;
  category: string | null;
  passages: number;
  verses: number;
  flagged: number;
  accepted: number;
  fidelity: number | null;
  first_page: number;
  first_idx: number;
  first_ord: number | null;
  last_made: string | null;
}

export interface ProseRow {
  page_no: number;
  idx: number;
  verse_ref: string | null;
  chapter: string | null;
  has_sanskrit: boolean | null;
  colophon: boolean | null;
  scholar: string | null;
  meta: string | null;
  made_at: string | null;
}

/** Rows a call: about 100 KB of text. */
export const PROSE_BATCH = 300;

export function loadScholarDocs(): Promise<MirrorResult<ScholarDoc>> {
  return callMirror<ScholarDoc>('corpus_reader_scholar_docs', {});
}

export function loadScholarProse(
  docCode: string, after: { page: number; idx: number } | null, limit: number = PROSE_BATCH,
): Promise<MirrorResult<ProseRow>> {
  return callMirror<ProseRow>('corpus_reader_scholar_prose', {
    p_doc: docCode, p_after_page: after ? after.page : null, p_after_idx: after ? after.idx : null, p_limit: limit,
  });
}

/** X1C_SITE_2026_10_28: a search in the scholarly English, and whether the database has it (C24 not applied). */
export interface ScholarSearchResult extends MirrorResult<MirrorHit> { missing: boolean }

export const SCHOLAR_SEARCH = 'corpus_reader_scholar_search';
export const SCHOLAR_SEARCH_OFF = 'The search in the scholarly English is not switched on yet. The search by words works now.';

/** The words in the scholarly English of every text (or one): at most 50 verses, the best first. The English's own
 *  marks (*Manu*, the verse's end //) are taken out of the snippet; its [[ ]] marks are the words found. */
export async function searchScholar(q: string, docCode: string | null = null, k = 30): Promise<ScholarSearchResult> {
  const query = (q ?? '').replace(/\s+/g, ' ').trim();
  if (query.length < MIN_WORDS) {
    return { ok: false, rows: [], error: `Type at least ${MIN_WORDS} characters.`, refused: false, missing: false };
  }
  const r = await callMirror<MirrorHit>(SCHOLAR_SEARCH, {
    q: query.slice(0, MAX_QUERY), k: Math.max(1, Math.min(50, k)), p_doc: docCode || null,
  });
  if (functionMissing(r, SCHOLAR_SEARCH)) return { ...r, error: SCHOLAR_SEARCH_OFF, missing: true };
  if (!r.ok) return { ...r, missing: false };
  return { ...r, rows: r.rows.map((h) => ({ ...h, snippet: h.snippet == null ? h.snippet : h.snippet.replace(/\*/g, '').replace(/\s*\/\/\s*/g, ' ').trim() })), missing: false };
}

/** The prose page of a text. */
export function proseHref(docCode: string): string {
  return `/corpus/${encodeURIComponent(docCode)}/prose`;
}

/** A verse in the reader, beside its Sanskrit (the reader finds its page from ?at=). */
export function verseHref(docCode: string, page: number, idx: number): string {
  return `/corpus/${encodeURIComponent(docCode)}?at=${page}.${idx}`;
}

// ---- the chapters ----------------------------------------------------------------------------------

const REF2 = /^\D*?(\d+)\.(\d+)$/;               // export_html.py _REF2_RE
const NUMERIC_CH = /^[0-9]+([.\-–][0-9]+)*$/;   // export_html.py _NUMERIC_CH_RE

export interface ChapterKey {
  kind: 'chapter' | 'page';
  value: string;
}

/** Each row's chapter, as the edition gives it. */
export function chapterKeys(rows: ProseRow[]): ChapterKey[] {
  const chs = rows.map((r) => {
    const m = REF2.exec((r.verse_ref ?? '').trim());
    return m ? m[1] : null;
  });
  const chap: (string | null)[] = rows.map((r) => (r.chapter ?? '').trim() || null);
  const shown = rows.map((r, i) => ({ r, c: chs[i] })).filter((x) => x.r.has_sanskrit !== false);
  if (shown.length > 0 && shown.filter((x) => x.c).length >= 0.5 * shown.length) {
    const after: (string | null)[] = new Array(rows.length).fill(null);
    let nxt: string | null = null;
    for (let i = rows.length - 1; i >= 0; i -= 1) {
      if (chs[i]) nxt = chs[i];
      after[i] = nxt;
    }
    let prev: string | null = null;
    rows.forEach((r, i) => {
      if (chs[i]) {
        prev = chs[i];
        chap[i] = chs[i];
        return;
      }
      if (prev && (r.colophon === true || after[i] === null)) chap[i] = prev;
      else if (after[i]) chap[i] = after[i];
    });
  }
  return rows.map((r, i) => {
    const c = chap[i];
    return c && NUMERIC_CH.test(c) ? { kind: 'chapter', value: c } : { kind: 'page', value: String(r.page_no) };
  });
}

export function chapterLabel(k: ChapterKey): string {
  return k.kind === 'chapter' ? `Adhyāya ${k.value}` : `Page ${k.value}`;
}

// ---- the prose ---------------------------------------------------------------------------------------

export type ProseToken = { text: string; em: boolean } | { note: number };

export interface ProseSegment {
  /** The anchor of its first verse, p<page>-<idx>. */
  id: string;
  page: number;
  idx: number;
  /** The verse number(s) shown small before it: "18", or "18–19" for a sentence over verses; '' for none. */
  label: string;
  tokens: ProseToken[];
  flag: boolean;
  title: string;
}

export interface ProseNote {
  n: number;
  ref: string;
  anchor: string;
  note: string;
}

export interface ProseChapter {
  id: string;
  key: ChapterKey;
  label: string;
  paragraphs: ProseSegment[][];
  notes: ProseNote[];
}

const SPEECH = /^[A-Z][^.:;]{0,60} said:/;       // scholar_translate.py _SPEECH
const PARA_MAX = 8;

const plain = (s: string) => s.replace(/\*/g, '').trim();

/** "81.18" -> "18"; "81.18–19" -> "18–19"; a line without a reference (a speaker's, a heading) has none, as in the
 *  edition. */
export function verseLabel(ref: string | null | undefined): string {
  const r = (ref ?? '').trim();
  if (!r) return '';
  const parts = r.split('.');
  return parts[parts.length - 1] || r;
}

/** The English as tokens: *terms* in italics, each note's number after its anchor's first appearance. */
export function withNotes(text: string, anchors: { anchor: string; n: number }[]): ProseToken[] {
  const parts = emphasisParts(text);
  const flat = parts.map((p) => p.text).join('');
  const marks = anchors.map((a, j) => {
    const a2 = plain(a.anchor);
    const at = a2 ? flat.indexOf(a2) : -1;
    return { n: a.n, pos: at >= 0 ? at + a2.length : -1, j };
  });
  const placed = marks.filter((m) => m.pos >= 0).sort((x, y) => x.pos - y.pos || x.j - y.j);
  const out: ProseToken[] = [];
  let off = 0;
  let k = 0;
  for (const p of parts) {
    const end = off + p.text.length;
    let cut = 0;
    while (k < placed.length && placed[k].pos <= end) {
      const at = placed[k].pos - off;
      if (at > cut) out.push({ text: p.text.slice(cut, at), em: p.em });
      cut = Math.max(cut, at);
      out.push({ note: placed[k].n });
      k += 1;
    }
    if (cut < p.text.length) out.push({ text: p.text.slice(cut), em: p.em });
    off = end;
  }
  for (; k < placed.length; k += 1) out.push({ note: placed[k].n });
  for (const m of marks) if (m.pos < 0) out.push({ note: m.n });
  return out;
}

/** The text's scholarly rows as chapters of paragraphs, with their notes. */
export function proseChapters(rows: ProseRow[]): ProseChapter[] {
  const keys = chapterKeys(rows);
  const out: ProseChapter[] = [];
  let cur: ProseChapter | null = null;
  let para: ProseSegment[] = [];
  const flush = () => {
    if (cur && para.length) cur.paragraphs.push(para);
    para = [];
  };
  rows.forEach((r, i) => {
    const s = parseScholar({ page_no: r.page_no, idx: r.idx, scholar: r.scholar, meta: r.meta, fidelity: null,
                            fluency: null, engine: null, made_at: r.made_at });
    if (!s || !s.text.trim()) return;   // a verse given with an earlier one, or none
    const key = keys[i];
    if (!cur || cur.key.kind !== key.kind || cur.key.value !== key.value) {
      flush();
      cur = { id: `ch-${out.length + 1}`, key, label: chapterLabel(key), paragraphs: [], notes: [] };
      out.push(cur);
    }
    const text = s.text.replace(/\s*\/\/\s*/g, ' ').trim();
    const label = verseLabel(s.range || r.verse_ref);
    // the notes in the order their anchors are read; one whose anchor is not found comes last
    const flat = plain(text);
    const ordered = s.notes
      .map((x, j) => {
        const a = plain(x.anchor);
        const at = a ? flat.indexOf(a) : -1;
        return { x, j, at: at >= 0 ? at : flat.length + 1 + j };
      })
      .sort((p, q) => p.at - q.at || p.j - q.j);
    const anchors: { anchor: string; n: number }[] = [];
    for (const o of ordered) {
      const n = cur.notes.length + 1;
      cur.notes.push({ n, ref: label, anchor: plain(o.x.anchor), note: o.x.note });
      anchors.push({ anchor: o.x.anchor, n });
    }
    let tokens = withNotes(text, anchors);
    if (s.doubts) {
      const n = cur.notes.length + 1;
      cur.notes.push({ n, ref: label, anchor: 'The reading', note: s.doubts });
      tokens = [...tokens, { note: n }];
    }
    const seg: ProseSegment = {
      id: `p${r.page_no}-${r.idx}`, page: r.page_no, idx: r.idx, label, tokens,
      flag: s.flag && !s.accepted, title: scholarStatus(s).title,
    };
    if (para.length && (SPEECH.test(text) || para.length >= PARA_MAX)) flush();
    para.push(seg);
  });
  flush();
  return out;
}

/** "3.8" for a mean fidelity, '' for none. */
export function meanScore(v: number | string | null | undefined): string {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) ? n.toFixed(1) : '';
}
