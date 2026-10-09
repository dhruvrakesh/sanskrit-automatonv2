/**
 * The Researchers' Corner, as it happens - CORNER_STATE_S1_2026_10_09: a request's stages and
 * progress, the next steps of a finished one, the desk's state as chips (editors), a command to copy,
 * and the Sync tab's cards. Only the Corner's page imports this file.
 */
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Ban, CheckCircle2, Circle, CircleDot, Clock, Info, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { deskIsLate, lastSeenText, TONE_CLASS, type CornerMe, type ResultLink, type Tone } from '@/lib/corner';
import {
  clockTime, DESK_COMMANDS, DESK_ROOT, mediaView, mirrorView, nextRound, progressText, requestStages, spendView,
  type DeskInfo, type LiveRequest, type RunView, type Stage,
} from '@/lib/cornerState';

const SEGMENT: Record<Tone, string> = {
  blue: 'bg-sky-600 dark:bg-sky-400', green: 'bg-emerald-600 dark:bg-emerald-400', amber: 'bg-amber-500 dark:bg-amber-400',
  red: 'bg-red-600 dark:bg-red-400', muted: 'bg-muted-foreground/50',
};
const LABEL: Record<Tone, string> = {
  blue: 'text-foreground', green: 'text-emerald-800 dark:text-emerald-300', amber: 'text-amber-800 dark:text-amber-300',
  red: 'text-red-700 dark:text-red-300', muted: 'text-muted-foreground',
};

function StageIcon({ s }: { s: Stage }) {
  const c = 'mt-px h-3 w-3 shrink-0';
  if (s.state === 'ahead') return <Circle className={`${c} text-muted-foreground/60`} aria-hidden="true" />;
  if (s.state === 'past') return <CheckCircle2 className={`${c} ${s.tone === 'green' ? 'text-emerald-600' : 'text-sky-600 dark:text-sky-400'}`} aria-hidden="true" />;
  if (s.tone === 'green') return <CheckCircle2 className={`${c} text-emerald-600`} aria-hidden="true" />;
  if (s.tone === 'red') return <XCircle className={`${c} text-red-600`} aria-hidden="true" />;
  if (s.tone === 'amber') return <Clock className={`${c} text-amber-600`} aria-hidden="true" />;
  if (s.tone === 'muted') return <Ban className={`${c} text-muted-foreground`} aria-hidden="true" />;
  return <CircleDot className={`${c} text-sky-600 dark:text-sky-400`} aria-hidden="true" />;
}

/** Where a request is: Asked -> Approved -> Taken by the desk -> Working -> Done, each with its
 *  local time, or how it stopped; while the desk works, its progress. Every state is in words. */
export function StageBar({ r }: { r: LiveRequest }) {
  const stages = requestStages(r, r.track);
  const working = r.status === 'running' || r.status === 'claimed';
  const p = working ? r.track?.progress ?? null : null;
  const text = progressText(p);
  const counted = !!p && p.step != null && p.of != null;
  return (
    <div className="space-y-2">
      <ol role="list" aria-label={`Stages of request #${r.id}`} className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))` }}>
        {stages.map((s) => (
          <li key={s.key} aria-current={s.state === 'now' ? 'step' : undefined} className="min-w-0">
            <span aria-hidden="true" className={`block h-1.5 rounded-full ${s.state === 'ahead' ? 'bg-border' : SEGMENT[s.tone]}`} />
            <span className={`mt-1 flex items-start gap-1 text-[11px] leading-tight ${s.state === 'ahead' ? 'text-muted-foreground' : LABEL[s.tone]} ${s.state === 'now' ? 'font-semibold' : ''}`}>
              <StageIcon s={s} />
              <span className="min-w-0 break-words">
                {s.label}
                {s.state === 'ahead' && <span className="sr-only"> (not yet)</span>}
              </span>
            </span>
            {s.at && <time dateTime={s.at} className="mt-0.5 block text-[11px] leading-tight text-muted-foreground">{clockTime(s.at)}</time>}
            {s.note && <span className="block text-[11px] leading-tight text-muted-foreground">{s.note}</span>}
          </li>
        ))}
      </ol>
      {text && (
        <div className="space-y-1">
          <p className="text-xs text-foreground">
            {text}
            {p?.at && <span className="text-muted-foreground"> (at {clockTime(p.at)})</span>}
          </p>
          {counted && (
            <div
              role="progressbar" aria-label={`Progress of request #${r.id}`} aria-valuemin={0} aria-valuemax={p.of!}
              aria-valuenow={p.step!} aria-valuetext={text} className="h-1 w-full overflow-hidden rounded-full bg-muted"
            >
              <div className="h-full rounded-full bg-sky-600 dark:bg-sky-400" style={{ width: `${Math.round((100 * p.step!) / p.of!)}%` }} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** What to do next with a finished request: links on to the Ask form, the result, or the page
 *  where an editor approves it. */
