/**
 * The Corner's guide - CORNER_UX_U1_2026_10_10.
 *
 * Ask the desk is guided, never pushed: the page leads with the choices that matter (a text, then
 * what to make), shows what is ready to be made in the chosen text, and lets a researcher choose
 * passages from the text itself instead of typing their numbers. Nothing here asks the desk for
 * anything: every suggestion only fills a form, and the request is still made by its own "Ask the
 * desk" button, at the price it shows.
 *
 * The rules are here, pure, so they are tested on their own; the parts that show them are
 * src/components/corpus/CornerGuide.tsx and PassagePicker.tsx (loaded when first opened). The
 * numbers come from what the Corner already loads (corpus_reader_docs, the text's stories, pictures
 * and graphic novels) and, where the database has it (docs/cloud/C13 in the automaton repo), from
 * corner_offering(): the working corpus so far, for the strip at the top. Before C13 the strip is
 * made from the texts alone.
 */
import { bookTitle, type StoryRow } from '@/lib/corpusLibrary';
import { callMirror, functionMissing, type MirrorDoc } from '@/lib/corpusMirror';
import type { MediaResult, MediaRow, NovelRow } from '@/lib/corpusMedia';

export const GUIDE_MARK = 'CORNER_UX_U1_2026_10_10';

// ---- what to make ---------------------------------------------------------------------------

export type Goal = 'story' | 'picture' | 'novel' | 'all';

export interface GoalCopy { key: Goal; label: string; what: string }

export const GOALS: readonly GoalCopy[] = [
  { key: 'story', label: 'A story', what: 'An episode retold in English and Hindi, every line citing its passage' },
  { key: 'picture', label: 'A picture', what: 'A drawing for a passage or a story, or ideas for pictures' },
  { key: 'novel', label: 'A graphic novel', what: 'An approved story told again, page by page' },
  { key: 'all', label: 'Everything', what: 'Every request the desk takes for this text' },
];

const GOAL_OF: Record<string, Goal> = {
  story_range: 'story', story_write: 'story', story_mine: 'story',
  picture_passage: 'picture', story_illustrate: 'picture', picture_redraw: 'picture', picture_ideas: 'picture',
  picture_cover: 'picture', picture_draw: 'picture',
  novel_plan: 'novel', novel_cast: 'novel', novel_draw: 'novel',
};

/** The goal a request belongs to on Ask the desk, or null for one asked elsewhere. */
export function goalOf(kind: string | null | undefined): Goal | null {
  return (kind && GOAL_OF[kind]) || null;
}

export function parseGoal(v: string | null | undefined): Goal | null {
  return v === 'story' || v === 'picture' || v === 'novel' || v === 'all' ? v : null;
}

/** Is this section shown for this goal? */
export const shows = (goal: Goal, section: Exclude<Goal, 'all'>): boolean => goal === 'all' || goal === section;

// ---- the texts ------------------------------------------------------------------------------

export interface TextLine {
  doc_code: string; label: string; passages: number; english: number; hindi: number; stories: number;
  /** English to work from, and no story or proposed episode yet. */
  untold: boolean;
}

const count = (v: unknown): number => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
};

/** The texts the desk can work from (some English), by title, as the Corner's list shows them. */
export function translatedTexts(rows: readonly unknown[] | null | undefined): TextLine[] {
  const out: TextLine[] = [];
  for (const x of rows ?? []) {
    const d = x as MirrorDoc;
    if (!d || typeof d.doc_code !== 'string' || !d.doc_code || count(d.english) <= 0) continue;
    const stories = count(d.stories);
    out.push({
      doc_code: d.doc_code, label: bookTitle(d).title, passages: count(d.passages), english: count(d.english),
      hindi: count(d.hindi), stories, untold: stories === 0,
    });
  }
  return out.sort((a, b) => a.label.localeCompare(b.label));
}

