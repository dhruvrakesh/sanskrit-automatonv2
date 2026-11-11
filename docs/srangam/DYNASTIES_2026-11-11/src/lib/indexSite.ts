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
 *
 * B2_SITE_2026_10_28 (docs/cloud/C23): a scholar's view of each relation. The desk weighs every kinship of the indexes
 * against Hemchandra Raychaudhuri's Political History of Ancient India (1923; public domain), read from its scan page
 * by page, each claim checked against the page's own words: a statement carries `scholars` (the book states it too:
 * agrees; another relation of the same two: differs; the other way round: reversed), a step its best `scholar`, a
 * tree the claims of its shown statements (`claims`, by key) and the works (`works`), a name what the works say of it
 * (`claims`, `claims_n`), the overview the works with their counts. Before C23 none of these come, and nothing changes.
 *
 * GENEALOGY_HEAL_2026_11_10 (docs/cloud/C26, docs/GENEALOGY_2026-11-10.md): asked on 10 Nov, "such a genealogy front end
 * does not make sense for anybody ... we cant even get the genealogy of Kaunteya (Arjun) right". The desk now draws a
 * son begotten by another (Arjuna by Indra) through his mother's husband (Pandu), never lets a line turn back on itself,
 * joins a name of several entries by the names both entries give ("shared"), and ties an epithet ("Kaunteya, the son
 * of Kunti, = Arjuna") to the person: a person carries `same_as` and `gloss`, a found name too (C26; absent before).
 * The pages say in plain words what each mark means (GUIDE) and send an epithet to the person it names.
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
  /** GENEALOGY_HEAL_2026_11_10 (C26): the persons this entry names ("= Arjuna"), and the entry's own gloss. */
  same_as?: SameAs[];
  gloss?: string;
}

/** GENEALOGY_HEAL_2026_11_10: a person an entry names, and how the desk told which entry of that name is meant. */
export interface SameAs { entry: number; head: string; how: string }

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
  /** B2_SITE_2026_10_28: what the scholars' works say of this relation (C23; absent before it). */
  scholars?: ScholarView[];
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
  /** B2_SITE_2026_10_28: the best scholar's verdict of the step's statements (agrees, differs, reversed; C23). */
  scholar?: string;
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
  /** B2_SITE_2026_10_28 (C23): the scholars' works, and the claims the shown statements rest on, by key. */
  works?: Record<string, TextInfo>;
  claims?: Record<string, Claim>;
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
  /** B2_SITE_2026_10_28 (C23): the scholars' works with their claims. */
  works?: WorkInfo[];
  run: { mark?: string; counts?: Record<string, number>; checked?: string; synced_at?: string } | null;
}

export interface FindHit {
  source: string; entry: number; head: string; sex: string; up: number; down: number; canonical: string | null; exact: boolean;
  /** GENEALOGY_HEAL_2026_11_10 (C26): an epithet's persons; has_line false for an epithet without a line of its own. */
  same_as?: SameAs[]; gloss?: string; has_line?: boolean;
}

export interface LineRow { source: string; rank: number; entries: number[]; heads: string[]; length: number; both_steps: number }

export interface NamePerson { source: string; entry: number; head: string; sex: string; up: number; down: number; parents: number; children: number; has_line: boolean }

export interface OfName {
  persons: NamePerson[];
  statements: Statement[];
  statements_n: number;
  /** B2_SITE_2026_10_28 (C23): what the scholars' works say of the name, in the book's order (60 at most). */
  claims?: Claim[];
  claims_n?: number;
}

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

// ---- DYNASTIES_2026_11_11: the Puranas' own lines (docs/cloud/C28_index_dynasties_2026-11-11.sql in the automaton repo)

export const DYNASTIES = '/corpus/genealogies/dynasties';