export function NextSteps({ links }: { links: ResultLink[] }) {
  if (!links.length) return null;
  return (
    <div role="group" aria-label="Next steps" className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-muted-foreground">Next:</span>
      {links.map((l) => (
        <Link key={`${l.label}|${l.href}`} to={l.href}
          className="inline-flex items-center rounded-md border border-border px-2.5 py-1 text-xs text-foreground hover:border-burgundy hover:text-burgundy">
          {l.label}
        </Link>
      ))}
    </div>
  );
}

function Chip({ tone, ok, children }: { tone: Tone; ok: boolean; children: ReactNode }) {
  return (
    <li>
      <Link to="/corpus/corner?tab=sync" className={`inline-flex max-w-full items-start gap-1 rounded px-1.5 py-0.5 text-xs font-medium hover:underline ${TONE_CLASS[tone]}`}>
        {ok ? <CheckCircle2 className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" /> : <AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
        <span className="min-w-0 break-words">{children}</span>
      </Link>
    </li>
  );
}

/** The desk's state in three chips (editors): the mirror, the pictures, the desk's spend. Only what
 *  the desk reported is shown; an older desk reports none of it. */
export function DeskChips({ info, now }: { info: DeskInfo; now: number }) {
  const m = info.sync?.mirror ? mirrorView(info.sync.mirror, now) : null;
  const d = info.sync?.media ? mediaView(info.sync.media, now) : null;
  const b = info.budget ? spendView(info.budget) : null;
  if (!m && !d && !b) return null;
  return (
    <ul role="list" aria-label="The desk's sync" className="flex flex-wrap gap-2">
      {m && <Chip tone={m.tone} ok={m.state === 'in_step'}>Mirror: {m.text}</Chip>}
      {d && <Chip tone={d.tone} ok={d.state === 'in_step'}>Pictures: {d.text}</Chip>}
      {b && <Chip tone={b.tone} ok={!info.budget?.paused && info.budget!.left > 0}>Desk spend: {b.text}</Chip>}
    </ul>
  );
}

/** One command for the desk, with a button that copies it. */
export function CopyCommand({ command, from }: { command: string; from?: string }) {
  const [said, setSaid] = useState<string | null>(null);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setSaid('Copied.');
    } catch {
      setSaid('Select the command to copy it.');
    }
  };
  return (
    <div className="space-y-1">
      <div className="flex items-start gap-2">
        <code className="min-w-0 flex-1 whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-xs text-foreground">{command}</code>
        <Button type="button" size="sm" variant="outline" className="h-7 shrink-0 px-2 text-xs" onClick={() => void copy()} aria-label={`Copy ${command}`}>
          Copy
        </Button>
      </div>
      {from && <p className="text-xs text-muted-foreground">Run it from <code className="break-all font-mono">{from}</code></p>}
      {said && <p role="status" className="text-xs text-muted-foreground">{said}</p>}
    </div>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words text-foreground">{children}</dd>
    </>
  );
}

