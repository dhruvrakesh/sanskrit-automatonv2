/**
 * The scholarly English of a verse, for the corpus reader - SCHOLAR_READER_2026_10_18.
 *
 * The automaton's scholarly English (scholar_translate.py) is a second, slower translation: made afresh from the
 * Sanskrit in the register of an unabridged critical translation (every word rendered, names and terms kept and
 * explained in notes), read by a critic and revised, then judged verse by verse against the Sanskrit. The mirror
 * (corpus_sync.py, SCHOLAR_MIRROR_2026_10_18) sends it beside the Hindi as two rows a verse, and the reader asks for
 * them with public.corpus_reader_scholar (docs/cloud/C18):
 *   scholar  the English ('' for a verse whose sentence is given with the verse before it);
 *   meta     JSON: status (passed | flagged | source_doubt), flag (waits for a person), accepted (a person read
 *            it), judge, notes [{anchor, note, kind}], doubts, range (a sentence over several verses, on its
 *            first verse), with (on the others).
 * Everything here is parsed defensively: a malformed meta row gives the English alone, never an error, and nothing
 * from the database is ever rendered as HTML.
 */
import type { MirrorScholarRow } from '@/lib/corpusMirror';

export interface ScholarNote {
  anchor: string;
  note: string;
  kind?: string;
}

export interface ScholarReading {
  /** The English; '' when the verse's sentence is given with an earlier verse (see `with`). */
  text: string;
  status: string;
  /** Waits for a person's reading: flagged by the judge, or its Sanskrit in doubt, and not yet accepted. */
  flag: boolean;
  /** A person has read it and accepted it. */
  accepted: boolean;
  /** A sentence over several verses: its range, on its first verse ("81.3-4"). */
  range: string | null;
  /** The verse's English is given with this range, on an earlier verse. */
  with: string | null;
  notes: ScholarNote[];
  doubts: string;
  fidelity: number | null;
  fluency: number | null;
  engine: string | null;
  judge: string | null;
  madeAt: string | null;
}

const str = (v: unknown): string => (typeof v === 'string' ? v.trim() : '');
const num = (v: unknown): number | null => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
};

/** One row of corpus_reader_scholar as a reading, or null when it has neither an English nor a "with". */
export function parseScholar(r: MirrorScholarRow | null | undefined): ScholarReading | null {
  if (!r || typeof r !== 'object') return null;
  let m: Record<string, unknown> = {};
  if (typeof r.meta === 'string' && r.meta.trim()) {
    try {
      const o = JSON.parse(r.meta);
      if (o && typeof o === 'object' && !Array.isArray(o)) m = o as Record<string, unknown>;
    } catch {
      /* a malformed meta row: the English alone */
    }
  }
  const text = typeof r.scholar === 'string' && r.scholar.trim() ? r.scholar : '';
  const withRef = text ? '' : str(m.with);
  if (!text && !withRef) return null;
  const notes: ScholarNote[] = Array.isArray(m.notes)
    ? (m.notes as unknown[]).flatMap((n) => {
      if (!n || typeof n !== 'object') return [];
      const o = n as Record<string, unknown>;
      const note = str(o.note);
      if (!note) return [];
      const kind = str(o.kind);
      return [kind ? { anchor: str(o.anchor), note, kind } : { anchor: str(o.anchor), note }];
    })
    : [];
  const status = str(m.status);
  const accepted = m.accepted === true;
  const flag = typeof m.flag === 'boolean' ? m.flag : (status === 'flagged' || status === 'source_doubt') && !accepted;
  return {
    text,
    status,
    flag,
    accepted,
    range: str(m.range) || null,
    with: withRef || null,
    notes,
    doubts: str(m.doubts),
    fidelity: num(r.fidelity),
    fluency: num(r.fluency),
    engine: str(r.engine) || null,
    judge: str(m.judge) || null,
    madeAt: str(r.made_at) || null,
  };
}

/** The readings of one reader page, by passage anchor ("p<page>-<idx>"). */
export function scholarByPassage(rows: MirrorScholarRow[] | null | undefined): Map<string, ScholarReading> {
  const out = new Map<string, ScholarReading>();
  for (const r of Array.isArray(rows) ? rows : []) {
    if (!r || typeof r.page_no !== 'number' || typeof r.idx !== 'number') continue;
    const s = parseScholar(r);
    if (s) out.set(`p${r.page_no}-${r.idx}`, s);
  }
  return out;
}

/** A *term* in italics, as the edition prints it: the parts of a text, each marked em or not. No HTML. */
export function emphasisParts(t: string | null | undefined): { text: string; em: boolean }[] {
  const out: { text: string; em: boolean }[] = [];
  const src = t ?? '';
  const re = /\*([^*\n]{1,80})\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src)) !== null) {
    if (m.index > last) out.push({ text: src.slice(last, m.index), em: false });
    out.push({ text: m[1], em: true });
    last = m.index + m[0].length;
  }
  if (last < src.length) out.push({ text: src.slice(last), em: false });
  return out;
}

/** 'anthropic:claude-sonnet-5-5' as 'Claude Sonnet 5.5'; 'gemini:gemini-2.5-flash' as 'Gemini 2.5 Flash'. */
export function engineName(e: string | null | undefined): string {
  const s = (e ?? '').trim();
  const c = /^anthropic:claude-([a-z]+)-(\d+)-(\d+)/.exec(s);
  if (c) return `Claude ${c[1][0].toUpperCase()}${c[1].slice(1)} ${c[2]}.${c[3]}`;
  const g = /^gemini:gemini-(\d+\.\d+)-([a-z]+)/.exec(s);
  if (g) return `Gemini ${g[1]} ${g[2][0].toUpperCase()}${g[2].slice(1)}`;
  return s;
}

export interface ScholarStatus {
  key: 'read' | 'passed' | 'flagged' | 'doubt' | 'other';
  label: string;
  title: string;
}

/** What the reader says of a verse's scholarly English: read by a person, judged faithful, flagged, or doubted. */
export function scholarStatus(s: ScholarReading): ScholarStatus {
  const by = s.judge ? ` by ${engineName(s.judge)}` : '';
  const score = s.fidelity != null ? ` (fidelity ${s.fidelity} of 5${s.fluency != null ? `, fluency ${s.fluency} of 5` : ''})` : '';
  if (s.accepted) return { key: 'read', label: 'read by a person', title: 'A person has read this English against the Sanskrit and accepted it.' };
  if (s.status === 'source_doubt') {
    return { key: 'doubt', label: 'the Sanskrit in doubt', title: `The translator doubts the reading of the Sanskrit here${score}; it waits for a person's reading.` };
  }
  if (s.flag || s.status === 'flagged') {
    return { key: 'flagged', label: 'flagged by the judge', title: `Judged against the Sanskrit${by}${score}: a possible error was found; it waits for a person's reading.` };
  }
  if (s.status === 'passed') {
    return { key: 'passed', label: 'judged faithful', title: `Judged verse by verse against the Sanskrit${by}${score}; not yet read by a person.` };
  }
  return { key: 'other', label: s.status || 'scholarly', title: 'Not yet read by a person.' };
}
