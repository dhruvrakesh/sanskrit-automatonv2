/**
 * /corpus/genealogies - the indexes' lines of descent, for signed-in readers - INDEX_SITE_2026_10_25.
 *
 * The desk's Vamsa page on the site (src/lib/indexSite.ts, docs/cloud/C21 in the automaton repo): the three indexes
 * with their counts and credits, a search by the index's own head word, and the longest lines of each index, each
 * opening on its eldest. Until C21 is pasted the page says so; before the desk's first index_sync.py --apply it
 * says that nothing has been sent; a refusal is a refusal, a failure a failure.
 * B2_SITE_2026_10_28 (docs/cloud/C23): the historians' works whose view is shown beside the steps, with their counts
 * and credits.
 */
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, GitBranch, Info, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import IndexCredits from '@/components/corpus/IndexCredits';
import {
  CAUTION, findIndexPersons, loadIndexLines, loadIndexOverview, personHref, SOURCE_SHORT,
  SOURCES, type LineRow, type Overview, type SourceInfo, type WorkInfo,
} from '@/lib/indexSite';

const nf = new Intl.NumberFormat('en-IN');
const LINK = 'text-burgundy hover:underline';
const LINES_SHOWN = 12;

function Failure({ what, error }: { what: string; error: string | null }) {
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">{what} could not be loaded.</p>
          <p className="mt-1 text-muted-foreground">This is a loading failure, not an empty list. Please try again shortly.</p>
          {error && <p className="mt-2 font-mono text-xs text-muted-foreground">{error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function SourceCard({ s }: { s: SourceInfo }) {
  return (
    <li className="rounded-lg border border-border p-4">
      <h3 className="font-serif text-base font-semibold text-foreground">{s.title}</h3>
      <p className="mt-0.5 text-xs text-muted-foreground">{s.edition}</p>
      <p className="mt-2 text-sm text-foreground/90">
        {nf.format(Number(s.persons) || 0)} persons in a line &middot; {nf.format(Number(s.steps) || 0)} steps from parent
        to child &middot; {nf.format(Number(s.statements) || 0)} relations stated &middot; {nf.format(Number(s.tied) || 0)} tied
        to our names
      </p>
    </li>
  );
}

/** B2_SITE_2026_10_28: a historian's work, as the page lists it beside the indexes. */
function WorkLine({ w }: { w: WorkInfo }) {
  return (
    <li className="text-sm text-foreground/90">
      <span className="font-serif font-semibold text-foreground">{w.title}</span>
      <span className="text-muted-foreground"> &middot; {nf.format(Number(w.claims) || 0)} claims read from the book, each beside the relations of the indexes it bears on</span>
    </li>
  );
}

function Finder({ source }: { source: string | null }) {
  const [params, setParams] = useSearchParams();
  const [text, setText] = useState(params.get('q') ?? '');
  const q = params.get('q') ?? '';
  useEffect(() => { setText(params.get('q') ?? ''); }, [params]);
  const hits = useQuery({
    queryKey: ['mirror', 'index-find', q, source],
    queryFn: () => findIndexPersons(q, source, 30),
    enabled: q.trim().length > 0,
    staleTime: 10 * 60 * 1000,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next = new URLSearchParams(params);
    if (text.trim()) next.set('q', text.trim()); else next.delete('q');
    setParams(next, { replace: true });
  };
  const r = hits.data;
  return (
    <section aria-labelledby="find-person" className="mb-8">
      <h2 id="find-person" className="mb-2 font-serif text-xl font-semibold text-foreground">Find a person</h2>
      <form onSubmit={submit} role="search" className="flex max-w-xl gap-2">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="By the index's head word: Janamejaya, Daśaratha, Yayāti"
          aria-label="A person's name, as the index writes it"
        />
        <Button type="submit"><Search className="mr-1 h-4 w-4" aria-hidden="true" /> Find</Button>
      </form>
      <p className="mt-1 text-xs text-muted-foreground">
        Diacritics are optional. The indexes number the persons who share a name (Janamejaya (II)); each is shown apart.
      </p>
      {hits.isLoading && <Skeleton className="mt-3 h-20 w-full" />}
      {r && !r.ok && r.refused && <CorpusRefused message={r.error} />}
      {r && !r.ok && !r.refused && <div className="mt-3"><Failure what="The persons" error={r.error} /></div>}
      {r?.ok && q && r.rows.length === 0 && <p className="mt-3 text-sm text-muted-foreground">No person of that name has a parent or a child in the indexes.</p>}
      {r?.ok && r.rows.length > 0 && (
        <ul className="mt-3 divide-y divide-border rounded-lg border border-border" aria-label="Persons found">
          {r.rows.map((h) => (
            <li key={`${h.source}:${h.entry}`} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-3 py-2">
              <Link to={personHref(h.source, h.entry)} className="font-serif text-foreground hover:text-burgundy">{h.head}</Link>
              <span className="text-xs text-muted-foreground">
                {SOURCE_SHORT[h.source] ?? h.source} &middot; lines run up to {h.up - 1} above and {h.down - 1} below
                {h.canonical ? <> &middot; our name {h.canonical}</> : null}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function LineItem({ l }: { l: LineRow }) {
  const heads = l.heads ?? [];
  const steps = Math.max(0, (Number(l.length) || heads.length) - 1);
  const shown = heads.length > 7 ? [...heads.slice(0, 4), '…', ...heads.slice(-2)] : heads;
  return (
    <li className="border-b border-border py-3 last:border-b-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <Link to={personHref(l.source, l.entries[0])} className="font-serif text-base text-foreground hover:text-burgundy">
          {heads[0]} &rarr; {heads[heads.length - 1]}
        </Link>
        <span className="text-xs text-muted-foreground">
          {nf.format(Number(l.length) || heads.length)} generations &middot; {nf.format(Number(l.both_steps) || 0)} of {nf.format(steps)} steps
          stated in both entries
        </span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{shown.join(' › ')}</p>
    </li>
  );
}

function Lines({ source, overview }: { source: string | null; overview: Overview }) {
  const q = useQuery({ queryKey: ['mirror', 'index-lines'], queryFn: () => loadIndexLines(null), staleTime: 10 * 60 * 1000 });
  const r = q.data;
  const bySource = useMemo(() => {
    const m: Record<string, LineRow[]> = {};
    for (const l of r?.ok ? r.rows : []) (m[l.source] ??= []).push(l);
    return m;
  }, [r]);
  const titles = Object.fromEntries(overview.sources.map((s) => [s.source, s.title]));
  return (
    <section aria-labelledby="longest-lines" className="mb-8">
      <h2 id="longest-lines" className="mb-1 font-serif text-xl font-semibold text-foreground">The longest lines</h2>
      <p className="mb-3 max-w-3xl text-sm text-muted-foreground">
        Each from a person without a parent in the index, down the child whose own line runs longest. Open one to see
        each step with what it rests on.
      </p>
      {q.isLoading && <Skeleton className="h-32 w-full" />}
      {r && !r.ok && (r.refused ? <CorpusRefused message={r.error} /> : <Failure what="The lines" error={r.error} />)}
      {r?.ok && SOURCES.filter((s) => !source || s === source).map((s) => {
        const ls = bySource[s] ?? [];
        return (
          <div key={s} className="mb-5">
            <h3 className="font-serif text-lg font-semibold text-foreground">{titles[s] ?? SOURCE_SHORT[s]}</h3>
            {ls.length === 0
              ? <p className="text-sm text-muted-foreground">No line of six generations or more in this index.</p>
              : <ul aria-label={`The longest lines of ${SOURCE_SHORT[s]}`}>{ls.slice(0, LINES_SHOWN).map((l) => <LineItem key={`${l.source}:${l.rank}`} l={l} />)}</ul>}
          </div>
        );
      })}
    </section>
  );
}

function Body() {
  const [params, setParams] = useSearchParams();
  const src = params.get('source');
  const source = src && (SOURCES as readonly string[]).includes(src) ? src : null;
  const q = useQuery({ queryKey: ['mirror', 'index-overview'], queryFn: loadIndexOverview, staleTime: 10 * 60 * 1000 });
  const r = q.data;
  const ov = r?.ok ? r.value : null;
  const empty = !!ov && ov.sources.every((s) => !Number(s.persons));
  const pick = (s: string | null) => {
    const next = new URLSearchParams(params);
    if (s) next.set('source', s); else next.delete('source');
    setParams(next, { replace: true });
  };
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Helmet><title>Genealogies | Working Corpus | Srangam</title></Helmet>
      <CorpusNav />
      <header className="mb-6">
        <h1 className="flex items-center gap-2 font-serif text-3xl font-semibold text-foreground">
          <GitBranch className="h-7 w-7 text-burgundy" aria-hidden="true" /> Genealogies
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          The lines of descent as three indexes of names state them: Dikshitar&apos;s Purāṇa Index, Sørensen&apos;s index
          to the names in the Mahābhārata, and Macdonell and Keith&apos;s Vedic Index. Each step is shown with what it
          rests on: the index&apos;s own words and references, the Sanskrit verse it cites where both names stand, the
          verses of the epics that name both, and our own passages that name both.
        </p>
        <p className="mt-2 flex max-w-3xl items-start gap-2 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-indigo-dharma" aria-hidden="true" />
          <span>
            The relations were read from the indexes by a model and each checked against the entry&apos;s own words; the
            verses were matched by machine. {CAUTION}
          </span>
        </p>
      </header>

      {q.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>}
      {r && !r.ok && r.refused && <CorpusRefused message={r.error} />}
      {r && !r.ok && !r.refused && r.missing && (
        <Card><CardContent className="pt-6 text-sm text-muted-foreground">
          The genealogies are not switched on yet. The names our texts name are at <Link to="/corpus/names" className={LINK}>Names</Link>.
        </CardContent></Card>
      )}
      {r && !r.ok && !r.refused && !r.missing && <Failure what="The genealogies" error={r.error} />}
      {ov && empty && <p className="text-muted-foreground">No genealogy has been sent from the desk yet.</p>}
      {ov && !empty && (
        <>
          <ul className="mb-6 grid gap-3 md:grid-cols-3" aria-label="The indexes">
            {[...ov.sources].sort((a, b) => (SOURCES as readonly string[]).indexOf(a.source) - (SOURCES as readonly string[]).indexOf(b.source))
              .map((s) => <SourceCard key={s.source} s={s} />)}
          </ul>
          {(ov.works ?? []).some((w) => Number(w.claims) > 0) && (
            <section aria-labelledby="historians" className="mb-6">
              <h2 id="historians" className="mb-1 font-serif text-lg font-semibold text-foreground">The historians&apos; view</h2>
              <p className="mb-2 max-w-3xl text-sm text-muted-foreground">
                Where the historian speaks of the same two persons, a step says so: he states the relation too, another
                relation of the two, or the same the other way round, with his words and page.
              </p>
              <ul aria-label="The historians">{(ov.works ?? []).filter((w) => Number(w.claims) > 0).map((w) => <WorkLine key={w.code} w={w} />)}</ul>
            </section>
          )}
          <div className="mb-6 flex flex-wrap gap-2" role="group" aria-label="Which index">
            {[null, ...SOURCES].map((s) => (
              <Button key={s ?? 'all'} size="sm" variant={source === s ? 'default' : 'outline'} aria-pressed={source === s} onClick={() => pick(s)}>
                {s ? SOURCE_SHORT[s] : 'All three'}
              </Button>
            ))}
          </div>
          <Finder source={source} />
          <Lines source={source} overview={ov} />
          <IndexCredits texts={ov.texts} works={ov.works ?? []} />
        </>
      )}
    </div>
  );
}

export default function CorpusGenealogies() {
  return (
    <>
      <Helmet><meta name="robots" content="noindex, nofollow" /></Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