/** One step of a line: a person, the father the text gives, the verse and its words, the index's person and verdict. */
export interface DynastyStep {
  name: string; father?: string; ref?: string; words?: string; person?: string; index_head?: string;
  how?: string; index?: string; joined?: string; page?: boolean;
}
export interface DynastyCounts {
  persons?: number; father?: number; name?: number; none?: number; joined?: number;
  agrees?: number; differs?: number; new?: number; absent?: number;
}
/** A line ("vip4:1"), or a work's own row ("vip4:0": n 0, its counts). */
export interface DynastyRow {
  key: string; work: string; n: number; title: string; text_code: string; label: string; length: number;
  steps: DynastyStep[]; counts: DynastyCounts; source: string;
}

export function loadDynasties(work: string | null = null): Promise<IndexResult<DynastyRow>> {
  return list<DynastyRow>('corpus_reader_index_dynasties', { p_work: work });
}

export const WORK_ORDER: readonly string[] = ['vip4', 'bhp9', 'bhp12'];
export const WORK_TITLE: Record<string, string> = {
  vip4: 'Viṣṇupurāṇa, book 4', bhp9: 'Bhāgavatapurāṇa, book 9', bhp12: 'Bhāgavatapurāṇa 12.1',
};

/** What the Purana Index says of a step, in words. */
export const INDEX_SAYS: Record<string, Chip> = {
  agrees: { label: 'index agrees', tone: 'ok', title: 'Dikshitar\'s Purāṇa Index gives this person the same father' },
  differs: { label: 'index differs', tone: 'half', title: 'The index has a person of this name, with another father' },
  new: { label: 'no father in the index', tone: 'half', title: 'The index has this person, and no father for him' },
  absent: { label: 'not in the index', tone: 'no', title: 'The index has no person of this name' },
};

/** The person's page on the genealogies (/corpus/genealogies/pui/123) when the site has one, else null. */
export function dynastyPersonHref(s: Pick<DynastyStep, 'person' | 'page'>): string | null {
  if (!s.page || !s.person) return null;
  const m = /^([a-z]+):(-?\d+)$/.exec(s.person);
  return m ? personHref(m[1], Number(m[2])) : null;
}

/** The work's counts, in a sentence. */
export function dynastyCountsText(c: DynastyCounts): string {
  const n = (v?: number) => new Intl.NumberFormat('en-IN').format(Number(v ?? 0));
  const found = Number(c.father ?? 0) + Number(c.name ?? 0);
  return `${n(c.persons)} persons; ${n(found)} found in the Purāṇa Index (${n(c.father)} with the same father); ` +
    `${n(c.differs)} with another father there; ${n(c.absent)} not in it.`;
}

export const DYNASTY_GUIDE: readonly { term: string; text: string }[] = [
  { term: 'What a line is', text: 'The persons the Purāṇa itself names, father to son, as its genealogical book tells them: each step is a statement of the text ("his son was Vikukṣi"), with the verse that makes it. A line starts from a father the text names without his own father here.' },
  { term: 'How it was read', text: 'A model (Claude) read the Sanskrit chapter by chapter and listed every statement of kinship it makes, with the verse and the words that say it; each was then checked by machine against GRETIL\'s text of that verse. Only the statements whose words and both names stand in their verse are drawn here.' },
  { term: 'Two persons of one name', text: 'A person is a name and the father the text gives him. Two persons of one name in different lines (two Sṛñjayas) are kept apart: a father is joined to a son of his name in the same chapter or the one before, or where the Purāṇa Index shows they are one person ("joined by the index").' },
  { term: 'The chips', text: 'index agrees: Dikshitar\'s Purāṇa Index gives the person the same father. index differs: the index has a person of that name with another father (a disagreement worth reading). no father in the index: the index has the person and no father. not in the index: the index has no such person.' },
  { term: 'The links', text: 'A name in burgundy opens that person\'s page in the Genealogies (the index\'s line, with what each step rests on).' },
  { term: 'What it is not yet', text: 'The lines of the Viṣṇupurāṇa and of the Bhāgavatapurāṇa are drawn apart; where the two Purāṇas differ is for the reader to see, and for our findings to come.' },
];

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

