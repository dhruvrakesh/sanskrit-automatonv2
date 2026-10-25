/**
 * The indexes' genealogies - INDEX_SITE_2026_10_25.
 *
 * The desk's Vamsa page (127.0.0.1:5057/vamsa) on the site, for signed-in readers: the lines of descent of three
 * indexes of names - V. R. Ramachandra Dikshitar's Purana Index, S. Soerensen's Index to the Names in the Mahabharata,
 * Macdonell and Keith's Vedic Index - each step with what it rests on: the index's own words and references, the
 * Sanskrit verse where both names stand (GRETIL's editions, read on the desk by vamsa_check.py), the verses of the
 * epics that name both (counted; the Mahabharata e-text's words are never sent), and our own passages that name both.
 * Computed on the desk (scripts/index_sync.py), sent to the private mirror, read here through five reader functions
 * (docs/cloud/C21 in the automaton repo):
 *   corpus_reader_index_overview()                    the indexes, their counts and credits, the GRETIL texts;
 *   corpus_reader_index_lines(source)                 the longest lines of each index;
 *   corpus_reader_index_find(fold, source, k)         persons by the index's head word, folded;
 *   corpus_reader_index_tree(source, entry, via, n)   one person: the line up and down, each step's evidence;
 *   corpus_reader_index_of_name(canonical)            a name of ours: its persons in the indexes and what they state.
 * The overview, a tree and a name come as one row, { result }. Nothing from the database is rendered as HTML.
 */
import { callMirror, functionMissing, type MirrorResult } from '@/lib/corpusMirror';

export const SOURCES = ['pui', 'inm', 'vei'] as const;
export type IndexSource = (typeof SOURCES)[number];

/** Short names for the indexes, as the page's filter shows them. */
export const SOURCE_SHORT: Record<string, string> = {
  pui: 'Purāṇa Index',
  inm: 'Mahābhārata names',
  vei: 'Vedic Index',
};

/** The texts whose verses are cited, as the desk names them (vamsa.html SHOWN). */
export const TEXT_SHORT: Record<string, string> = {
  vi: 'Viṣṇu (1910)', vic: 'Viṣṇu (crit.)', bh: 'Bhāgavata', br: 'Brahmāṇḍa', m: 'Matsya', hv: 'Harivaṃśa',
  ram: 'Rāmāyaṇa', mbh: 'Mahābhārata',
};

/** The epics whose verses that name both are counted, as the desk shows them. */
export const EPICS: readonly { code: string; label: string }[] = [
  { code: 'mbh', label: 'MBh' }, { code: 'hv', label: 'HV' }, { code: 'ram', label: 'Rām' },
];

export interface IndexName { entry: number; head: string }

export interface IndexPerson extends IndexName {
  sex: string;
  named_only: boolean;
  parents: number;
  children: number;
  up: number;
  down: number;
  canonical: string | null;
  spouses: IndexName[];
}

export interface Cite {
  text?: string;
  ref?: string;
  verdict?: string;
  printed?: string;
  at?: string[];
  subject_form?: string;
  object_form?: string;
}

export interface Place { doc: string; page: number; idx: number; ref: string }

export interface Statement {
  key: string;
  source: string;
  stated_in: string;
  entry_id: number;
  relation: string;
  subject: string;
  object: string;
  words: string;
  refs: string[];
  n: number;
  subject_entry: number | null;
  object_entry: number | null;
  subject_canonical: string | null;
  object_canonical: string | null;
  ours: string;
  passages: number;
  texts: number;
  places: Place[];
  cited: string;
  cites: Cite[];
  best_text: string;
  best_ref: string;
  together: Record<string, [number, string]>;
}

export interface Step {
  parent: number;
  child: number;
  joined: string;
  both_entries: boolean;
  cited: string;
  ours: string;
  epic: Record<string, [number, string]>;
  items: Statement[];
}

export interface Rung extends IndexPerson {
  generation: number;
  siblings: IndexName[];
  siblings_n: number;
  other_parents: (IndexPerson & { evidence: Step | null })[];
}

export interface Descendant extends IndexPerson { of: number; on_line: boolean; evidence: Step | null }

export interface TextInfo { title: string; edition: string; rights: string; show: boolean }

export interface Tree {
  source: string;
  entry: number;
  me: number;
  title: string | null;
  person: IndexPerson;
  line: Rung[];
  steps: Step[];
  down: Descendant[][];
  verses: Record<string, string>;
  texts: Record<string, TextInfo>;
}

export interface SourceInfo {
  source: string;
  title: string;
  edition: string;
  rights: string;
  persons: number;
  tied: number;
  steps: number;
  statements: number;
  lines: number;
}

