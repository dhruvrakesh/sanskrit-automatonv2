/**
 * Learn - training and quests for the working corpus - LEARN_T1_2026_10_09.
 *
 * /corpus/learn teaches invited researchers and editors to use every tool of the working corpus,
 * with quests, XP, levels and badges. The database holds the rules (docs/cloud/C11_learn_2026-10-09.sql
 * in the automaton repo): which quests there are, their XP, whether a quest is marked by hand
 * ("self") or checked live from the Researchers' Corner ("auto"), who has the editors' quests, the
 * levels and the badges. This file holds the words: each quest's title, why it matters, its steps
 * and the tool it links to; the tracks, the badges and the levels by name.
 *
 * Same contract as corner.ts: check `ok` first; `refused` is not a failure; a function the
 * database does not have yet (C11 not applied) is `missing`, and the page then shows the toolbox
 * alone and says so quietly. Every call keeps the server's own sentence (such as "Learn is open to
 * invited researchers and editors." or "No such quest: x."), which the page shows as it is.
 */
import { supabase } from '@/integrations/supabase/client';
import { functionMissing } from '@/lib/corpusMirror';
import { atHref } from '@/lib/corpusLibrary';
import type { MediaResult } from '@/lib/corpusMedia';

export const LEARN_MARK = 'LEARN_T1_2026_10_09';
export const LEARN_KEY = ['learn'] as const;
export const LEARN_HREF = '/corpus/learn';

export type LearnResult<T> = MediaResult<T>;

// ---- the rows -------------------------------------------------------------------------------

export type QuestMode = 'self' | 'auto';

/** One row of learn_me(). */
export interface QuestRow {
  quest: string; track: string; xp: number; mode: QuestMode | string; editors_only: boolean; done: boolean;
  done_at: string | null;
}

/** The one row of learn_summary(). badges: the tracks finished, in track order. */
export interface LearnSummary {
  xp: number; level: string; level_index: number; next_level: string | null; next_level_xp: number | null;
  badges: string[] | null; quests_done: number; quests_total: number;
}

/** One row of learn_team() (editors only). */
export interface TeamMember {
  user_id: string; email: string | null; roles: string[] | null; xp: number; level: string; quests_done: number;
  last_activity: string | null;
}

// ---- the words ------------------------------------------------------------------------------

export type TrackKey = 'find' | 'read' | 'ask' | 'make' | 'edit';

export interface TrackCopy { key: TrackKey; title: string; intro: string; badge: string }

export const TRACKS: TrackCopy[] = [
  { key: 'find', title: 'Find your way', badge: 'Wayfinder',
    intro: 'The Library, the reader, the two searches and the names: how to reach any passage of any text.' },
  { key: 'read', title: 'Read what the desk made', badge: 'Close reader',
    intro: 'The stories, pictures and graphic novels drawn from the texts, each tied to its passages, and the published texts.' },
  { key: 'ask', title: 'Ask the desk', badge: 'Desk hand',
    intro: 'Ask the translation desk for something new, in the Researchers\' Corner. These quests are checked for you from your own requests.' },
  { key: 'make', title: 'Make and publish', badge: 'Anthologist',
    intro: 'Gather approved stories into an anthology of your own, see it published, and print it.' },
  { key: 'edit', title: 'For editors', badge: 'Editor\'s hand',
    intro: 'The decisions only an editor (an admin or the super admin) makes. Checked for you from the Corner.' },
];

/** What the Ask track says about money, once, plainly. */
export const PAID_NOTE =
  'These quests only point you to the Corner; nothing is asked for you. A researcher\'s paid request still waits for an editor\'s approval and counts against the day\'s cap, as any other.';

export interface QuestCopy {
  title: string;
  why: string;
  steps: string[];
  href: string;
  /** The tool the link opens, for its name ("Try it in the Library"). */
  tool: string;
}

const CORNER_ASK = '/corpus/corner?tab=ask';
const ANTHOLOGIES = '/corpus/corner?tab=anthologies';