/** B2_SITE_2026_10_28: a scholar's view of a step (C23), as a chip. */
const SCHOLAR_CHIP: Record<string, Chip> = {
  agrees: { label: 'Raychaudhuri agrees', tone: 'ok', title: 'Raychaudhuri\'s Political History of Ancient India (1923) states this relation too' },
  differs: { label: 'Raychaudhuri: another relation', tone: 'half', title: 'Raychaudhuri (1923) states another relation of the same two persons' },
  reversed: { label: 'Raychaudhuri: the other way', tone: 'half', title: 'Raychaudhuri (1923) states this relation the other way round' },
};

/** The chips of a step, as the desk draws them: the cited verse, the epics, our passages, the scholar's view
 *  (B2_SITE_2026_10_28), how the persons were told apart. */
export function stepChips(st: Pick<Step, 'cited' | 'epic' | 'ours' | 'joined'> & { scholar?: string }): Chip[] {
  const out: Chip[] = [];
  const c = CITED[st.cited];
  if (c) out.push(c);
  for (const e of EPICS) {
    const n = st.epic?.[e.code]?.[0] ?? 0;
    if (n > 0) out.push({ label: `${e.label} ${n}`, tone: 'ep', title: `${n} ${n === 1 ? 'verse' : 'verses'} of the ${TEXT_SHORT[e.code] ?? e.code} name both` });
  }
  if (st.ours === 'named together') out.push({ label: 'ours: together', tone: 'ok', title: 'One of our own passages names both' });
  else if (st.ours === 'named near') out.push({ label: 'ours: near', tone: 'ep', title: 'Our own passages name both within a few passages' });
  const sc = st.scholar ? SCHOLAR_CHIP[st.scholar] : undefined;
  if (sc) out.push(sc);
  if (st.joined === 'verse') out.push({ label: 'by a shared verse', tone: 'half', title: 'The name has several entries; the one whose entry cites the same verse was taken' });
  else if (st.joined === 'shared') out.push({ label: JOIN_SHARED, tone: 'half', title: 'The name has several entries; the one whose entry names three or more of the same persons was taken' });
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

// ---- B2_SITE_2026_10_28: a scholar's view (docs/cloud/C23) -------------------------------------------------------

/** A scholar's view of one relation of an index, as the desk weighs it (kin_index.py): the book states the relation
 *  too (agrees), another relation of the same two (differs), or the same relation the other way round (reversed). */
export interface ScholarView { work: string; verdict: string; note: string; claims: string[] }

export interface ClaimCite { printed?: string; work?: string; locus?: string; ours?: string | null; note?: string }

/** One claim of a scholar's work, read from its scan page (scholar_claims.py), its quotation found on the page. */
export interface Claim {
  key: string;
  work: string;
  pdf_page: number;
  printed: string | null;
  n: number;
  subject: string;
  relation: string;
  object: string | null;
  claim: string;
  quote: string | null;
  quote_check: string | null;
  stance: string | null;
  hedge: string | null;
  subject_canonical: string | null;
  subject_how: string | null;
  object_canonical: string | null;
  object_how: string | null;
  cites: ClaimCite[];
}

export interface WorkInfo extends TextInfo { code: string; claims: number }

/** Short names for the scholars' works, as a chip shows them. */
export const WORK_SHORT: Record<string, string> = { phai1923: 'Raychaudhuri' };

/** The verdicts in the order the desk ranks them (kin_index.py SCHOLAR_ORDER). */
export const VERDICTS = ['agrees', 'differs', 'reversed'] as const;

/** A scholar's verdict, in words: "Raychaudhuri (1923) states it too". */
export function verdictText(v: Pick<ScholarView, 'work' | 'verdict'>, works?: Record<string, Pick<TextInfo, 'title'>>): string {
  const who = WORK_SHORT[v.work] ?? works?.[v.work]?.title ?? v.work;
  const year = /(\d{4})$/.exec(v.work)?.[1];
  const name = year ? `${who} (${year})` : who;
  switch (v.verdict) {
    case 'agrees': return `${name} states it too`;
    case 'differs': return `${name} states another relation of the two`;
    case 'reversed': return `${name} states it the other way round`;
    default: return name;
  }
}

/** How a name of the book was tied to one of ours: certain (the same name, or with its number), else probable. */
export function tieLabel(how: string | null | undefined): '' | 'certain' | 'probable' {
  if (!how) return '';
  return how === 'exact' || how === 'numbered exact' ? 'certain' : 'probable';
}

/** The book's page as the book prints it ("p. 37"; a front-matter page "p. ii"), else the scan's. */
export function claimPage(c: Pick<Claim, 'printed' | 'pdf_page'>): string {
  return c.printed ? `p. ${c.printed}` : `scan p. ${c.pdf_page}`;
}

/** The claims a statement's views rest on, in order, each once, those the tree has. */
export function viewClaims(views: readonly ScholarView[] | undefined, claims: Record<string, Claim> | undefined): Claim[] {
  const out: Claim[] = [];
  const seen = new Set<string>();
  for (const v of views ?? []) {
    for (const k of v.claims ?? []) {
      const c = claims?.[k];
      if (c && !seen.has(k)) { seen.add(k); out.push(c); }
    }
  }
  return out;
}

const TONE_RANK: Record<Tone, number> = { ok: 3, ep: 2, half: 1, no: 0 };

/** How well a step is attested, for the strip over the line: the best of its chips ("the index alone" is "no"). */
export function stepStrength(st: Pick<Step, 'cited' | 'epic' | 'ours' | 'joined'> & { scholar?: string }): Tone {
  let best: Tone = 'no';
  for (const c of stepChips(st)) {
    if (c.label === 'a name only' || c.label === 'by a shared verse' || c.label === JOIN_SHARED) continue;   // how the persons were told apart
    if (TONE_RANK[c.tone] > TONE_RANK[best]) best = c.tone;
  }
  return best;
}

/** The line's steps counted by what they rest on, for its header. */
export function lineCounts(steps: readonly (Pick<Step, 'cited' | 'epic' | 'ours'> & { scholar?: string })[]) {
  let verse = 0; let epic = 0; let ours = 0; let agrees = 0; let otherwise = 0;
  for (const s of steps) {
    if (s.cited === 'both') verse += 1;
    if (EPICS.some((e) => (s.epic?.[e.code]?.[0] ?? 0) > 0)) epic += 1;
    if (s.ours === 'named together') ours += 1;
    if (s.scholar === 'agrees') agrees += 1;
    else if (s.scholar === 'differs' || s.scholar === 'reversed') otherwise += 1;
  }
  return { verse, epic, ours, agrees, otherwise };
}

/** The credit of the scholars' works, from their rows (C23): the work, its edition and its rights. */
export const CLAIMS_CREDIT =
  'The scholars\' claims were read from the scan of each work page by page by a model, each checked against the ' +
  'page\'s own words; the quotations are as the scan reads them, uncorrected. Only works in the public domain are shown.';

// ---- GENEALOGY_HEAL_2026_11_10: the epithets, and the page in plain words -----------------------------------------

/** A step whose name had several entries, joined by the names both entries give (vamsa_view.py "shared"). */
export const JOIN_SHARED = 'by the names both entries give';

const NOT_TOLD = 'several entries of that name, not told apart';

/** What an entry's epithet says: one person ("Kaunteya¹ = Arjuna"), a group ("the sons of Kunti": four persons), or
 *  several entries of one name the desk could not tell apart; '' when the entry names no one. */
export function epithetKind(p: Pick<IndexPerson, 'same_as'>): '' | 'one' | 'group' | 'unsure' {
  const xs = p.same_as ?? [];
  if (!xs.length) return '';
  if (xs.every((x) => x.how === NOT_TOLD)) return 'unsure';
  return xs.length === 1 ? 'one' : 'group';
}

/** How the desk told an epithet's person apart, in words for a title. */
export function epithetHow(how: string): string {
  switch (how) {
    case "the entry's number": return 'the index gives the entry\'s number';
    case "the index's only entry of that name": return 'the index has one entry of that name';
    case 'the only entry of that name with a line': return 'the only entry of that name with parents or children';
    case 'the entry of that name with the most kin in the index': return 'the entry of that name the index says most of';
    case 'the singular entries of this name': return 'the persons the singular entries of this name name';
    case NOT_TOLD: return 'the index has several entries of that name and does not say which';
    default: return how;
  }
}

/** A word on each index under a person's name: why some marks never show for it. */
export const SOURCE_NOTE: Record<string, string> = {
  inm: 'Sørensen cites the Calcutta edition of the Mahābhārata (1834–39) by its running verse numbers, which the ' +
    'critical edition does not keep, so none of his steps can show a cited verse with both names; the strip shows ' +
    'instead how many verses of the epics name both.',
  pui: 'Dikshitar cites the Purāṇas by book, chapter and verse; where we hold the Purāṇa in Sanskrit (GRETIL), the ' +
    'cited verse was read and the two names looked for in it. The Vāyu is not held.',
  vei: 'Macdonell and Keith cite the Vedic texts; their references are given as printed.',
};

/** The page in plain words: what a line is, what each mark means, and what it is not. */
export const GUIDE: readonly { term: string; text: string }[] = [
  { term: 'What a line is', text: 'The chain of parent-to-child steps one index states, drawn up through the father and down through the son whose own line runs longest. It is the index\'s statements joined by machine, not a dynasty a historian compiled; each step says what it rests on.' },
  { term: 'The numbers on the left', text: '0 is the person you opened; −1 a parent, −2 a grandparent; +1 a child, +2 a grandchild.' },
  { term: 'The coloured strip', text: 'One square for each step, eldest first; click one to see that step. Green: a verse the index cites names both persons, one of our own passages names both, or the historian beside the indexes states the relation too. Blue: verses of the Mahābhārata, Harivaṃśa or Rāmāyaṇa name both. Amber: one of the two names stands in the cited verse, or the historian states another relation. Grey: the index alone.' },
  { term: 'The chips between two persons', text: 'verse ✓: both names stand in the verse the index cites. MBh 7, HV 2, Rām 1: that many verses of the epic name both (counted by machine; the Mahābhārata\'s words are never shown). ours: together: one of our own passages names both. A solid rail: both persons\' entries state the step; dashed: one entry does.' },
  { term: 'Two fathers', text: 'A son begotten on a king\'s wife by a god or a sage has two fathers in the index (Arjuna: Pāṇḍu and Indra). The line runs through the mother\'s husband, as the dynasties count him; the begetter is shown beside him, and "line through" draws the line up through him instead.' },
  { term: 'Epithets', text: 'Kaunteya ("the son of Kuntī"), Pārtha and Dhanañjaya are names of Arjuna, not persons of their own: such an entry sends you to the person it names. A plural ("the sons of Kuntī") lists the persons its singular entries name.' },
  { term: '"a name only" and "by the names both entries give"', text: 'Many names have several entries (there are several Arjunas). Where a statement does not say which one is meant, the desk takes the entry whose own words name three or more of the same persons; where it still cannot tell, the person is "a name only" and the line stops there.' },
  { term: 'What it is not, yet', text: 'A reconciled dynasty. The Purāṇas\' own genealogical chapters (the Viṣṇu\'s book IV, the Bhāgavata\'s book IX, the Harivaṃśa) are to be read verse by verse into dynasties of their own, each generation with its verse; until then a line here is one index\'s statements, each with its evidence.' },
];