/** Where to begin: texts with English and no story yet, the most English first. */
export function untoldTexts(texts: readonly TextLine[], n = 6): TextLine[] {
  return texts.filter((t) => t.untold).sort((a, b) => b.english - a.english || a.label.localeCompare(b.label)).slice(0, n);
}

/** "Surprise me": a text waiting for its first story (else any text), never the one already chosen. */
export function surpriseText(texts: readonly TextLine[], not?: string | null, rnd: () => number = Math.random): TextLine | null {
  const pool = (texts.some((t) => t.untold && t.doc_code !== not) ? texts.filter((t) => t.untold) : texts)
    .filter((t) => t.doc_code !== not);
  if (!pool.length) return null;
  const i = Math.min(pool.length - 1, Math.max(0, Math.floor(rnd() * pool.length)));
  return pool[i];
}

const plural = (n: number, one: string, many = `${one}s`): string => `${n.toLocaleString('en-IN')} ${n === 1 ? one : many}`;

// ---- the offering so far --------------------------------------------------------------------

/** One row of corner_offering() (C13). */
export interface Offering {
  texts: number; passages_en: number; stories_approved: number; stories_draft: number; stories_proposed: number;
  pictures: number; novels: number; anthologies: number; untold: number; done_all: number; done_7d: number;
}

const OFFERING_KEYS: (keyof Offering)[] = [
  'texts', 'passages_en', 'stories_approved', 'stories_draft', 'stories_proposed', 'pictures', 'novels', 'anthologies',
  'untold', 'done_all', 'done_7d',
];

export function parseOffering(x: unknown): Offering | null {
  if (!x || typeof x !== 'object') return null;
  const r = x as Record<string, unknown>;
  if (!OFFERING_KEYS.every((k) => k in r)) return null;
  return Object.fromEntries(OFFERING_KEYS.map((k) => [k, count(r[k])])) as unknown as Offering;
}

export const OFFERING_KEY = ['corner', 'offering'] as const;

/** corner_offering(), or null data while the database does not have it (before C13) or refuses it. */
export async function loadOffering(): Promise<MediaResult<Offering>> {
  const r = await callMirror<unknown>('corner_offering', {});
  const rows = r.ok ? r.rows.map(parseOffering).filter((o): o is Offering => !!o) : [];
  return { ...r, rows, missing: functionMissing(r, 'corner_offering') };
}

/** The strip's parts: from corner_offering() when there is one, else from the texts alone. */
export function offeringParts(o: Offering | null, texts: readonly TextLine[]): string[] {
  if (o) {
    const parts = [
      plural(o.texts, 'text') + ' in English',
      plural(o.passages_en, 'passage') + ' translated',
      plural(o.stories_approved, 'story', 'stories') + ' told',
    ];
    if (o.pictures) parts.push(plural(o.pictures, 'picture'));
    if (o.novels) parts.push(plural(o.novels, 'graphic novel'));
    if (o.anthologies) parts.push(plural(o.anthologies, 'anthology', 'anthologies') + ' published');
    if (o.done_7d) parts.push(`${plural(o.done_7d, 'request')} done this week`);
    return parts;
  }
  if (!texts.length) return [];
  const english = texts.reduce((a, t) => a + t.english, 0);
  return [plural(texts.length, 'text') + ' in English', plural(english, 'passage') + ' translated'];
}

/** "17 texts are waiting for their first story", or null when none is. Counted from the texts, as the
 *  list and "Where to begin" count them, so the three always agree. */
export function untoldLine(texts: readonly TextLine[]): string | null {
  const n = texts.filter((t) => t.untold).length;
  if (!n) return null;
  return n === 1 ? '1 text is waiting for its first story' : `${n.toLocaleString('en-IN')} texts are waiting for their first story`;
}

// ---- one text -------------------------------------------------------------------------------

export interface TextState { approved: number; drafts: number; proposed: number; pictures: number; novels: number }

const liveStory = (s: StoryRow): boolean => s.status !== 'retired' && s.status !== 'rejected';

