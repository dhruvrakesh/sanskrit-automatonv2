/**
 * The desk's edit forms - CORNER_C10_MAIL_2026_10_09. Loaded only when Edit is clicked under a
 * story, a picture or a graphic novel's page (DeskActions), so the reading pages stay as small as
 * they were.
 *
 * Each form starts from what the page shows (the DeskTarget's values) and sends only what changed,
 * trimmed: story_edit (title, title_hi; for a written story also story_en, story_hi), picture_edit
 * (title, caption_en, caption_hi, context_note; the licence for editors), novel_page_edit (scene,
 * caption, caption_hi). The bounds are corner._clean's (cornerC10.ts); the database checks them
 * again and the desk once more before it changes anything. A free request is approved at once and
 * the change reaches the page after the desk's next round and sync.
 */
import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ActionNote } from '@/components/corpus/CornerParts';
import type { DeskTarget } from '@/components/corpus/DeskActions';
import { CORNER_KEY, createRequest, imageIdOf, s } from '@/lib/corner';
import { changedFields, editFields, fieldProblem, type EditKind, type FieldRule } from '@/lib/cornerC10';
import { flushMail } from '@/lib/cornerMail';

interface Props {
  target: DeskTarget;
  kind: EditKind;
  editor: boolean;
  onClose: () => void;
  /** The request was made: the server's sentence, for the bar to show. */
  onDone: (text: string) => void;
}

/** What the request names (the story, the picture, the page) and what the page shows of it now. */
function subject(t: DeskTarget): { ids: Record<string, unknown> | null; before: Record<string, unknown>; key: string } {
  if (t.type === 'story') {
    return { ids: { story_id: t.story_id }, key: `s${t.story_id}`, before: { title: t.title, title_hi: t.title_hi, story_en: t.story_en, story_hi: t.story_hi } };
  }
  if (t.type === 'picture') {
    const id = t.image_id ?? imageIdOf(t.media_key);
    return {
      ids: id == null ? null : { image_id: id }, key: `p${id ?? 'x'}`,
      before: { title: t.title, caption_en: t.caption_en, caption_hi: t.caption_hi, context_note: t.context_note, license: t.license },
    };
  }
  return {
    ids: t.page != null ? { novel_id: t.novel_id, page: t.page } : null, key: `n${t.novel_id}-${t.page ?? 0}`,
    before: { scene: t.scene, caption: t.caption, caption_hi: t.caption_hi },
  };
}

const TITLES: Record<EditKind, string> = {
  story_edit: 'Edit the story', picture_edit: "Edit the picture's words", novel_page_edit: 'Edit the page',
};

function helpFor(kind: EditKind, status: string | null): string {
  if (kind === 'story_edit') {
    return status === 'candidate'
      ? 'Only what you change is sent. A proposed episode keeps its place until it is written; only its titles change now.'
      : 'Only what you change is sent. The desk makes the change on its next round and checks the story against its citations again; the story is then a draft until an editor approves it.';
  }
  if (kind === 'picture_edit') return 'Only what you change is sent. The desk makes the change on its next round; the picture itself is not drawn again.';
  return 'Only what you change is sent. The desk makes the change on its next round. A new scene does not draw the page again: ask for that after.';
}

export default function DeskEdit({ target, kind, editor, onClose, onDone }: Props) {
  const qc = useQueryClient();
  const { ids, before, key } = useMemo(() => subject(target), [target]);
  const status = target.status;
  const rules = useMemo(() => editFields(kind, status, editor), [kind, status, editor]);
  const [vals, setVals] = useState<Record<string, string>>(() => Object.fromEntries(rules.map((f) => [f.key, s(before[f.key])])));
  const changed = changedFields(rules, before, vals);
  const problems = rules.map((f) => (f.key in changed ? fieldProblem(f, changed[f.key]) : null)).filter((x): x is string => !!x);
  const count = Object.keys(changed).length;
  const m = useMutation({
    mutationFn: () => createRequest(kind, target.doc_code, { ...(ids ?? {}), ...changed }),
    onSuccess: (r) => {
      if (!r.ok) return;
      const x = r.rows[0];
      void qc.invalidateQueries({ queryKey: CORNER_KEY });
      void flushMail();
      onDone(`${x?.message ?? 'Asked.'}${x?.request_id ? ` (request #${x.request_id})` : ''}`);
    },
  });
  const title = target.type === 'novel' && target.page != null ? `Edit page ${target.page}` : TITLES[kind];
  const can = !!ids && count > 0 && problems.length === 0 && !m.isPending;
  const field = (f: FieldRule) => {
    const id = `desk-edit-${key}-${f.key}`;
    const common = {
      id, value: vals[f.key] ?? '',
      onChange: (e: { target: { value: string } }) => setVals((v) => ({ ...v, [f.key]: e.target.value })),
      lang: f.lang, className: f.lang === 'hi' ? 'font-devanagari' : undefined,
    };
    return (
      <div key={f.key} className="space-y-1.5">
        <Label htmlFor={id}>{f.label}{f.key in changed ? ' (changed)' : ''}</Label>
        {f.rows ? <Textarea rows={f.rows} {...common} /> : <Input {...common} />}
      </div>
    );
  };
  return (
    <div className="mt-3 space-y-3 rounded-md border border-border bg-background p-3">
      <h3 className="font-serif text-base text-foreground">{title}</h3>
      <p className="text-xs text-muted-foreground">{helpFor(kind, status)}</p>
      <form aria-label={title} className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (can) m.mutate(); }}>
        {rules.map(field)}
        {problems.map((p) => <ActionNote key={p} ok={false} text={p} />)}
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" size="sm" disabled={!can} className="bg-burgundy text-white hover:bg-burgundy/90">
            {m.isPending ? 'Sending...' : count > 1 ? `Send ${count} changes` : 'Send the change'}
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={onClose} disabled={m.isPending}>Cancel</Button>
          {count === 0 && <span className="text-xs text-muted-foreground">Nothing changed yet.</span>}
        </div>
      </form>
      {m.data && !m.data.ok && <ActionNote ok={false} text={m.data.error} />}
    </div>
  );
}
