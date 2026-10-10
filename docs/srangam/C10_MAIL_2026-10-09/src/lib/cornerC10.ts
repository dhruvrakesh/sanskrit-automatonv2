/**
 * The Corner level with the desk - CORNER_C10_MAIL_2026_10_09.
 *
 * The rules of the edit forms (DeskEdit.tsx: a story, a picture's words, a novel's page) and the
 * reads of the Corner's new panels (CornerPanels.tsx: the ideas for pictures the desk proposed, and
 * for editors the retired pictures). The database checks every request again
 * (docs/cloud/C10b_corner_kinds_2026-10-09.sql, corner._clean) and the desk checks it once more
 * before it acts; these rules only spare a round trip and say the same thing first. Only the forms
 * and the panels import this file, each loaded when it is first used.
 */
import { lib, s, type CornerResult } from '@/lib/corner';

// ---- the edit forms -------------------------------------------------------------------------

export type EditKind = 'story_edit' | 'picture_edit' | 'novel_page_edit';

export interface FieldRule {
  key: string; label: string; min: number; max: number;
  /** A text box of this many rows, else one line. */
  rows?: number; lang?: 'hi'; editorOnly?: boolean;
}

/** The bounds of corner._clean (C10b), field by field. */
export const STORY_FIELDS: readonly FieldRule[] = [
  { key: 'title', label: 'Title', min: 3, max: 300 },
  { key: 'title_hi', label: 'Title in Hindi', min: 0, max: 300, lang: 'hi' },
  { key: 'story_en', label: 'The story in English', min: 20, max: 6000, rows: 10 },
  { key: 'story_hi', label: 'The story in Hindi', min: 0, max: 8000, rows: 10, lang: 'hi' },
];
export const PICTURE_FIELDS: readonly FieldRule[] = [
  { key: 'title', label: 'Title', min: 3, max: 200 },
  { key: 'caption_en', label: 'Caption in English', min: 0, max: 500, rows: 2 },
  { key: 'caption_hi', label: 'Caption in Hindi', min: 0, max: 500, rows: 2, lang: 'hi' },
  { key: 'context_note', label: 'A note on what it shows', min: 0, max: 1000, rows: 3 },
  { key: 'license', label: 'Licence', min: 0, max: 200, editorOnly: true },
];
export const PAGE_FIELDS: readonly FieldRule[] = [
  { key: 'scene', label: 'The scene the artist is asked for', min: 10, max: 2000, rows: 4 },
  { key: 'caption', label: 'Caption in English', min: 0, max: 2000, rows: 3 },
  { key: 'caption_hi', label: 'Caption in Hindi', min: 0, max: 2000, rows: 3, lang: 'hi' },
];

const GONE = new Set(['retired', 'rejected']);

/** May this viewer edit an item in this status: never a retired one, and an approved one only as an
 *  editor (corner._clean refuses a researcher's edit of an approved story, picture or novel). */
export function mayEdit(status: string | null | undefined, editor: boolean): boolean {
  if (GONE.has(status ?? '')) return false;
  return status !== 'approved' || editor;
}

/** The fields this viewer may change: a proposed episode only its titles (it is not written yet);
 *  a picture's licence only an editor. */
export function editFields(kind: EditKind, status: string | null | undefined, editor: boolean): FieldRule[] {
  if (kind === 'story_edit') return STORY_FIELDS.filter((f) => status !== 'candidate' || f.key === 'title' || f.key === 'title_hi');
  if (kind === 'picture_edit') return PICTURE_FIELDS.filter((f) => !f.editorOnly || editor);
  return [...PAGE_FIELDS];
}

/** Only what changed, trimmed (as the database trims it). An emptied field is sent as '' (the
 *  database clears it) where it may be empty. */
export function changedFields(
  rules: readonly FieldRule[], before: Record<string, unknown>, after: Record<string, string | undefined>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const f of rules) {
    const now = after[f.key];
    if (now === undefined) continue;
    const v = now.trim();
    if (v !== s(before[f.key])) out[f.key] = v;
  }
  return out;
}

/** "Title: 3 to 300 characters", in the database's own words, or null when it is fine. */
export function fieldProblem(rule: FieldRule, value: string): string | null {
  const n = value.trim().length;
  return n < rule.min || n > rule.max ? `${rule.label}: ${rule.min} to ${rule.max} characters` : null;
}