/** What the chosen text has, as far as this viewer sees it. */
export function textState(stories: readonly StoryRow[], pics: readonly MediaRow[], novels: readonly NovelRow[]): TextState {
  const live = stories.filter(liveStory);
  return {
    approved: live.filter((s) => s.status === 'approved').length,
    drafts: live.filter((s) => s.status === 'draft').length,
    proposed: live.filter((s) => s.status === 'candidate').length,
    pictures: pics.filter((p) => p.status !== 'retired').length,
    novels: novels.filter((n) => n.status !== 'retired').length,
  };
}

/** "3 stories (1 approved, 1 draft, 1 proposed) · 2 pictures · 1 graphic novel". */
export function textStateLine(s: TextState): string {
  const stories = s.approved + s.drafts + s.proposed;
  const bits: string[] = [];
  if (s.approved) bits.push(`${s.approved} approved`);
  if (s.drafts) bits.push(`${s.drafts} ${s.drafts === 1 ? 'draft' : 'drafts'}`);
  if (s.proposed) bits.push(`${s.proposed} proposed`);
  let head = 'No story yet';
  if (stories && s.approved === stories) head = plural(stories, 'approved story', 'approved stories');
  else if (stories) head = `${plural(stories, 'story', 'stories')} (${bits.join(', ')})`;
  return [head, plural(s.pictures, 'picture'), plural(s.novels, 'graphic novel')].join(' · ');
}

// ---- ready in this text ---------------------------------------------------------------------

export interface Suggestion {
  /** Unique on the page. */
  key: string;
  kind: string;
  goal: Exclude<Goal, 'all'>;
  title: string;
  why: string;
  /** What it puts in the form (story_id, ...); nothing for a request with no choice to make. */
  fill: Record<string, string>;
}

const named = (s: Pick<StoryRow, 'title' | 'story_id'>): string => `"${(s.title || `Story ${s.story_id}`).trim()}"`;

/** What is ready to be asked for in the chosen text, from what the Corner has loaded, the first step of
 *  the work first (at most two of a kind). Each is offered only when this viewer may ask for its kind.
 *  `textStories` is the text's own count of stories of any status (corpus_reader_docs): "find its
 *  episodes" is offered only when it has none at all. `seesDrafts`: this viewer is shown the drafts and
 *  the work in progress (an editor; or a researcher once the database has C13). Without them, "no
 *  picture" or "no graphic novel" may only mean "none approved yet", so those are not offered. */
export function readyNow(o: {
  stories: readonly StoryRow[]; pics: readonly MediaRow[]; novels: readonly NovelRow[];
  usable: (kind: string) => boolean; seesDrafts: boolean; textStories: number; max?: number;
}): Suggestion[] {
  const max = o.max ?? 8;
  const live = o.stories.filter(liveStory);
  const out: Suggestion[] = [];
  const byId = (a: StoryRow, b: StoryRow) => a.story_id - b.story_id;
  if (!live.length && o.textStories <= 0 && o.usable('story_mine')) {
    out.push({
      key: 'story_mine', kind: 'story_mine', goal: 'story', title: 'Find the episodes worth telling',
      why: 'No story has been drawn from this text yet. The desk reads it and proposes episodes; each can then be written.',
      fill: {},
    });
  }
  if (o.usable('story_write')) {
    for (const s of live.filter((x) => x.status === 'candidate').sort(byId).slice(0, 2)) {
      out.push({
        key: `story_write:${s.story_id}`, kind: 'story_write', goal: 'story', title: `Write ${named(s)}`,
        why: 'A proposed episode: the desk writes it out in English and Hindi from the passages it cites.',
        fill: { story_id: String(s.story_id) },
      });
    }
  }
  if (o.seesDrafts && o.usable('story_illustrate')) {
    const drawn = new Set(o.pics.filter((p) => p.status !== 'retired' && p.story_id != null).map((p) => p.story_id));
    const bare = live.filter((x) => (x.status === 'approved' || x.status === 'draft') && !drawn.has(x.story_id))
      .sort((a, b) => Number(b.status === 'approved') - Number(a.status === 'approved') || byId(a, b));
    for (const s of bare.slice(0, 2)) {
      out.push({
        key: `story_illustrate:${s.story_id}`, kind: 'story_illustrate', goal: 'picture', title: `A picture for ${named(s)}`,
        why: s.status === 'approved' ? 'An approved story with no picture yet.' : 'A draft story with no picture yet.',
        fill: { story_id: String(s.story_id) },
      });
    }
  }
  if (o.seesDrafts && o.usable('novel_plan')) {
    const told = new Set(o.novels.filter((n) => n.status !== 'retired' && n.story_id != null).map((n) => n.story_id));
    const s = live.filter((x) => x.status === 'approved' && !told.has(x.story_id)).sort(byId)[0];
    if (s) {
      out.push({
        key: `novel_plan:${s.story_id}`, kind: 'novel_plan', goal: 'novel', title: `A graphic novel of ${named(s)}`,
        why: 'An approved story that has no graphic novel yet: the desk plans its pages first.',
        fill: { story_id: String(s.story_id) },
      });
    }
  }
  if (o.seesDrafts && !o.pics.length && o.usable('picture_ideas')) {
    out.push({
      key: 'picture_ideas', kind: 'picture_ideas', goal: 'picture', title: 'Ideas for its first pictures',
      why: 'No picture has been drawn for this text yet. The desk proposes some; nothing is drawn until you ask.',
      fill: {},
    });
  }
  return out.slice(0, max);
}

