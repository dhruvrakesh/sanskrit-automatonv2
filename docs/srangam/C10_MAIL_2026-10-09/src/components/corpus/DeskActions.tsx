/**
 * Ask the desk from where one is reading - CORNER_C9_2026_10_09.
 *
 * A compact bar under a story, a picture or a graphic novel, shown only to those who may ask the
 * desk (corner_me().can_request: invited researchers and editors); for everyone else it is nothing
 * at all, so the pages read exactly as before. Each button makes one request
 * (corner_request_create) and says what the server answered; the editors' decisions (approve,
 * retire) are requests too, carried out on the desk. Retiring asks for a second click.
 *
 * CORNER_C10_MAIL_2026_10_09: Edit (a story, a picture's words, a novel's page; never an approved one
 * for a researcher), Check again (a story against its citations), and a novel's cast or every page
 * drawn again (a second click, with the estimate). The edit forms are DeskEdit.tsx, loaded only when
 * Edit is clicked, and prefilled from what the page already shows (the target's values); only what
 * changed is sent. These kinds appear only once corner_kinds() lists them (C10b). After every request
 * the Corner's waiting emails are sent (cornerMail.flushMail).
 */
import { lazy, Suspense, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, NotebookPen } from 'lucide-react';
import { ActionNote } from '@/components/corpus/CornerParts';
import {
  aboutUsd, CORNER_KEY, createRequest, estimateFor, imageIdOf, kindUsable, loadKinds, loadMe, type CornerKind,
} from '@/lib/corner';
import type { EditKind } from '@/lib/cornerC10';
import { isMedia, loadMedia } from '@/lib/corpusMedia';

const DeskEdit = lazy(() => import('@/components/corpus/DeskEdit'));
/** The Corner's waiting emails, sent after a request (cornerMail.flushMail): loaded only then, so
 *  the reading pages do not carry the email code. Fire and forget; it never fails the bar. */
const flushMail = (): void => { void import('@/lib/cornerMail').then((x) => x.flushMail()).catch(() => undefined); };

/** What the desk is asked about, with (optionally) what the page shows of it now: the edit forms
 *  start from these values. */
export type DeskTarget =
  | {
    type: 'story'; doc_code: string; story_id: number; status: string | null;
    title?: string | null; title_hi?: string | null; story_en?: string | null; story_hi?: string | null;
  }
  | {
    type: 'picture'; doc_code: string; image_id?: number | null; media_key?: string | null; status: string | null;
    title?: string | null; caption_en?: string | null; caption_hi?: string | null; context_note?: string | null; license?: string | null;
  }
  | {
    type: 'novel'; doc_code: string; novel_id: number; status: string | null; pages?: number | null; page?: number; page_status?: string | null;
    scene?: string | null; caption?: string | null; caption_hi?: string | null;
    /** How many cast sheets and pages have a picture (the whole novel's bar): "again" only then. */
    drawn?: { cast: number; pages: number } | null;
  };

interface Action {
  id: string;
  kind: string;
  label: string;
  params: Record<string, unknown>;
  confirm?: string;
  /** Opens the edit form instead of asking at once. */
  edit?: boolean;
}

const GONE = new Set(['retired', 'rejected']);
const act = (kind: string, label: string, params: Record<string, unknown>, more: Partial<Action> = {}): Action =>
  ({ id: `${kind}:${label}`, kind, label, params, ...more });