// ---- the ideas for pictures -----------------------------------------------------------------

export interface Idea { image_id: number; kind: string | null; title: string | null; brief: string | null; at: string | null }

/** An idea as corner_ideas() answers it: whether it is drawn, and the newest request to draw it. */
export interface IdeaRow extends Idea {
  request_id: number | null; asked_at: string | null; drawn: boolean; draw_request_id: number | null; draw_status: string | null;
}

export interface RetiredPicture {
  image_id: number; kind: string | null; title: string | null; caption_en: string | null; retired_at: string | null; has_file: boolean;
}

const intOf = (v: unknown): number | null => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && /^\d{1,10}$/.test(v.trim()) ? Number(v) : NaN;
  return Number.isInteger(n) && n > 0 ? n : null;
};
const textOf = (v: unknown, n: number): string | null => (typeof v === 'string' && v.trim() ? v.trim().slice(0, n) : null);
const atOf = (v: unknown): string | null => {
  const t = typeof v === 'string' ? v.trim() : '';
  return /^\d{1,6}\.\d{1,6}$/.test(t) ? t : null;
};

function idea(x: unknown): Idea | null {
  if (!x || typeof x !== 'object' || Array.isArray(x)) return null;
  const r = x as Record<string, unknown>;
  const id = intOf(r.image_id);
  if (id == null) return null;
  return { image_id: id, kind: textOf(r.kind, 40), title: textOf(r.title, 300), brief: textOf(r.brief, 2000), at: atOf(r.at) };
}

/** The ideas of a picture_ideas or picture_cover result ({"ideas": [...], "count"}), read
 *  defensively (a JSON object, or its text); at most 50. */
export function parseIdeas(result: unknown): Idea[] {
  let v: unknown = result;
  if (typeof result === 'string') {
    try { v = JSON.parse(result); } catch { v = null; }
  }
  const list = v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>).ideas : null;
  if (!Array.isArray(list)) return [];
  const seen = new Set<number>();
  const out: Idea[] = [];
  for (const x of list.slice(0, 50)) {
    const i = idea(x);
    if (i && !seen.has(i.image_id)) { seen.add(i.image_id); out.push(i); }
  }
  return out;
}

export function ideaRow(x: unknown): IdeaRow | null {
  const i = idea(x);
  if (!i) return null;
  const r = x as Record<string, unknown>;
  return {
    ...i, request_id: intOf(r.request_id), asked_at: textOf(r.asked_at, 40), drawn: r.drawn === true,
    draw_request_id: intOf(r.draw_request_id), draw_status: textOf(r.draw_status, 40),
  };
}

export function retiredRow(x: unknown): RetiredPicture | null {
  if (!x || typeof x !== 'object' || Array.isArray(x)) return null;
  const r = x as Record<string, unknown>;
  const id = intOf(r.image_id);
  if (id == null) return null;
  return {
    image_id: id, kind: textOf(r.kind, 40), title: textOf(r.title, 300), caption_en: textOf(r.caption_en, 500),
    retired_at: textOf(r.retired_at, 40), has_file: r.has_file === true,
  };
}

export const IDEAS_KEY = (doc: string) => ['corner', 'ideas', doc] as const;
export const RETIRED_KEY = (doc: string) => ['corner', 'retired', doc] as const;

export function loadIdeas(doc: string): Promise<CornerResult<IdeaRow>> {
  return lib<IdeaRow>('corner_ideas', { p_doc: doc });
}

export function loadRetired(doc: string): Promise<CornerResult<RetiredPicture>> {
  return lib<RetiredPicture>('corner_retired_pictures', { p_doc: doc });
}

/** Where an idea stands: drawn (its picture is on the site), asked to be drawn (and how that
 *  stands), or waiting to be drawn. A finished drawing whose picture is not on the site yet is
 *  'synced' (it comes with the desk's next sync). */
export type IdeaState = 'drawn' | 'asked' | 'synced' | 'waiting';

const ASKED = new Set(['pending', 'approved', 'claimed', 'running']);

export function ideaState(r: Pick<IdeaRow, 'drawn' | 'draw_status'> | null | undefined): IdeaState {
  if (r?.drawn) return 'drawn';
  if (r?.draw_status && ASKED.has(r.draw_status)) return 'asked';
  if (r?.draw_status === 'done') return 'synced';
  return 'waiting';
}
