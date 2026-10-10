/**
 * The Corner's new panels - CORNER_C10_MAIL_2026_10_09. Loaded by /corpus/corner when one of them is
 * first shown, so the Corner's own chunk grows little.
 *
 *   IdeasPanel    Ask: the ideas for pictures the desk proposed for the chosen text (corner_ideas,
 *                 everyone's, newest first), each with "Draw this idea" (picture_draw) or, once drawn,
 *                 a link to the picture.
 *   IdeasResult   My requests: the ideas of a finished picture_ideas or picture_cover request, the same.
 *   RetiredPanel  Ask, editors: the text's retired pictures (corner_retired_pictures), each with
 *                 "Restore" (picture_restore).
 *   MailPrefsCard Settings, everyone: email me when my requests finish; editors also when a
 *                 researcher's request waits (corner_mail_prefs_set).
 *   MailAdminCard Settings, the super admin: email on or off, From, Reply-to, the site's address
 *                 (corner_settings_set).
 *   MailLine      Sync, editors: the email queue (corner_mail_state).
 * Every action is a request or a database function that checks the caller again; a function the
 * database does not have yet shows nothing.
 */
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Images, Loader2, Mail, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { ActionNote, CornerProblem } from '@/components/corpus/CornerParts';
import { atHref } from '@/lib/corpusLibrary';
import {
  aboutUsd, CORNER_KEY, createRequest, estimateFor, kindUsable, loadKinds, pictureHref, setSetting, statusLabel, when,
  type CornerKind, type CornerMe, type CornerRequest, type SettingKey,
} from '@/lib/corner';
import {
  ideaRow, ideaState, IDEAS_KEY, loadIdeas, loadRetired, parseIdeas, RETIRED_KEY, retiredRow, type Idea, type IdeaRow,
} from '@/lib/cornerC10';
import {
  cleanMailFrom, cleanReplyTo, cleanSiteUrl, DEFAULT_FROM, DEFAULT_SITE, flushMail, loadMailState, MAIL_KEY, mailLineText,
  MAIL_PREFS_KEY, MAIL_STATE_KEY, saveMailPrefs, type MailPrefs,
} from '@/lib/cornerMail';
import { clockTime } from '@/lib/cornerState';

const KINDS_KEY = [...CORNER_KEY, 'kinds'] as const;
const LINK = 'font-medium text-burgundy underline decoration-burgundy/40 underline-offset-2 hover:decoration-burgundy';

function useKinds() {
  const q = useQuery({ queryKey: KINDS_KEY, queryFn: loadKinds, staleTime: 5 * 60 * 1000 });
  return new Map<string, CornerKind>((q.data?.ok ? q.data.rows : []).map((k) => [k.kind, k]));
}

/** One request from a panel's button: the server's sentence after it, the waiting emails sent. */
function useAsk(kind: string, doc: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: Record<string, unknown>) => createRequest(kind, doc, params),
    onSuccess: (r) => {
      if (!r.ok) return;
      void qc.invalidateQueries({ queryKey: CORNER_KEY });
      void flushMail();
    },
  });
}