/** How many suggestions each goal has. */
export function goalCounts(list: readonly Suggestion[]): Record<Exclude<Goal, 'all'>, number> {
  const c = { story: 0, picture: 0, novel: 0 };
  for (const s of list) c[s.goal] += 1;
  return c;
}

// ---- choosing passages ----------------------------------------------------------------------

/** The most passages a story is drawn from (corner._clean, C9). */
export const RANGE_MAX = 60;

export interface Picked { ref: string; ord: number }

/** What a range chosen in the text says, before the desk is asked: its length, or what is wrong. */
export function rangeNote(from: Picked | null, to: Picked | null): { ok: boolean; text: string } | null {
  if (!from || !to) return null;
  if (to.ord < from.ord) return { ok: false, text: 'The last passage comes before the first.' };
  const n = to.ord - from.ord + 1;
  if (n > RANGE_MAX) return { ok: false, text: `${n} passages: a story is drawn from ${RANGE_MAX} at most.` };
  return { ok: true, text: n === 1 ? '1 passage.' : `${n} passages.` };
}

/** A passage's first words for the picker ("The king said ..."), at most n characters. */
export function firstWords(text: string | null | undefined, n = 180): string {
  const t = (text ?? '').replace(/\s+/g, ' ').trim();
  if (t.length <= n) return t;
  const cut = t.slice(0, n);
  const sp = cut.lastIndexOf(' ');
  return `${(sp > n * 0.6 ? cut.slice(0, sp) : cut).trimEnd()}...`;
}

/** A brief for a picture of a passage, started from its English (the researcher changes it). */
export function briefFrom(english: string | null | undefined): string {
  const t = (english ?? '').replace(/\s+/g, ' ').trim();
  return t ? firstWords(t, 600) : '';
}

// ---- remembered in this browser -------------------------------------------------------------

const LAST_DOC = 'srangam.corner.lastDoc';
const DOC_RE = /^[A-Za-z0-9_.-]{1,120}$/;

/** The text chosen last time on this browser, if any (never throws). */
export function recallDoc(): string | null {
  try {
    const v = window.localStorage.getItem(LAST_DOC);
    return v && DOC_RE.test(v) ? v : null;
  } catch {
    return null;
  }
}

export function rememberDoc(code: string): void {
  try {
    if (code && DOC_RE.test(code)) window.localStorage.setItem(LAST_DOC, code);
  } catch {
    /* a private window: nothing is remembered */
  }
}