function StateBadge({ v }: { v: RunView }) {
  return <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${TONE_CLASS[v.tone]}`}>{v.text}</span>;
}

function SyncCard({ title, children, todo, command, from, say }: {
  title: string; children: ReactNode; todo: boolean; command: string; from?: string; say?: { todo: string; idle: string };
}) {
  const head = `sync-${title.toLowerCase().replace(/[^a-z]+/g, '-')}`;
  return (
    <Card className={todo ? 'border-amber-500/50' : undefined}>
      <CardContent className="space-y-3 pb-4 pt-4 text-sm">
        <section aria-labelledby={head} className="space-y-3">
          <h2 id={head} className="font-serif text-lg font-semibold text-foreground">{title}</h2>
          {children}
          <div className="space-y-1.5 border-t border-border pt-3">
            <p className={todo ? 'font-medium text-amber-800 dark:text-amber-300' : 'text-xs text-muted-foreground'}>
              {todo ? (say?.todo ?? 'Not in step. Run this on the desk:') : (say?.idle ?? 'If it falls out of step, run this on the desk:')}
            </p>
            <CopyCommand command={command} from={from} />
          </div>
        </section>
      </CardContent>
    </Card>
  );
}

const NOT_REPORTED = 'The desk has not reported its sync state yet (an older desk version).';

/** The Sync tab (editors): the desk, the mirror and the pictures as the desk last reported them,
 *  and under each what to run on the desk when it is not in step. */
export function SyncPanel({ me, info, now }: { me: CornerMe; info: DeskInfo; now: number }) {
  const seen = me.worker_last_seen;
  const late = deskIsLate(seen, now);
  const every = info.sync?.every_min ?? 10;
  const round = nextRound(seen, now, every);
  const m = info.sync?.mirror ?? null;
  const d = info.sync?.media ?? null;
  const mv = m ? mirrorView(m, now) : null;
  const dv = d ? mediaView(d, now) : null;
  const b = info.budget;
  const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
  return (
    <div className="space-y-4">
      {!info.sync && (
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> {NOT_REPORTED}
        </p>
      )}
      <div className="grid gap-4 lg:grid-cols-3">
        <SyncCard
          title="The desk" todo={late} command={DESK_COMMANDS.round}
          say={{ todo: 'The desk is late. Start a round in PowerShell on the desk:', idle: 'To start a round now, run this in PowerShell on the desk:' }}
        >
          <dl className="grid grid-cols-[auto,minmax(0,1fr)] gap-x-3 gap-y-1">
            <Fact label="Last seen">{seen ? `${lastSeenText(seen, now)} (${clockTime(seen, now)})` : 'never'}</Fact>
            <Fact label="Next round">{cap(round.text)}</Fact>
            <Fact label="Rounds">every {every} minutes</Fact>
            {b && <Fact label="Spend">{spendView(b).text}{b.spent > 0 ? ` (spent $${b.spent.toFixed(2)})` : ''}</Fact>}
            {info.client && <Fact label="Desk">{info.client}{info.at ? `, reported ${clockTime(info.at, now)}` : ''}</Fact>}
          </dl>
          {late && <p className="text-xs text-muted-foreground">Approved requests wait until it is back.</p>}
        </SyncCard>
        <SyncCard title="The mirror" todo={!!mv && mv.state !== 'in_step'} command={DESK_COMMANDS.mirror} from={DESK_ROOT}>
          {!m && <p className="text-muted-foreground">{info.sync ? 'No mirror run reported yet.' : 'Not reported yet.'}</p>}
          {m && mv && (
            <dl className="grid grid-cols-[auto,minmax(0,1fr)] gap-x-3 gap-y-1">
              <Fact label="State"><StateBadge v={mv} /></Fact>
              <Fact label="Last run">{m.at ? clockTime(m.at, now) : 'not known'}</Fact>
              {(m.equal != null || m.different != null) && <Fact label="Groups">{m.equal ?? 0} equal, {m.different ?? 0} different</Fact>}
              {m.error && <Fact label="Error"><span className="font-mono text-xs">{m.error}</span></Fact>}
              {m.client && <Fact label="Client">{m.client}</Fact>}
            </dl>
          )}
        </SyncCard>
        <SyncCard title="Pictures" todo={!!dv && dv.state !== 'in_step'} command={DESK_COMMANDS.media} from={DESK_ROOT}>
          {!d && <p className="text-muted-foreground">{info.sync ? 'No pictures run reported yet.' : 'Not reported yet.'}</p>}
          {d && dv && (
            <dl className="grid grid-cols-[auto,minmax(0,1fr)] gap-x-3 gap-y-1">
              <Fact label="State"><StateBadge v={dv} /></Fact>
              <Fact label="Last run">{d.at ? clockTime(d.at, now) : 'not known'}</Fact>
              {d.files_needed != null && d.files_on_drive != null && <Fact label="On Drive">{d.files_on_drive} of {d.files_needed} files</Fact>}
              {d.pictures != null && <Fact label="Pictures">{d.pictures}</Fact>}
              {d.error && <Fact label="Error"><span className="font-mono text-xs">{d.error}</span></Fact>}
            </dl>
          )}
        </SyncCard>
      </div>
    </div>
  );
}
