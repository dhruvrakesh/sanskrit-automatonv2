/**
 * /admin/desk-site - the desk and the site at a glance, for the super admin - ADMIN_STATUS_2026_11_19.
 *
 * Asked on 19 Nov: "alot of the admin dashboard and landing pages need to be reimagined and rewired to reflect present
 * state of local and online deployment and linkages". The other admin pages read the articles' tables; none says what
 * the desk on the PC (the automaton) sends to this site, when it last did, whether its worker is alive, who may read
 * the working corpus, or which AI keys the site's functions used. One read-only function gathers it
 * (public.corpus_admin_status(), docs/cloud/C30 in the automaton repo): the super admin only, nothing written. The
 * page says when it was read ("as of") and reads again only when asked (Refresh) or after 10 minutes. The desk's own
 * figures (the Claude credit, its jobs) stay on the desk and are not sent here.
 */
import type { ReactNode } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Activity, AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { callMirror, functionMissing } from '@/lib/corpusMirror';

export interface IndexTable { rows: number; last_changed: string | null }
export interface AdminStatus {
  as_of: string;
  mirror: { texts: number; retired: number; last_text_synced: string | null; passages_about: number;
            translations_about: number; last_run: { started_at: string | null; finished_at: string | null } | null };
  index: Record<string, IndexTable>;
  index_run: { mark?: string; scheme?: string; checked?: string; counts?: Record<string, number> } | null;
  desk: { last_seen: string | null; queued: number; running: number; pending: number };
  access: { mode: string; since: string | null; readers_listed: number; roles: Record<string, number> };
  ai_7d?: { provider: string; model: string; ok: boolean; calls: number; last_call: string | null }[];
  ai_functions_7d?: Record<string, number>;
}
interface Loaded { ok: boolean; value: AdminStatus | null; error: string | null; refused: boolean; missing: boolean }

const FN = 'corpus_admin_status';
export const OWN_PROVIDERS = ['gemini', 'openai'];
export const DESK_LATE_MIN = 30;     // the Corner's worker reports every 10 minutes
export const MIRROR_LATE_H = 3;      // the mirror's task runs every 2 hours
const TABLES: [string, string][] = [
  ['dynasties', 'Dynasties (the lines of 17 texts)'], ['vamsas', 'Vaṃśas (the dynasties across the texts)'],
  ['persons', 'Persons of the indexes'], ['steps', 'Steps of their lines'], ['statements', 'Kinships the indexes state'],
  ['claims', 'Scholars\' claims (public domain)'], ['lines', 'Longest lines'], ['verses', 'Verses (GRETIL)'],
  ['texts', 'Indexes, texts and their credits'], ['meta', 'The desk\'s run row'],
];
const MODE: Record<string, string> = {
  signed_in: 'every signed-in person', readers: 'admins, researchers and the readers listed',
  admins: 'admins only',
};

async function loadStatus(): Promise<Loaded> {
  const r = await callMirror<{ result: AdminStatus }>(FN, {});
  if (!r.ok) return { ok: false, value: null, error: r.error ?? 'no answer', refused: r.refused, missing: functionMissing(r, FN) };
  const v = r.rows[0]?.result;
  if (!v || typeof v !== 'object') {
    return { ok: false, value: null, error: 'The status answered in an unexpected form.', refused: false, missing: false };
  }
  return { ok: true, value: v, error: null, refused: false, missing: false };
}

const nf = new Intl.NumberFormat('en-IN');
export function ago(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return 'never';
  const m = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60000));
  if (m < 1) return 'just now';
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 48 ? `${h} h ago` : `${Math.round(h / 24)} days ago`;
}
function when(iso: string | null | undefined): string {
  if (!iso) return 'never';
  return `${new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })} (${ago(iso)})`;
}
export function late(iso: string | null | undefined, minutes: number, now: Date = new Date()): boolean {
  return !iso || now.getTime() - new Date(iso).getTime() > minutes * 60000;
}

