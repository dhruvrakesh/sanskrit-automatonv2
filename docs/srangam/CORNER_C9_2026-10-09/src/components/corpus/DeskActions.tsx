/**
 * Ask the desk from where one is reading - CORNER_C9_2026_10_09.
 *
 * A compact bar under a story, a picture or a graphic novel, shown only to those who may ask the
 * desk (corner_me().can_request: invited researchers and editors); for everyone else it is nothing
 * at all, so the pages read exactly as before. Each button makes one request
 * (corner_request_create) and says what the server answered; the editors' decisions (approve,
 * retire) are requests too, carried out on the desk. Retiring asks for a second click.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, NotebookPen } from 'lucide-react';
import { ActionNote } from '@/components/corpus/CornerParts';
import {
  aboutUsd, CORNER_KEY, createRequest, estimateFor, imageIdOf, loadKinds, loadMe, type CornerKind,
} from '@/lib/corner';
import { isMedia, loadMedia } from '@/lib/corpusMedia';

export type DeskTarget =
  | { type: 'story'; doc_code: string; story_id: number; status: string | null }
  | { type: 'picture'; doc_code: string; image_id?: number | null; media_key?: string | null; status: string | null }
  | { type: 'novel'; doc_code: string; novel_id: number; status: string | null; pages?: number | null; page?: number; page_status?: string | null };

interface Action {
  kind: string;
  label: string;
  params: Record<string, unknown>;
  confirm?: string;
}

const GONE = new Set(['retired', 'rejected']);

function actionsFor(t: DeskTarget, editor: boolean, hasPicture: boolean): Action[] {
  const out: Action[] = [];
  if (GONE.has(t.status ?? '')) return out;
  if (t.type === 'story') {
    const p = { story_id: t.story_id };
    if (t.status === 'candidate') out.push({ kind: 'story_write', label: 'Write it', params: p });
    if (!hasPicture) out.push({ kind: 'story_illustrate', label: 'Illustrate', params: p });
    if (editor && t.status === 'draft') out.push({ kind: 'story_approve', label: 'Approve', params: p });
    if (editor) out.push({ kind: 'story_retire', label: 'Retire', params: p, confirm: 'Click again to retire the story' });
  } else if (t.type === 'picture') {
    const id = t.image_id ?? imageIdOf(t.media_key);
    if (id == null) return out;
    const p = { image_id: id };
    out.push({ kind: 'picture_redraw', label: 'Draw again', params: p });
    if (editor && t.status === 'draft') out.push({ kind: 'picture_approve', label: 'Approve', params: p });
    if (editor) out.push({ kind: 'picture_retire', label: 'Retire', params: p, confirm: 'Click again to retire the picture' });
  } else if (t.page != null) {
    // one page of the novel: drawn (again), and approved once it has a picture
    out.push({ kind: 'novel_draw', label: t.page_status ? `Draw page ${t.page} again` : `Draw page ${t.page}`, params: { novel_id: t.novel_id, pages: String(t.page) } });
    if (editor && t.page_status && t.page_status !== 'approved') {
      out.push({ kind: 'novel_page_approve', label: `Approve page ${t.page}`, params: { novel_id: t.novel_id, page: t.page } });
    }
  } else {
    const p = { novel_id: t.novel_id };
    out.push({ kind: 'novel_cast', label: 'Draw the cast', params: p });
    out.push({ kind: 'novel_draw', label: 'Draw the pages', params: { novel_id: t.novel_id, pages: '' } });
    if (editor && t.status !== 'approved') out.push({ kind: 'novel_approve', label: 'Approve the novel', params: p });
    if (editor) out.push({ kind: 'novel_retire', label: 'Retire', params: p, confirm: 'Click again to retire the novel' });
  }
  return out;
}

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
  const [said, setSaid] = useState<{ ok: boolean; text: string } | null>(null);
  const m = useMutation({
    mutationFn: (a: Action) => createRequest(a.kind, target.doc_code, a.params),
    onSuccess: (r) => {
      setArmed(null);
      if (r.ok) {
        const x = r.rows[0];
        setSaid({ ok: true, text: `${x?.message ?? 'Asked.'}${x?.request_id ? ` (request #${x.request_id})` : ''}` });
        void qc.invalidateQueries({ queryKey: CORNER_KEY });
      } else {
        setSaid({ ok: false, text: r.error ?? 'The request failed.' });
      }
    },
  });

  if (!can) return null;
  const known = new Map<string, CornerKind>((kinds.data?.ok ? kinds.data.rows : []).map((k) => [k.kind, k]));
  const usable = (kind: string) => {
    const k = known.get(kind);
    return k ? k.enabled && (!k.editor_only || !!row?.is_editor) : true;
  };
  const actions = actionsFor(target, !!row?.is_editor, hasPicture).filter((a) => usable(a.kind));
  const plan = target.type === 'story' && target.status === 'approved' && usable('novel_plan');
  if (!actions.length && !plan) return null;
  const novelPages = target.type === 'novel' ? target.pages : null;

  const click = (a: Action) => {
    if (a.confirm && armed !== a.kind) { setArmed(a.kind); setSaid(null); return; }
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
          const on = armed === a.kind;
          return (
            <button
              key={a.kind + a.label}
              type="button"
              disabled={m.isPending}
              onClick={() => click(a)}
              aria-pressed={a.confirm ? on : undefined}
              className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs disabled:opacity-50 ${on ? 'border-red-600 bg-red-50 text-red-800 dark:bg-red-950/30 dark:text-red-200' : 'border-border text-foreground hover:border-burgundy hover:text-burgundy'}`}
            >
              {m.isPending && m.variables?.kind === a.kind && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
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
      {said && <div className="mt-2"><ActionNote ok={said.ok} text={said.text} mineLink={said.ok} /></div>}
    </div>
  );
}