export const QUESTS: Record<string, QuestCopy> = {
  // ---- find your way
  find_library: {
    title: 'Open the Library and pick a text',
    why: 'Every text on the translation desk stands on a shelf in the Library, with how far it is translated into English and Hindi.',
    steps: ['Open the Library.', 'Look along a shelf and choose a text.', 'It opens in the reader at its first page.'],
    href: '/corpus', tool: 'the Library',
  },
  find_passage: {
    title: 'Jump straight to a passage',
    why: 'Stories, pictures and citations name a passage as the reader\'s margin does: 25.7 is scan page 25, passage 7. A link with ?at= opens the reader at it.',
    steps: [
      'Open /corpus/nilamata_seg?at=25.7 (the link below).',
      'The reader finds the page that holds scan page 25 and marks passage 25.7.',
      'Change the number after ?at= to go anywhere in a text.',
    ],
    href: atHref('nilamata_seg', '25.7'), tool: 'the reader',
  },
  find_views: {
    title: 'Read a passage in Sanskrit, IAST, English and Hindi',
    why: 'The reader always shows the Sanskrit in Devanagari. The IAST, the English and the Hindi can each be shown or hidden, beside the Sanskrit or under it.',
    steps: [
      'Open a text with Hindi, such as the Nīlamata Purāṇa.',
      'In the reading bar, tick IAST, English and Hindi.',
      'Untick Side by side to read everything in one column; tick it again to have the Sanskrit on the left on a wide screen.',
    ],
    href: '/corpus/nilamata_seg', tool: 'the reader',
  },
  find_search: {
    title: 'Search the corpus for a word',
    why: 'Word search finds a word in the English, in any form ("sacrifice" also finds "sacrificed"), and in the IAST as written, across every text.',
    steps: [
      'Open the Library.',
      'Under Search the whole corpus, keep By words.',
      'Type a word, such as Vitastā or cremation ground, and press Search.',
      'Open a result: it lands on its passage. Inside a text, Find in this text searches that text alone.',
    ],
    href: '/corpus', tool: 'the search',
  },
  find_meaning: {
    title: 'Search by meaning',
    why: 'Meaning search finds the passages closest in meaning to a question in plain English, even when they share no word with it.',
    steps: [
      'Open the Library.',
      'Under Search the whole corpus, choose By meaning.',
      'Ask a question, such as: why did the king sell his wife and son?',
      'Each result shows how close a match it is. In the reader, Similar passages in the corpus does the same for one passage.',
    ],
    href: '/corpus', tool: 'meaning search',
  },
  find_names: {
    title: 'Follow a name through its mentions',
    why: 'Names lists the people, deities, places, peoples, rivers and mountains recognised in the passages (by machine, not reviewed), and every passage that names each one.',
    steps: [
      'Open Names.',
      'Search for a name, such as Vitastā, or browse by kind.',
      'Open the name: every passage that mentions it, in reading order, each a link into its text.',
    ],
    href: '/corpus/names', tool: 'Names',
  },
  // ---- read what the desk made
  read_story: {
    title: 'Read a story and open one of its citations',
    why: 'Each story is retold in English and Hindi from the passages it cites. Every citation is a link into the text, so you can check the story against it.',
    steps: ['Open Stories and choose one.', 'Read it in English or in Hindi.', 'Open one of its citations: the reader opens at that passage.'],
    href: '/corpus/stories', tool: 'Stories',
  },
  read_picture: {
    title: 'Open a picture and go to its passage',
    why: 'Each picture is drawn for a passage and anchored to it. The pictures are generated, not historical sources.',
    steps: ['Open Pictures and choose one.', 'Under the picture, follow "read the passage" to the passage it illustrates.'],
    href: '/corpus/images', tool: 'Pictures',
  },
  read_novel: {
    title: 'Read a graphic novel',
    why: 'A graphic novel retells an approved story page by page. Each caption and each line spoken cites its passage.',
    steps: ['Open Graphic novels and choose one.', 'Read it page by page, and follow a citation to its passage.'],
    href: '/corpus/novels', tool: 'Graphic novels',
  },
  read_texts: {
    title: 'Open a published text',
    why: 'The published texts at /texts are open to every visitor, not only to signed-in readers. A text of the working corpus that is published links to its published reader.',
    steps: ['Open Published texts.', 'Choose a text and read a page.'],
    href: '/texts', tool: 'Published texts',
  },
  // ---- ask the desk (checked for you)
  ask_any: {
    title: 'Ask the desk for anything',
    why: 'The desk is a PC that carries out requests on its rounds, within its own spend cap. Any request of yours counts, whatever becomes of it.',
    steps: ['Open the Corner, at Ask the desk.', 'Choose a text and one of the requests.', 'Fill it in and press Ask the desk.'],
    href: CORNER_ASK, tool: 'the Corner',
  },
  ask_story: {
    title: 'Ask for a story from passages you choose',
    why: 'Name a run of passages (60 at most) and a working title; the desk writes a story from them, citing each passage it uses.',
    steps: [
      'In the Corner, choose a text.',
      'Under A story from passages you choose, give the first and the last passage, such as 25.2 and 25.9, and a title.',
      'Press Ask the desk.',
    ],
    href: `${CORNER_ASK}&kind=story_range`, tool: 'the Corner',
  },
  ask_done: {
    title: 'See one of your requests through',
    why: 'A request is done when the desk has carried it out. What it made comes back as a draft until an editor approves it.',
    steps: [
      'Open My requests in the Corner.',
      'Wait until one of them says done (a researcher\'s paid request is approved by an editor first).',
      'Open what it made from the links on the request.',
    ],
    href: '/corpus/corner?tab=mine', tool: 'My requests',
  },
  ask_write: {
    title: 'Ask for a proposed episode to be written',
    why: 'The desk proposes episodes worth telling that it finds in a text; one is written out in English and Hindi when someone asks for it.',
    steps: [
      'In the Corner, choose a text with proposed episodes.',
      'Under Write a proposed episode, choose one.',
      'Press Ask the desk.',
    ],
    href: `${CORNER_ASK}&kind=story_write`, tool: 'the Corner',
  },
  ask_picture: {
    title: 'Ask for a picture',
    why: 'A picture can be drawn for a passage, from your brief, or for a story that has none yet.',
    steps: [
      'In the Corner, under Pictures, choose A picture for a passage or A picture for a story.',
      'For a passage, say what the picture should show, as the passage tells it (20 characters or more).',
      'Press Ask the desk.',
    ],
    href: `${CORNER_ASK}&kind=picture_passage`, tool: 'the Corner',
  },
  ask_novel: {
    title: 'Ask for a graphic novel to be planned',
    why: 'A graphic novel is planned from an approved story: its pages, their captions and the lines spoken, each citing its passage.',
    steps: [
      'In the Corner, under Graphic novels, choose Plan a graphic novel from a story.',
      'Choose an approved story, the number of pages (8 to 16) and its readers.',
      'Press Ask the desk.',
    ],
    href: `${CORNER_ASK}&kind=novel_plan`, tool: 'the Corner',
  },
  // ---- make and publish
  make_anthology: {
    title: 'Start an anthology',
    why: 'An anthology gathers approved stories from any of the texts, in the order you choose, with a title and an introduction.',
    steps: ['Open New anthology.', 'Give it a title and add a story.', 'Save it. It stays a draft, yours alone, until an editor publishes it.'],
    href: '/corpus/anthologies/new', tool: 'New anthology',
  },
  make_three: {
    title: 'Put three stories in one anthology',
    why: 'Three stories or more make an anthology worth reading through. Checked live: the anthology must hold three now.',
    steps: ['Open one of your anthologies and choose Edit.', 'Add stories until it holds three or more, and put them in order.', 'Save it.'],
    href: ANTHOLOGIES, tool: 'the anthologies',
  },
  make_published: {
    title: 'See an anthology of yours published',
    why: 'An editor publishes an anthology once all its stories are approved; then every reader of the working corpus can read it.',
    steps: ['Make sure every story in it is approved.', 'Ask an editor to publish it: editors see your drafts.'],
    href: ANTHOLOGIES, tool: 'the anthologies',
  },
  make_print: {
    title: 'Print an anthology or save it as PDF',
    why: 'An anthology prints on its own, one story to a page, with its pictures and its citations.',
    steps: ['Open an anthology.', 'Press Print or save as PDF.', 'Print it, or choose Save as PDF in the print dialog.'],
    href: ANTHOLOGIES, tool: 'the anthologies',
  },
  // ---- for editors
  edit_decide: {
    title: 'Decide a researcher\'s request',
    why: 'A researcher\'s paid request waits for an editor. Approving it commits its estimate against the day\'s cap.',
    steps: ['Open the Queue in the Corner.', 'Read the request and its note.', 'Approve or reject it, with a note to the researcher if you like.'],
    href: '/corpus/corner?tab=queue', tool: 'the Queue',
  },
  edit_approve: {
    title: 'Ask the desk to approve a story',
    why: 'Approving a story is an editor\'s decision, carried out on the desk; the story then shows to every reader.',
    steps: ['Open a draft story in Stories.', 'In its Ask the desk bar, press Approve.', 'The desk approves it on its next round.'],
    href: '/corpus/stories', tool: 'Stories',
  },
  edit_publish: {
    title: 'Publish an anthology',
    why: 'Publishing puts an anthology in front of every reader of the working corpus.',
    steps: ['Open an anthology whose stories are all approved.', 'Press Publish.'],
    href: ANTHOLOGIES, tool: 'the anthologies',
  },
};