function Late({ children }: { children: ReactNode }) {
  return (
    <p className="mt-2 flex items-start gap-2 rounded border border-amber-500/40 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{children}
    </p>
  );
}

function Row({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/60 py-1.5 text-sm last:border-0">
      <dt className="text-muted-foreground">{k}</dt><dd className="text-right font-medium text-foreground">{v}</dd>
    </div>
  );
}

function Body({ s }: { s: AdminStatus }) {
  const ai = s.ai_7d ?? [];
  const other = ai.filter((x) => !OWN_PROVIDERS.includes(x.provider));
  const failed = ai.filter((x) => !x.ok).reduce((n, x) => n + x.calls, 0);
  const roles = Object.entries(s.access.roles ?? {}).sort();
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle className="text-lg">The desk (the PC)</CardTitle>
          <CardDescription>Its worker reports here every 10 minutes while the dashboard runs.</CardDescription></CardHeader>
        <CardContent>
          <dl>
            <Row k="Last seen" v={when(s.desk.last_seen)} />
            <Row k="Corner requests waiting for the desk" v={`${s.desk.queued} queued, ${s.desk.running} running`} />
            <Row k="Corner requests waiting for an editor" v={s.desk.pending} />
          </dl>
          {late(s.desk.last_seen, DESK_LATE_MIN) && <Late>The desk has not been seen for more than {DESK_LATE_MIN} minutes: is the PC on and its dashboard running?</Late>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-lg">The library mirror</CardTitle>
          <CardDescription>The texts the desk sends to the working corpus (its task runs every 2 hours).</CardDescription></CardHeader>
        <CardContent>
          <dl>
            <Row k="Texts on the site" v={nf.format(s.mirror.texts)} />
            <Row k="Texts withdrawn" v={nf.format(s.mirror.retired)} />
            <Row k="Passages" v={s.mirror.passages_about > 0 ? `about ${nf.format(s.mirror.passages_about)}` : 'not counted yet'} />
            <Row k="Translations" v={s.mirror.translations_about > 0 ? `about ${nf.format(s.mirror.translations_about)}` : 'not counted yet'} />
            <Row k="Last run of the mirror" v={when(s.mirror.last_run?.started_at)} />
            <Row k="A text last changed" v={when(s.mirror.last_text_synced)} />
          </dl>
          {late(s.mirror.last_run?.started_at, MIRROR_LATE_H * 60) && <Late>The mirror has not run for more than {MIRROR_LATE_H} hours.</Late>}
        </CardContent>
      </Card>
      <Card className="lg:col-span-2">
        <CardHeader><CardTitle className="text-lg">The genealogies the desk sends</CardTitle>
          <CardDescription>
            Sent every night, and only what changed: "last changed" is when a row last changed, not when the desk last
            looked. See them at <Link to="/corpus/genealogies" className="text-burgundy hover:underline">Genealogies</Link>,{' '}
            <Link to="/corpus/genealogies/dynasties" className="text-burgundy hover:underline">Dynasties</Link> and{' '}
            <Link to="/corpus/genealogies/vamsas" className="text-burgundy hover:underline">Sūryavaṃśa and Candravaṃśa</Link>.
          </CardDescription></CardHeader>
        <CardContent>
          <table className="w-full text-sm" aria-label="The index tables">
            <thead><tr className="text-left text-muted-foreground"><th className="py-1 font-normal">Table</th><th className="py-1 text-right font-normal">Rows</th><th className="py-1 text-right font-normal">Last changed</th></tr></thead>
            <tbody>
              {TABLES.filter(([k]) => s.index?.[k]).map(([k, label]) => (
                <tr key={k} className="border-t border-border/60">
                  <td className="py-1.5">{label}</td>
                  <td className="py-1.5 text-right font-medium">{nf.format(s.index[k].rows)}</td>
                  <td className="py-1.5 text-right">{when(s.index[k].last_changed)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {s.index_run?.mark && <p className="mt-2 text-xs text-muted-foreground">The desk's sender: {s.index_run.mark}{s.index_run.scheme ? `, scheme ${s.index_run.scheme}` : ''}.</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-lg">Who may read the working corpus</CardTitle></CardHeader>
        <CardContent>
          <dl>
            <Row k="The setting" v={MODE[s.access.mode] ?? s.access.mode} />
            <Row k="Since" v={when(s.access.since)} />
            <Row k="Readers listed" v={s.access.readers_listed} />
            {roles.map(([r, n]) => <Row key={r} k={`Role: ${r.replace('_', ' ')}`} v={n} />)}
          </dl>
          <p className="mt-2 text-sm"><Link to="/admin/researchers" className="text-burgundy hover:underline">Invite a researcher</Link></p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-lg">The site's AI calls, last 7 days</CardTitle>
          <CardDescription>Every call the site's functions made through your own keys, as the ledger has them.</CardDescription></CardHeader>
        <CardContent>
          {ai.length === 0 ? <p className="text-sm text-muted-foreground">No call in the last 7 days.</p> : (
            <table className="w-full text-sm" aria-label="The AI calls">
              <thead><tr className="text-left text-muted-foreground"><th className="py-1 font-normal">Provider and model</th><th className="py-1 text-right font-normal">Calls</th><th className="py-1 text-right font-normal">Last</th></tr></thead>
              <tbody>
                {ai.map((x) => (
                  <tr key={`${x.provider}/${x.model}/${x.ok}`} className="border-t border-border/60">
                    <td className="py-1.5">{x.provider} · {x.model}{x.ok ? '' : ' · failed'}</td>
                    <td className="py-1.5 text-right font-medium">{nf.format(x.calls)}</td>
                    <td className="py-1.5 text-right">{ago(x.last_call)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {other.length > 0 && <Late>Calls went through {other.map((x) => x.provider).join(', ')}: the site should use your own Gemini or OpenAI key. Check the keys.</Late>}
          {failed > 0 && <Late>{failed} call(s) failed in the last 7 days.</Late>}
          {s.ai_functions_7d && Object.keys(s.ai_functions_7d).length > 0 && (
            <p className="mt-2 text-xs text-muted-foreground">By function: {Object.entries(s.ai_functions_7d).sort().map(([f, n]) => `${f} ${n}`).join('; ')}.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function DeskSite() {
  const q = useQuery({ queryKey: ['admin-status'], queryFn: loadStatus, staleTime: 10 * 60 * 1000 });
  const r = q.data;
  return (
    <div className="space-y-6 p-4 sm:p-6">
      <Helmet><title>Desk and site | Admin | Srangam</title></Helmet>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-3xl font-bold tracking-tight text-foreground">
            <Activity className="h-7 w-7 text-burgundy" aria-hidden="true" /> Desk and site
          </h2>
          <p className="mt-1 max-w-3xl text-muted-foreground">
            What the desk on the PC sends to this site and when, whether its worker is alive, who may read the working
            corpus, and which AI keys the site used. Read from the site's own database; nothing is changed here. The
            desk's own figures (the Claude credit, its jobs) stay on the desk.
          </p>
          {r && r.ok && r.value && <p className="mt-1 text-sm text-muted-foreground" aria-label="As of">As of {when(r.value.as_of)}</p>}
        </div>
        <Button variant="outline" size="sm" onClick={() => q.refetch()} disabled={q.isFetching}>
          <RefreshCw className={`mr-2 h-4 w-4 ${q.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />Refresh
        </Button>
      </div>
      {q.isLoading && <div className="grid gap-4 lg:grid-cols-2" aria-busy="true"><Skeleton className="h-48" /><Skeleton className="h-48" /></div>}
      {r && !r.ok && r.refused && <p className="text-muted-foreground">Only the super admin may see the desk and the site.</p>}
      {r && !r.ok && !r.refused && r.missing && <p className="text-muted-foreground">This page is not switched on yet (docs/cloud/C30 in the automaton repo).</p>}
      {r && !r.ok && !r.refused && !r.missing && <Late>The status could not be read: {r.error}</Late>}
      {r && r.ok && r.value && <Body s={r.value} />}
    </div>
  );
}