export interface Overview {
  sources: SourceInfo[];
  texts: (TextInfo & { code: string })[];
  run: { mark?: string; counts?: Record<string, number>; checked?: string; synced_at?: string } | null;
}

export interface FindHit { source: string; entry: number; head: string; sex: string; up: number; down: number; canonical: string | null; exact: boolean }

export interface LineRow { source: string; rank: number; entries: number[]; heads: string[]; length: number; both_steps: number }

export interface NamePerson { source: string; entry: number; head: string; sex: string; up: number; down: number; parents: number; children: number; has_line: boolean }

export interface OfName { persons: NamePerson[]; statements: Statement[]; statements_n: number }

/** A list from the mirror, and whether the database has the function at all (C21 not applied: missing). */
export interface IndexResult<T> extends MirrorResult<T> { missing: boolean }

/** One answer from the mirror (the overview, a tree, a name), or null with the reason. */
export interface IndexOne<T> { ok: boolean; value: T | null; error: string | null; refused: boolean; missing: boolean }

async function list<T>(fn: string, args: Record<string, unknown>): Promise<IndexResult<T>> {
  const r = await callMirror<T>(fn, args);
  return { ...r, missing: functionMissing(r, fn) };
}

async function one<T>(fn: string, args: Record<string, unknown>): Promise<IndexOne<T>> {
  const r = await list<{ result: T | null }>(fn, args);
  if (!r.ok) return { ok: false, value: null, error: r.error, refused: r.refused, missing: r.missing };
  const v = r.rows.length ? r.rows[0]?.result ?? null : null;
  if (!v || typeof v !== 'object') {
    return { ok: false, value: null, error: 'The genealogies answered in an unexpected form.', refused: false, missing: false };
  }
  const e = (v as { error?: unknown }).error;
  if (typeof e === 'string' && e) return { ok: false, value: null, error: e, refused: false, missing: false };
  return { ok: true, value: v, error: null, refused: false, missing: false };
}

export function loadIndexOverview(): Promise<IndexOne<Overview>> {
  return one<Overview>('corpus_reader_index_overview', {});
}

export function loadIndexLines(source: string | null = null): Promise<IndexResult<LineRow>> {
  return list<LineRow>('corpus_reader_index_lines', { p_source: source });
}

/** Persons by the index's head word: needs two letters after folding. */
export function findIndexPersons(q: string, source: string | null = null, k = 20): Promise<IndexResult<FindHit>> {
  const f = foldName(q);
  if (f.length < 2) return Promise.resolve({ ok: true, rows: [], error: null, refused: false, missing: false });
  return list<FindHit>('corpus_reader_index_find', { p_fold: f, p_source: source, p_k: Math.max(1, Math.min(50, k)) });
}

export function loadIndexTree(source: string, entry: number, via: number | null = null, down = 2): Promise<IndexOne<Tree>> {
  return one<Tree>('corpus_reader_index_tree', {
    p_source: source, p_entry: entry, p_via: via, p_down: Math.max(0, Math.min(4, down)),
  });
}

export function loadIndexOfName(canonical: string): Promise<IndexOne<OfName>> {
  return one<OfName>('corpus_reader_index_of_name', { p_canonical: canonical });
}

// ---- names, folded as the desk folds them -----------------------------------------------------------------------

const HONORIFIC = /^\s*(?:śrī|Śrī|sri|shri|śrīmat|bhagavat)\s+/i;           // vamsa_view.py HONORIFIC
const MARK_LEAD = /^(\d{1,2})\.\s+(.+)$/;                                    // relations_view.split_mark
const MARK_TAIL = /\s*(?:\((\d{1,2}|[ivxlc]{1,6})\)|\[(\d{1,2})\])\s*$/i;

/** The index's head word folded as the desk folds it (relations_view.fold of split_mark): the honorific and the
 *  homonym's number left out, the diacritics taken off, letters and digits only. "Daśaratha (II)" -> "dasaratha". */
export function foldName(s: string): string {
  let t = (s ?? '').trim().replace(HONORIFIC, '');
  const lead = MARK_LEAD.exec(t);
  if (lead) t = lead[2];
  else t = t.replace(MARK_TAIL, '');
  t = t.replace(/\([^)]*\)|\[[^\]]*\]/g, ' ');
  return t.normalize('NFKD').toLowerCase().replace(/\p{M}/gu, '').replace(/[^a-z0-9]+/g, '');
}

// ---- addresses ------------------------------------------------------------------------------------------------

export const GENEALOGIES = '/corpus/genealogies';

export function personHref(source: string, entry: number, via: number | null = null): string {
  const base = `${GENEALOGIES}/${encodeURIComponent(source)}/${entry}`;
  return via != null ? `${base}?via=${via}` : base;
}