export interface Level { index: number; name: string; min: number }

/** As learn._levels() in C11. */
export const LEVELS: Level[] = [
  { index: 0, name: 'Reader', min: 0 },
  { index: 1, name: 'Explorer', min: 50 },
  { index: 2, name: 'Storyteller', min: 120 },
  { index: 3, name: 'Curator', min: 200 },
  { index: 4, name: 'Keeper', min: 280 },
];

export const BADGES: Record<TrackKey, string> = Object.fromEntries(TRACKS.map((t) => [t.key, t.badge])) as Record<TrackKey, string>;

// ---- the toolbox and how the desk works -----------------------------------------------------

export interface Tool { name: string; href: string; what: string }

export const TOOLBOX: Tool[] = [
  { name: 'Library', href: '/corpus', what: 'Every text of the working corpus on its shelf, with how far it is translated. Start here.' },
  { name: 'Reader', href: '/corpus/nilamata_seg', what: 'One text, passage by passage: the Sanskrit, the IAST, the English and the Hindi. ?at=25.7 opens it at a passage.' },
  { name: 'Search', href: '/corpus', what: 'By words in the English and the IAST, or by meaning in plain English, across every text; Find in this text inside one.' },
  { name: 'Names', href: '/corpus/names', what: 'The people, deities, places and rivers named in the passages, and where each is named.' },
  { name: 'Stories', href: '/corpus/stories', what: 'Episodes retold in English and Hindi from the passages they cite, each citation a link.' },
  { name: 'Pictures', href: '/corpus/images', what: 'Illustrations drawn for passages, each linked to the passage it shows. Generated, not historical.' },
  { name: 'Graphic novels', href: '/corpus/novels', what: 'Approved stories told page by page, every caption citing its passage.' },
  { name: 'Published texts', href: '/texts', what: 'The texts published to every visitor, outside the working corpus.' },
  { name: 'Researchers\' Corner', href: '/corpus/corner', what: 'Ask the desk for stories, pictures and graphic novels, and follow your requests.' },
  { name: 'Anthologies', href: ANTHOLOGIES, what: 'Approved stories gathered in an order you choose; published by an editor; printed or saved as PDF.' },
];