const asked = (r: { ok: boolean; rows: { message?: string; request_id?: number }[]; error: string | null }) =>
  (r.ok ? `${r.rows[0]?.message ?? 'Asked.'}${r.rows[0]?.request_id ? ` (request #${r.rows[0].request_id})` : ''}` : r.error);

// ---- the ideas for pictures -----------------------------------------------------------------

function DrawIdea({ doc, idea, row, k, may }: { doc: string; idea: Idea; row: IdeaRow | null; k: CornerKind | undefined; may: boolean }) {
  const m = useAsk('picture_draw', doc);
  const state = ideaState(row);
  const name = idea.title || `img:${idea.image_id}`;
  if (state === 'drawn') {
    return <Link to={pictureHref(doc, idea.image_id)} className={`text-xs ${LINK}`}>See the picture</Link>;
  }
  if (state === 'asked') {
    return (
      <p className="text-xs text-muted-foreground">
        Asked to be drawn{row?.draw_request_id ? ` (request #${row.draw_request_id})` : ''}: {statusLabel(row?.draw_status)}.
      </p>
    );
  }
  if (state === 'synced') {
    return <p className="text-xs text-muted-foreground">Drawn on the desk; the picture comes here with the desk&apos;s next sync.</p>;
  }
  const est = estimateFor(k, { image_id: idea.image_id });
  const before = row?.draw_status && ['failed', 'rejected', 'cancelled'].includes(row.draw_status)
    ? `The last request to draw it was ${statusLabel(row.draw_status)}.` : null;
  return (
    <div className="space-y-1.5">
      {before && <p className="text-xs text-muted-foreground">{before}</p>}
      {may && !(m.data?.ok) && (
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" variant="outline" className="h-7 px-2.5 text-xs" disabled={m.isPending}
            onClick={() => m.mutate({ image_id: idea.image_id })} aria-label={`Draw this idea: ${name}`}>
            {m.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" aria-hidden="true" />}
            Draw this idea
          </Button>
          {est > 0 && <span className="text-xs text-muted-foreground">{aboutUsd(est)}</span>}
        </div>
      )}
      {m.data && <ActionNote ok={m.data.ok} text={asked(m.data)} mineLink={m.data.ok} />}
    </div>
  );
}

function IdeaItem({ doc, idea, row, k, may }: { doc: string; idea: Idea; row: IdeaRow | null; k: CornerKind | undefined; may: boolean }) {
  return (
    <li className="space-y-1 rounded-md border border-border p-3 text-sm">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-medium text-foreground">{idea.title || `An idea (img:${idea.image_id})`}</span>
        {idea.kind === 'cover' && <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">cover</span>}
        {idea.at && <Link to={atHref(doc, idea.at)} className="font-mono text-xs text-burgundy hover:underline" title="The passage it illustrates">{idea.at}</Link>}
        <span className="font-mono text-xs text-muted-foreground">img:{idea.image_id}</span>
      </div>
      {idea.brief && <p className="line-clamp-4 whitespace-pre-line text-muted-foreground">{idea.brief}</p>}
      <DrawIdea doc={doc} idea={idea} row={row} k={k} may={may} />
    </li>
  );
}

const SHOWN = 20;

/** The text's ideas for pictures, everyone's, newest first. */
export function IdeasPanel({ doc, me }: { doc: string; me: CornerMe }) {
  const known = useKinds();
  const [all, setAll] = useState(false);
  const q = useQuery({
    queryKey: IDEAS_KEY(doc), queryFn: () => loadIdeas(doc), staleTime: 60 * 1000,
    refetchInterval: (query) => ((query.state.data?.ok ? query.state.data.rows : []).some((x) => ideaState(ideaRow(x)) === 'asked') ? 60 * 1000 : false),
  });
  if (q.data && !q.data.ok && (q.data.missing || q.data.refused)) return null;
  const rows = (q.data?.ok ? q.data.rows : []).map(ideaRow).filter((x): x is IdeaRow => !!x);
  const k = known.get('picture_draw');
  const may = kindUsable('picture_draw', k, me.is_editor);
  const waiting = rows.filter((r) => ideaState(r) === 'waiting').length;
  const shown = all ? rows : rows.slice(0, SHOWN);
  return (
    <section aria-labelledby="ideas-head" className="mt-6 space-y-3">
      <h3 id="ideas-head" className="flex items-center gap-2 font-serif text-lg font-semibold text-foreground">
        <Images className="h-4 w-4 text-burgundy" aria-hidden="true" /> Ideas waiting to be drawn
        {rows.length > 0 && <span className="text-sm font-normal text-muted-foreground">({waiting} of {rows.length})</span>}
      </h3>
      <p className="text-xs text-muted-foreground">
        The desk&apos;s ideas for pictures in this text, everyone&apos;s, newest first. Drawing one is a request of its own; a drawn
        picture comes back as a draft until an editor approves it.
      </p>
      {q.isLoading && <Skeleton className="h-20 w-full" />}
      {q.data && !q.data.ok && <CornerProblem r={q.data} what="The ideas for pictures" />}
      {q.data?.ok && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">No ideas for pictures in this text yet. Ask the desk for some above.</p>
      )}
      {shown.length > 0 && (
        <ol className="grid gap-3 lg:grid-cols-2">
          {shown.map((r) => <IdeaItem key={r.image_id} doc={doc} idea={r} row={r} k={k} may={may} />)}
        </ol>
      )}
      {!all && rows.length > SHOWN && (
        <Button type="button" size="sm" variant="outline" onClick={() => setAll(true)}>Show all {rows.length} ideas</Button>
      )}
    </section>
  );
}

/** The ideas of a finished picture_ideas or picture_cover request, each with "Draw this idea". */
export function IdeasResult({ r, editor }: { r: CornerRequest; editor: boolean }) {
  const doc = r.doc_code ?? '';
  const known = useKinds();
  const ideas = parseIdeas(r.result);
  const q = useQuery({ queryKey: IDEAS_KEY(doc), queryFn: () => loadIdeas(doc), staleTime: 60 * 1000, enabled: !!doc && ideas.length > 0 });
  const byId = new Map<number, IdeaRow>();
  for (const x of q.data?.ok ? q.data.rows : []) {
    const row = ideaRow(x);
    if (row) byId.set(row.image_id, row);
  }
  if (!doc) return null;
  if (!ideas.length) return <p className="text-sm text-muted-foreground">The desk proposed no new idea this time.</p>;
  const k = known.get('picture_draw');
  const may = kindUsable('picture_draw', k, editor);
  return (
    <div role="group" aria-label={`Ideas of request #${r.id}`} className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">
        {ideas.length === 1 ? 'The idea' : `The ${ideas.length} ideas`} the desk proposed:
      </p>
      <ol className="grid gap-2 lg:grid-cols-2">
        {ideas.map((i) => <IdeaItem key={i.image_id} doc={doc} idea={i} row={byId.get(i.image_id) ?? null} k={k} may={may} />)}
      </ol>
    </div>
  );
}

// ---- retired pictures (editors) -------------------------------------------------------------

function Restore({ doc, id, name }: { doc: string; id: number; name: string }) {
  const m = useAsk('picture_restore', doc);
  return (
    <div className="space-y-1.5">
      {!(m.data?.ok) && (
        <Button type="button" size="sm" variant="outline" className="h-7 gap-1 px-2.5 text-xs" disabled={m.isPending}
          onClick={() => m.mutate({ image_id: id })} aria-label={`Restore ${name}`}>
          {m.isPending ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> : <RotateCcw className="h-3 w-3" aria-hidden="true" />}
          Restore
        </Button>
      )}
      {m.data && <ActionNote ok={m.data.ok} text={asked(m.data)} mineLink={m.data.ok} />}
    </div>
  );
}

/** The text's retired pictures, newest first, each with "Restore". Editors only (the database says so too). */
export function RetiredPanel({ doc }: { doc: string }) {
  const [all, setAll] = useState(false);
  const q = useQuery({ queryKey: RETIRED_KEY(doc), queryFn: () => loadRetired(doc), staleTime: 60 * 1000 });
  if (q.data && !q.data.ok && (q.data.missing || q.data.refused)) return null;
  const rows = (q.data?.ok ? q.data.rows : []).map(retiredRow).filter((x): x is NonNullable<ReturnType<typeof retiredRow>> => !!x);
  const shown = all ? rows : rows.slice(0, SHOWN);
  return (
    <section aria-labelledby="retired-head" className="mt-6 space-y-3">
      <h3 id="retired-head" className="font-serif text-lg font-semibold text-foreground">
        Retired pictures{rows.length > 0 && <span className="ml-2 text-sm font-normal text-muted-foreground">({rows.length})</span>}
      </h3>
      <p className="text-xs text-muted-foreground">
        For editors. A restored picture comes back as a draft after the desk&apos;s next round, or as an idea to draw when the
        desk has no drawing of it.
      </p>
      {q.isLoading && <Skeleton className="h-16 w-full" />}
      {q.data && !q.data.ok && <CornerProblem r={q.data} what="The retired pictures" />}
      {q.data?.ok && rows.length === 0 && <p className="text-sm text-muted-foreground">No picture of this text is retired.</p>}
      {shown.length > 0 && (
        <ol className="grid gap-3 lg:grid-cols-2">
          {shown.map((p) => {
            const name = p.title || `img:${p.image_id}`;
            return (
              <li key={p.image_id} className="space-y-1 rounded-md border border-border p-3 text-sm">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="font-medium text-foreground">{name}</span>
                  <span className="font-mono text-xs text-muted-foreground">img:{p.image_id}</span>
                  {p.retired_at && <span className="text-xs text-muted-foreground">retired {when(p.retired_at)}</span>}
                </div>
                {p.caption_en && <p className="line-clamp-2 text-muted-foreground">{p.caption_en}</p>}
                {!p.has_file && <p className="text-xs text-muted-foreground">Its file is no longer on the site.</p>}
                <Restore doc={doc} id={p.image_id} name={name} />
              </li>
            );
          })}
        </ol>
      )}
      {!all && rows.length > SHOWN && (
        <Button type="button" size="sm" variant="outline" onClick={() => setAll(true)}>Show all {rows.length}</Button>
      )}
    </section>
  );
}

// ---- email ----------------------------------------------------------------------------------

function Check({ id, checked, onChange, disabled, label }: {
  id: string; checked: boolean; onChange: (v: boolean) => void; disabled?: boolean; label: string;
}) {
  return (
    <label htmlFor={id} className="flex items-center gap-2 text-sm font-medium">
      <input id={id} type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)}
        aria-label={label} className="h-4 w-4 accent-[hsl(var(--burgundy))]" />
      {label}
    </label>
  );
}

/** Everyone's own choice. Each box is kept as soon as it is changed. */
export function MailPrefsCard({ prefs, editor }: { prefs: MailPrefs; editor: boolean }) {
  const qc = useQueryClient();
  const [mine, setMine] = useState(prefs.on_my_requests);
  const [queue, setQueue] = useState(prefs.on_queue);
  const [said, setSaid] = useState<{ ok: boolean; text: string } | null>(null);
  const m = useMutation({
    mutationFn: (v: { mine: boolean | null; queue: boolean | null }) => saveMailPrefs(v.mine, v.queue),
    onSuccess: (r, v) => {
      if (r.ok) {
        setSaid({ ok: true, text: 'Saved.' });
        void qc.invalidateQueries({ queryKey: MAIL_PREFS_KEY });
      } else {
        if (v.mine != null) setMine(!v.mine);
        if (v.queue != null) setQueue(!v.queue);
        setSaid({ ok: false, text: r.error ?? 'It could not be saved.' });
      }
    },
  });
  const isEditor = editor || prefs.is_editor;
  return (
    <Card className="max-w-2xl">
      <CardContent className="space-y-3 pt-6 text-sm">
        <h2 className="flex items-center gap-2 font-serif text-lg font-semibold text-foreground">
          <Mail className="h-4 w-4 text-burgundy" aria-hidden="true" /> Email
        </h2>
        <div className="space-y-1">
          <Check id="mail-mine" checked={mine} disabled={m.isPending} label="Email me when my requests finish"
            onChange={(v) => { setMine(v); setSaid(null); m.mutate({ mine: v, queue: null }); }} />
          <p className="pl-6 text-xs text-muted-foreground">When a paid request is done, when any request fails, and when an editor turns one down.</p>
        </div>
        {isEditor && (
          <div className="space-y-1">
            <Check id="mail-queue" checked={queue} disabled={m.isPending} label="Email me when a researcher's request waits"
              onChange={(v) => { setQueue(v); setSaid(null); m.mutate({ mine: null, queue: v }); }} />
            <p className="pl-6 text-xs text-muted-foreground">One email for each request that waits for an editor&apos;s decision.</p>
          </div>
        )}
        {said && <ActionNote ok={said.ok} text={said.text} />}
        {!prefs.mail_enabled && (
          <p className="text-muted-foreground">Email from the Corner is off at the moment. Your choice is kept for when it is turned on.</p>
        )}
        <p className="text-xs text-muted-foreground">
          The emails come from {prefs.mail_from ?? 'nartiang.org'} to the address you sign in with. Each one ends with a link back here.
        </p>
      </CardContent>
    </Card>
  );
}

function MailRow({ k, label, hint, value, shown, children }: {
  k: SettingKey; label: string; hint: string; value: () => string | null; shown?: (v: string) => string; children: ReactNode;
}) {
  const qc = useQueryClient();
  const [bad, setBad] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: (v: string) => setSetting(k, v),
    onSuccess: (r) => { if (r.ok) void qc.invalidateQueries({ queryKey: MAIL_KEY }); },
  });
  const save = () => {
    const v = value();
    if (v == null) { setBad(hint); return; }
    setBad(null);
    m.mutate(v);
  };
  const kept = m.data?.ok ? String(m.data.rows[0] ?? '') : '';
  return (
    <div className="space-y-2 border-b border-border pb-4 last:border-0">
      <p className="font-medium text-foreground">{label}</p>
      <div className="flex flex-wrap items-end gap-3">
        {children}
        <Button type="button" size="sm" variant="outline" disabled={m.isPending} onClick={save}>{m.isPending ? 'Saving...' : 'Save'}</Button>
      </div>
      <p className="text-xs text-muted-foreground">{hint}</p>
      {bad && <ActionNote ok={false} text={bad} />}
      {m.data && <ActionNote ok={m.data.ok} text={m.data.ok ? `Saved: ${shown ? shown(kept) : kept}` : m.data.error} />}
    </div>
  );
}