/** A place in our own texts, in the reader (it finds its page from ?at=). */
export function placeHref(p: Place): string {
  return `/corpus/${encodeURIComponent(p.doc)}?at=${p.page}.${p.idx}`;
}

export function nameHrefOf(canonical: string): string {
  return `/corpus/names/${encodeURIComponent(canonical)}`;
}

// ---- what the steps rest on, in words ---------------------------------------------------------------------------

export type Tone = 'ok' | 'half' | 'no' | 'ep';
export interface Chip { label: string; tone: Tone; title: string }

const CITED: Record<string, Chip> = {
  both: { label: 'verse ✓', tone: 'ok', title: 'Both names stand in the verse the index cites' },
  one: { label: 'one name', tone: 'half', title: 'One of the two names stands in the cited verse' },
  neither: { label: 'neither name', tone: 'no', title: 'Neither name stands in the cited verse or the two on each side of it' },
  'not held': { label: 'not held', tone: 'no', title: 'The index cites a text we do not hold in Sanskrit (the Vāyu; the Matsya after chapter 176)' },
  'no verse': { label: 'no such verse', tone: 'no', title: 'The edition has no verse of that number' },
};

/** The chips of a step, as the desk draws them: the cited verse, the epics, our passages, how the persons were told apart. */
export function stepChips(st: Pick<Step, 'cited' | 'epic' | 'ours' | 'joined'>): Chip[] {
  const out: Chip[] = [];
  const c = CITED[st.cited];
  if (c) out.push(c);
  for (const e of EPICS) {
    const n = st.epic?.[e.code]?.[0] ?? 0;
    if (n > 0) out.push({ label: `${e.label} ${n}`, tone: 'ep', title: `${n} ${n === 1 ? 'verse' : 'verses'} of the ${TEXT_SHORT[e.code] ?? e.code} name both` });
  }
  if (st.ours === 'named together') out.push({ label: 'ours: together', tone: 'ok', title: 'One of our own passages names both' });
  else if (st.ours === 'named near') out.push({ label: 'ours: near', tone: 'ep', title: 'Our own passages name both within a few passages' });
  if (st.joined === 'verse') out.push({ label: 'by a shared verse', tone: 'half', title: 'The name has several entries; the one whose entry cites the same verse was taken' });
  else if (st.joined === 'named') out.push({ label: 'a name only', tone: 'no', title: 'The index names this person, but its entries of that name cannot be told apart' });
  if (!out.length) out.push({ label: 'the index alone', tone: 'no', title: 'Only the index states this step' });
  return out;
}

/** The desk's groups of relations (relations_view.py GROUPS), in the order a name's page lists them. */
export const RELATION_GROUPS: readonly { key: string; label: string; relations: readonly string[] }[] = [
  { key: 'family', label: 'Family', relations: ['son_of', 'daughter_of', 'father_of', 'mother_of', 'grandson_of', 'granddaughter_of', 'grandfather_of', 'descendant_of', 'ancestor_of'] },
  { key: 'marriage', label: 'Marriage', relations: ['wife_of', 'husband_of', 'married'] },
  { key: 'siblings', label: 'Brothers and sisters', relations: ['brother_of', 'sister_of'] },
  { key: 'rule', label: 'Rule', relations: ['king_of', 'queen_of', 'successor_of', 'predecessor_of'] },
  { key: 'learning', label: 'Teachers, pupils and patrons', relations: ['pupil_of', 'teacher_of', 'priest_of', 'patron_of'] },
  { key: 'time', label: 'Contemporaries', relations: ['contemporary_of'] },
];

/** Statements in the desk's groups, in order; a relation of no group goes last, as "Other". */
export function groupStatements<T extends Pick<Statement, 'relation'>>(rows: readonly T[]): { key: string; label: string; rows: T[] }[] {
  const out = RELATION_GROUPS.map((g) => ({ key: g.key, label: g.label, rows: [] as T[] }));
  const other = { key: 'other', label: 'Other', rows: [] as T[] };
  for (const r of rows) {
    const i = RELATION_GROUPS.findIndex((g) => g.relations.includes(r.relation));
    (i >= 0 ? out[i] : other).rows.push(r);
  }
  return [...out, other].filter((g) => g.rows.length > 0);
}

export function relationLabel(relation: string): string {
  return (relation ?? '').replace(/_/g, ' ');
}

/** What a statement's own check says when no verse is shown for it. */
export function citedNote(cited: string): string {
  switch (cited) {
    case 'not held': return 'The index cites a text we do not hold in Sanskrit (the Vāyu; the Matsya after chapter 176).';
    case 'no citation': return 'The index gives no verse for this statement.';
    case 'neither': return 'Neither name stands in the cited verse or the two on each side of it: the edition may differ, or the index.';
    case 'no verse': return 'The edition has no verse of that number.';
    default: return '';
  }
}