export interface DeskStep { title: string; text: string }

export const DESK_STEPS: DeskStep[] = [
  { title: 'You ask', text: 'In the Researchers\' Corner, choose a text and what you would like: a story, a picture, a graphic novel. The form shows what it is estimated to cost.' },
  { title: 'An editor approves', text: 'A researcher\'s paid request waits for an editor (an admin or the super admin), who approves or rejects it. Each approved request counts against the day\'s cap.' },
  { title: 'The desk takes it', text: 'The desk is a PC that comes for approved requests on its next round, about every 10 minutes while it is on, and carries them out with its own scripts.' },
  { title: 'Results arrive as drafts', text: 'What the desk made comes back as a draft, checked against its citations, until an editor approves it. Follow it in My requests.' },
];

// ---- calls ----------------------------------------------------------------------------------

const TIMEOUT_MS = 15000;
const REFUSED_RE = /signed-in readers only|permission denied|not allowed|42501/i;
/** The corpus's own gate (C5/C7), as opposed to Learn's (invited researchers and editors). */
const CORPUS_GATE_RE = /signed-in readers only|permission denied/i;

const failed = <T,>(error: string, refused = false): LearnResult<T> => ({ ok: false, rows: [], error, refused, missing: false });

type RpcAnswer = { data: unknown; error: { message?: string; code?: string } | null };
type Timeout = { __timeout: true };
/** The generated types do not list C11's functions; this is the one untyped door to them. */
const db = supabase as unknown as { rpc: (fn: string, args: Record<string, unknown>) => PromiseLike<RpcAnswer> };