/** The super admin's email settings. Reply-to and the site's address are not read back (the
 *  database does not answer them); what is saved replaces them. */
export function MailAdminCard({ prefs }: { prefs: MailPrefs }) {
  const [on, setOn] = useState(prefs.mail_enabled);
  const [from, setFrom] = useState(prefs.mail_from ?? DEFAULT_FROM);
  const [reply, setReply] = useState('');
  const [site, setSite] = useState('');
  return (
    <Card className="max-w-2xl">
      <CardContent className="space-y-4 pt-6 text-sm">
        <h2 className="font-serif text-lg font-semibold text-foreground">Email from the Corner (super admin)</h2>
        <MailRow k="mail_enabled" label="Sending" value={() => (on ? 'true' : 'false')} shown={(v) => (v === 'true' ? 'on' : 'off')}
          hint="When on, the Corner queues its emails and the corner-mail function sends them through Resend. Nothing goes out until RESEND_API_KEY is in the project's secrets and corner-mail is deployed.">
          <Check id="mail-enabled" checked={on} onChange={setOn} label="Send the Corner's emails" />
        </MailRow>
        <MailRow k="mail_from" label="From" value={() => cleanMailFrom(from)}
          hint="A name and an address at a domain verified in Resend, such as Srangam desk <desk@nartiang.org>.">
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label htmlFor="mail-from">Name and address</Label>
            <Input id="mail-from" value={from} onChange={(e) => setFrom(e.target.value)} maxLength={320} />
          </div>
        </MailRow>
        <MailRow k="mail_reply_to" label="Reply-to" value={() => cleanReplyTo(reply)} shown={(v) => v || '(none)'}
          hint="Where replies go: one address, or empty for none. The address saved now is not shown here; saving replaces it.">
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label htmlFor="mail-reply">Address</Label>
            <Input id="mail-reply" type="email" value={reply} onChange={(e) => setReply(e.target.value)} maxLength={254} placeholder="desk@nartiang.org" />
          </div>
        </MailRow>
        <MailRow k="site_url" label="The site's address in the emails" value={() => cleanSiteUrl(site)}
          hint={`https:// and the host, no path, such as ${DEFAULT_SITE}. The address saved now is not shown here; saving replaces it.`}>
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label htmlFor="mail-site">Address</Label>
            <Input id="mail-site" value={site} onChange={(e) => setSite(e.target.value)} maxLength={200} placeholder={DEFAULT_SITE} />
          </div>
        </MailRow>
      </CardContent>
    </Card>
  );
}

/** The Sync tab's line on the email queue (editors). */
export function MailLine({ now }: { now: number }) {
  const q = useQuery({ queryKey: MAIL_STATE_KEY, queryFn: loadMailState, staleTime: 60 * 1000, refetchInterval: 5 * 60 * 1000 });
  const m = q.data?.ok ? q.data.data : null;
  if (!m) return null;
  return (
    <section aria-label="Email" className="space-y-1 rounded-md border border-border bg-muted/30 px-4 py-3 text-sm">
      <p className="flex flex-wrap items-center gap-x-1.5">
        <Mail className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <span className="font-medium text-foreground">Mail:</span>
        <span className={m.mail_enabled ? 'text-foreground' : 'text-muted-foreground'}>{mailLineText(m, (ts) => clockTime(ts, now))}</span>
      </p>
      {m.last_error && (
        <p className="text-xs text-muted-foreground">Last problem: <span className="break-all font-mono">{m.last_error}</span></p>
      )}
      {!m.mail_enabled && <p className="text-xs text-muted-foreground">The super admin turns it on in Settings.</p>}
    </section>
  );
}