/** Names for a list: a name the index gives without an entry, stated in several places, once with its count
 *  ("Yayāti ×3", the first of them linked); a person with an entry is always shown apart. */
export function collapseNames<T extends IndexName>(names: readonly T[]): (T & { times: number })[] {
  const out: (T & { times: number })[] = [];
  const seen = new Map<string, T & { times: number }>();
  for (const n of names) {
    if (n.entry < 0) {
      const had = seen.get(n.head);
      if (had) { had.times += 1; continue; }
      const x = { ...n, times: 1 };
      seen.set(n.head, x);
      out.push(x);
    } else {
      out.push({ ...n, times: 1 });
    }
  }
  return out;
}

/** A long verse (the Harivamsa's e-text runs whole passages together) is cut to this many characters until opened. */
export const VERSE_CLAMP = 360;

/** A generation's label: 0 for the person, -3 three above, +2 two below. */
export function generationLabel(g: number): string {
  return g > 0 ? `+${g}` : String(g);
}

export interface CiteBlock {
  text: string;
  ref: string;
  printed: string;
  verdict: string;
  verses: { ref: string; words: string; forms: string[] }[];
}

/** A statement's citations that found a name, as the desk shows them (vamsa.html showStep): each with up to two of
 *  its verses where the site may show the Sanskrit (GRETIL's texts; never the Mahabharata e-text), two verses in all. */
export function citeBlocks(it: Pick<Statement, 'cites'>, verses: Record<string, string>): CiteBlock[] {
  const out: CiteBlock[] = [];
  let shown = 0;
  for (const cv of it.cites ?? []) {
    if (shown >= 2 || (cv.verdict !== 'both' && cv.verdict !== 'one')) continue;
    const at = cv.at && cv.at.length ? cv.at : [cv.ref ?? ''];
    const vs: CiteBlock['verses'] = [];
    for (const ref of at.slice(0, 2)) {
      const w = verses[`${cv.text}|${ref}`];
      if (w) {
        vs.push({ ref, words: w, forms: [cv.subject_form ?? '', cv.object_form ?? ''].filter(Boolean) });
        shown += 1;
      }
    }
    out.push({ text: cv.text ?? '', ref: cv.ref ?? '', printed: cv.printed ?? '', verdict: cv.verdict, verses: vs });
  }
  return out;
}

/** A verse split where the two names stand, for <mark> without any HTML from the server. */
export function markForms(words: string, forms: string[]): { text: string; mark: boolean }[] {
  const spans: [number, number][] = [];
  for (const f of forms) {
    if (!f) continue;
    const k = words.indexOf(f);
    if (k >= 0 && !spans.some(([a, b]) => k < b && k + f.length > a)) spans.push([k, k + f.length]);
  }
  spans.sort((a, b) => a[0] - b[0]);
  const out: { text: string; mark: boolean }[] = [];
  let at = 0;
  for (const [a, b] of spans) {
    if (a > at) out.push({ text: words.slice(at, a), mark: false });
    out.push({ text: words.slice(a, b), mark: true });
    at = b;
  }
  if (at < words.length) out.push({ text: words.slice(at), mark: false });
  return out;
}

/** The epics' verses that name both, in words: "MBh 1.90.47 and 4 more; HV 23.110". */
export function epicLine(together: Record<string, [number, string]> | undefined): string {
  const parts: string[] = [];
  for (const e of EPICS) {
    const t = together?.[e.code];
    if (t && t[0] > 0 && t[1]) parts.push(`${e.label} ${t[1]}${t[0] > 1 ? ` and ${t[0] - 1} more` : ''}`);
  }
  return parts.join('; ');
}

/** The credit of the three indexes, as the desk gives it. */
export const INDEX_CREDIT =
  'The relations: V. R. Ramachandra Dikshitar, The Purana Index (Madras, 1951-55); S. Soerensen, An Index to the Names ' +
  'in the Mahabharata (London, 1904-25); A. A. Macdonell and A. B. Keith, Vedic Index of Names and Subjects (London, ' +
  '1912): read from the Cologne Digital Sanskrit Dictionaries\' e-texts, each statement checked against the entry\'s ' +
  'own words, and given here with those words under the Cologne licence, CC BY-NC-SA 3.0.';
export const LICENCE_URL = 'https://creativecommons.org/licenses/by-nc-sa/3.0/';
export const CAUTION = 'A verse where both names stand says where to read; it does not by itself prove the relation.';