/** One call: its rows (a scalar answer becomes one row), or the server's own sentence. */
async function call<T>(fn: string, args: Record<string, unknown>, scalar = false): Promise<LearnResult<T>> {
  let res: RpcAnswer | Timeout | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    res = await Promise.race<RpcAnswer | Timeout>([
      db.rpc(fn, args),
      new Promise<Timeout>((resolve) => { timer = setTimeout(() => resolve({ __timeout: true }), TIMEOUT_MS); }),
    ]);
  } catch (e) {
    return failed<T>(e instanceof Error && e.message ? e.message : 'The working corpus could not be reached.');
  } finally {
    clearTimeout(timer);
  }
  if (!res) return failed<T>('The working corpus answered in an unexpected form.');
  if ('__timeout' in res) return failed<T>('The working corpus took too long to answer. Please try again.');
  if (res.error) {
    const msg = String(res.error.message ?? res.error);
    const refused = res.error.code === '42501' || REFUSED_RE.test(msg);
    const r = failed<T>(msg || 'The request failed.', refused);
    return { ...r, missing: functionMissing(r, fn) };
  }
  if (scalar) return { ok: true, rows: res.data == null ? [] : [res.data as T], error: null, refused: false, missing: false };
  if (!Array.isArray(res.data)) return failed<T>('The working corpus answered in an unexpected form.');
  return { ok: true, rows: res.data as T[], error: null, refused: false, missing: false };
}

export function loadQuests(): Promise<LearnResult<QuestRow>> {
  return call<QuestRow>('learn_me', {});
}

export function loadSummary(): Promise<LearnResult<LearnSummary>> {
  return call<LearnSummary>('learn_summary', {});
}

/** "I did this". true: marked now; false: it was marked already (the first time is kept). */
export function markQuest(quest: string): Promise<LearnResult<boolean>> {
  return call<boolean>('learn_mark', { p_quest: quest }, true);
}

export function loadTeam(): Promise<LearnResult<TeamMember>> {
  return call<TeamMember>('learn_team', {});
}

/** Refused by the corpus itself (not a reader), rather than by Learn (a reader, not invited). */
export function refusedByCorpus(r: Pick<LearnResult<unknown>, 'refused' | 'error'>): boolean {
  return r.refused && CORPUS_GATE_RE.test(r.error ?? '');
}

// ---- the rules the page uses ----------------------------------------------------------------

const n = (v: unknown): number => {
  const x = typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN;
  return Number.isFinite(x) ? x : 0;
};

export function isQuestRow(x: unknown): x is QuestRow {
  return !!x && typeof x === 'object' && typeof (x as QuestRow).quest === 'string' && typeof (x as QuestRow).track === 'string';
}

export interface Quest extends QuestRow { copy: QuestCopy }

/** A quest with its words; one the site does not know yet gets plain ones. */
export function withCopy(row: QuestRow): Quest {
  const copy = QUESTS[row.quest] ?? { title: row.quest.replace(/_/g, ' '), why: '', steps: [], href: LEARN_HREF, tool: 'the working corpus' };
  return { ...row, xp: n(row.xp), done: !!row.done, copy };
}

export interface TrackGroup {
  key: string; title: string; intro: string; badge: string; quests: Quest[];
  done: number; total: number; xp: number; xpDone: number; complete: boolean;
}