function actionsFor(t: DeskTarget, editor: boolean, hasPicture: boolean): Action[] {
  const out: Action[] = [];
  if (GONE.has(t.status ?? '')) return out;
  // a researcher never edits an approved story, picture or novel (nor an approved page)
  const mayEdit = (status: string | null | undefined) => editor || status !== 'approved';
  if (t.type === 'story') {
    const p = { story_id: t.story_id };
    if (t.status === 'candidate') out.push(act('story_write', 'Write it', p));
    if (!hasPicture) out.push(act('story_illustrate', 'Illustrate', p));
    if (mayEdit(t.status)) out.push(act('story_edit', 'Edit', p, { edit: true }));
    if (t.status === 'draft' || t.status === 'approved') out.push(act('story_verify', 'Check again', p));
    if (editor && t.status === 'draft') out.push(act('story_approve', 'Approve', p));
    if (editor) out.push(act('story_retire', 'Retire', p, { confirm: 'Click again to retire the story' }));
  } else if (t.type === 'picture') {
    const id = t.image_id ?? imageIdOf(t.media_key);
    if (id == null) return out;
    const p = { image_id: id };
    out.push(act('picture_redraw', 'Draw again', p));
    if (mayEdit(t.status)) out.push(act('picture_edit', 'Edit words', p, { edit: true }));
    if (editor && t.status === 'draft') out.push(act('picture_approve', 'Approve', p));
    if (editor) out.push(act('picture_retire', 'Retire', p, { confirm: 'Click again to retire the picture' }));
  } else if (t.page != null) {
    // one page of the novel: drawn (again), edited, and approved once it has a picture
    out.push(act('novel_draw', t.page_status ? `Draw page ${t.page} again` : `Draw page ${t.page}`, { novel_id: t.novel_id, pages: String(t.page) }));
    if (mayEdit(t.status) && mayEdit(t.page_status)) {
      out.push(act('novel_page_edit', `Edit page ${t.page}`, { novel_id: t.novel_id, page: t.page }, { edit: true }));
    }
    if (editor && t.page_status && t.page_status !== 'approved') {
      out.push(act('novel_page_approve', `Approve page ${t.page}`, { novel_id: t.novel_id, page: t.page }));
    }
  } else {
    const p = { novel_id: t.novel_id };
    out.push(act('novel_cast', 'Draw the cast', p));
    out.push(act('novel_draw', 'Draw the pages', { novel_id: t.novel_id, pages: '' }));
    // CORNER_C10_MAIL_2026_10_09: again, even where there is a picture (redo); a second click
    if (!t.drawn || t.drawn.cast > 0) {
      out.push(act('novel_cast', 'Draw the cast again', { ...p, redo: true }, { confirm: 'Click again to draw the cast again' }));
    }
    if (!t.drawn || t.drawn.pages > 0) {
      out.push(act('novel_draw', 'Draw every page again', { novel_id: t.novel_id, pages: '', redo: true }, { confirm: 'Click again to draw every page again' }));
    }
    if (editor && t.status !== 'approved') out.push(act('novel_approve', 'Approve the novel', p));
    if (editor) out.push(act('novel_retire', 'Retire', p, { confirm: 'Click again to retire the novel' }));
  }
  return out;
}

/** A redo is a kind of C10b's: offered only once corner_kinds() lists C10b's kinds. */
const needsC10 = (a: Action) => a.params.redo === true;