/** Done, of how many, and the XP, for a list of quests. */
export function trackProgress(quests: Pick<QuestRow, 'done' | 'xp'>[]): { done: number; total: number; xp: number; xpDone: number; complete: boolean } {
  const done = quests.filter((q) => q.done).length;
  const xp = quests.reduce((a, q) => a + n(q.xp), 0);
  const xpDone = quests.reduce((a, q) => a + (q.done ? n(q.xp) : 0), 0);
  return { done, total: quests.length, xp, xpDone, complete: quests.length > 0 && done === quests.length };
}

/** The tracks in their order, each with its quests in the database's order; a track with no quest
 *  for this person (the editors' one, for a researcher) is left out. */
export function groupByTrack(rows: unknown[]): TrackGroup[] {
  const quests = rows.filter(isQuestRow).map(withCopy);
  const known = TRACKS.map((t) => t.key as string);
  const keys = [...known, ...[...new Set(quests.map((q) => q.track))].filter((k) => !known.includes(k))];
  return keys
    .map((key) => {
      const t = TRACKS.find((x) => x.key === key);
      const qs = quests.filter((q) => q.track === key);
      return { key, title: t?.title ?? key, intro: t?.intro ?? '', badge: t?.badge ?? key, quests: qs, ...trackProgress(qs) };
    })
    .filter((g) => g.quests.length > 0);
}

/** The first quest not yet done, in track order; null when every one is done. */
export function nextQuest(rows: unknown[]): Quest | null {
  for (const g of groupByTrack(rows)) {
    const q = g.quests.find((x) => !x.done);
    if (q) return q;
  }
  return null;
}

export function levelFor(xp: number): { level: Level; next: Level | null } {
  const v = n(xp);
  let level = LEVELS[0];
  for (const l of LEVELS) if (v >= l.min) level = l;
  return { level, next: LEVELS.find((l) => l.min > v) ?? null };
}

/** The summary as learn_summary() makes it, from learn_me()'s rows (when the summary is not to hand). */
export function summarize(rows: unknown[]): LearnSummary {
  const groups = groupByTrack(rows);
  const all = groups.flatMap((g) => g.quests);
  const p = trackProgress(all);
  const { level, next } = levelFor(p.xpDone);
  return {
    xp: p.xpDone, level: level.name, level_index: level.index, next_level: next?.name ?? null, next_level_xp: next?.min ?? null,
    badges: groups.filter((g) => g.complete).map((g) => g.key), quests_done: p.done, quests_total: p.total,
  };
}

/** Where the XP bar stands: from the start of this level to the next (full at the top level). */
export function levelProgress(s: Pick<LearnSummary, 'xp' | 'next_level_xp'>): { min: number; max: number; now: number; pct: number; toNext: number | null } {
  const xp = n(s.xp);
  const { level } = levelFor(xp);
  const nextAt = s.next_level_xp == null ? null : n(s.next_level_xp);
  if (nextAt == null || nextAt <= xp) return { min: level.min, max: Math.max(level.min, xp), now: xp, pct: 100, toNext: null };
  const span = Math.max(1, nextAt - level.min);
  return { min: level.min, max: nextAt, now: xp, pct: Math.round((100 * Math.max(0, xp - level.min)) / span), toNext: nextAt - xp };
}

/** The badge for a track ("Wayfinder"), or the track's key for one the site does not know. */
export function badgeName(track: string): string {
  return (BADGES as Record<string, string>)[track] ?? track;
}

/** "9 Oct 2026", or '' for none. */
export function doneDate(ts: string | null | undefined): string {
  if (!ts) return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '';
  try {
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

const ROLE_LABELS: Record<string, string> = { super_admin: 'super admin', admin: 'admin', researcher: 'researcher' };

export function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role.replace(/_/g, ' ');
}

/** The quest as done now, for the page to show at once while learn_me() is read again. */
export function markedDone(rows: QuestRow[] | undefined, quest: string, now: string = new Date().toISOString()): QuestRow[] | undefined {
  if (!rows) return rows;
  return rows.map((r) => (r.quest === quest && !r.done ? { ...r, done: true, done_at: now } : r));
}