/** `className` replaces the bar's outer margin (mb-6 by default). */
export default function DeskActions({ target, className = 'mb-6' }: { target: DeskTarget; className?: string }) {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: [...CORNER_KEY, 'me'], queryFn: loadMe, staleTime: 60 * 1000 });
  const row = me.data?.ok ? me.data.rows[0] : undefined;
  const can = !!row?.can_request;
  const kinds = useQuery({ queryKey: [...CORNER_KEY, 'kinds'], queryFn: loadKinds, staleTime: 5 * 60 * 1000, enabled: can });
  // the same query as StoryPlate's, so it is asked once: a story with a picture is drawn again from the picture
  const story = target.type === 'story' ? target : null;
  const pics = useQuery({
    queryKey: ['mirror', 'media', 'story', story?.doc_code ?? '', story?.story_id ?? 0],
    queryFn: () => loadMedia({ doc: story!.doc_code, story: story!.story_id, k: 4 }),
    staleTime: 5 * 60 * 1000,
    enabled: can && !!story,
  });
  const hasPicture = !!(pics.data?.ok && pics.data.rows.filter(isMedia).length);
  const [armed, setArmed] = useState<string | null>(null);
  const [editing, setEditing] = useState<EditKind | null>(null);
  const [said, setSaid] = useState<{ ok: boolean; text: string } | null>(null);
  const m = useMutation({
    mutationFn: (a: Action) => createRequest(a.kind, target.doc_code, a.params),
    onSuccess: (r) => {
      setArmed(null);
      if (r.ok) {
        const x = r.rows[0];
        setSaid({ ok: true, text: `${x?.message ?? 'Asked.'}${x?.request_id ? ` (request #${x.request_id})` : ''}` });
        void qc.invalidateQueries({ queryKey: CORNER_KEY });
        flushMail();
      } else {
        setSaid({ ok: false, text: r.error ?? 'The request failed.' });
      }
    },
  });

  if (!can) return null;
  const known = new Map<string, CornerKind>((kinds.data?.ok ? kinds.data.rows : []).map((k) => [k.kind, k]));
  const usable = (kind: string) => kindUsable(kind, known.get(kind), !!row?.is_editor);
  const c10 = known.has('story_edit');
  const actions = actionsFor(target, !!row?.is_editor, hasPicture).filter((a) => usable(a.kind) && (!needsC10(a) || c10));
  const plan = target.type === 'story' && target.status === 'approved' && usable('novel_plan');
  if (!actions.length && !plan) return null;
  const novelPages = target.type === 'novel' ? target.pages : null;

  const click = (a: Action) => {
    if (a.edit) { setArmed(null); setSaid(null); setEditing(editing === a.kind ? null : (a.kind as EditKind)); return; }
    if (a.confirm && armed !== a.id) { setArmed(a.id); setSaid(null); return; }
    setSaid(null);
    m.mutate(a);
  };

  return (
    <div className={`rounded-md border border-dashed border-burgundy/40 px-3 py-2.5 text-sm print:hidden ${className}`} role="group" aria-label="Ask the desk">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <NotebookPen className="h-3.5 w-3.5" aria-hidden="true" /> Ask the desk
        </span>
        {actions.map((a) => {
          const k = known.get(a.kind);
          const est = k?.cost_bearing ? estimateFor(k, a.params, { pages: novelPages }) : 0;
          const on = armed === a.id;
          const open = !!a.edit && editing === a.kind;
          return (
            <button
              key={a.id}
              type="button"
              disabled={m.isPending}
              onClick={() => click(a)}
              aria-pressed={a.confirm ? on : undefined}
              aria-expanded={a.edit ? open : undefined}
              className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs disabled:opacity-50 ${on ? 'border-red-600 bg-red-50 text-red-800 dark:bg-red-950/30 dark:text-red-200' : open ? 'border-burgundy text-burgundy' : 'border-border text-foreground hover:border-burgundy hover:text-burgundy'}`}
            >
              {m.isPending && m.variables?.id === a.id && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
              <span>{on ? a.confirm : a.label}</span>
              {est > 0 && <span className="text-muted-foreground">{aboutUsd(est)}</span>}
            </button>
          );
        })}
        {plan && target.type === 'story' && (
          <Link
            to={`/corpus/corner?tab=ask&kind=novel_plan&doc=${encodeURIComponent(target.doc_code)}&story_id=${target.story_id}`}
            className="inline-flex items-center rounded-md border border-border px-2.5 py-1 text-xs text-foreground hover:border-burgundy hover:text-burgundy"
          >
            Plan a graphic novel
          </Link>
        )}
        {armed && (
          <button type="button" onClick={() => setArmed(null)} className="text-xs text-muted-foreground hover:text-foreground hover:underline">
            Keep it
          </button>
        )}
      </div>
      {editing && (
        <Suspense fallback={<p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> Opening the form...</p>}>
          <DeskEdit
            target={target}
            kind={editing}
            editor={!!row?.is_editor}
            onClose={() => setEditing(null)}
            onDone={(text) => { setEditing(null); setSaid({ ok: true, text }); }}
          />
        </Suspense>
      )}
      {said && <div className="mt-2"><ActionNote ok={said.ok} text={said.text} mineLink={said.ok} /></div>}
    </div>
  );
}
