/**
 * /corpus/names and /corpus/names/:canonical - CORPUS_LIBRARY_C6_2026_10_08.
 *
 * The names index of the working corpus: the people, deities, places, peoples, rivers and
 * mountains the translation desk recognised in the passages (corpus.entities, corpus.mentions),
 * how often and in how many texts each is named, and, for one name, every passage that names it,
 * in reading order, with a link into the text. Machine-recognised, not reviewed.
 */
import { FormEvent, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowLeft, ChevronLeft, ChevronRight, Info, Search, Users } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import { displayTranslation, passageLabel } from '@/lib/corpusDisplay';
import { mirrorHref } from '@/lib/corpusMirror';
import {
  bookTitle, KIND_LABELS, loadName, loadNames, NAME_KINDS, nameHref, type LibResult,
} from '@/lib/corpusLibrary';

const nf = new Intl.NumberFormat('en-IN');
const PAGE = 60;
const HITS = 50;

function Problem({ r, what }: { r: LibResult<unknown>; what: string }) {
  if (r.refused) return <CorpusRefused message={r.error} />;
  if (r.missing) {
    return (
      <p className="flex items-start gap-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> The names index is not available here yet.
      </p>
    );
  }
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">{what} could not be loaded.</p>
          {r.error && <p className="mt-2 font-mono text-xs text-muted-foreground">{r.error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function Pager({ offset, size, total, go }: { offset: number; size: number; total: number; go: (o: number) => void }) {
  if (total <= size) return null;
  return (
    <nav className="my-6 flex items-center justify-between gap-4 text-sm" aria-label="More names">
      <Button variant="outline" size="sm" onClick={() => go(Math.max(0, offset - size))} disabled={offset <= 0}>
        <ChevronLeft className="mr-1 h-4 w-4" aria-hidden="true" /> Previous
      </Button>
      <span className="text-muted-foreground">{nf.format(offset + 1)}&ndash;{nf.format(Math.min(offset + size, total))} of {nf.format(total)}</span>
      <Button variant="outline" size="sm" onClick={() => go(offset + size)} disabled={offset + size >= total}>
        Next <ChevronRight className="ml-1 h-4 w-4" aria-hidden="true" />
      </Button>
    </nav>
  );
}

function NamesIndex() {
  const [search, setSearch] = useSearchParams();
  const q = search.get('q') ?? '';
  const kind = search.get('kind');
  const offset = Math.max(0, Number.parseInt(search.get('o') ?? '0', 10) || 0);
  const [draft, setDraft] = useState(q);
  const set = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(search);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v); else next.delete(k);
    }
    setSearch(next);
  };
  const res = useQuery({
    queryKey: ['mirror', 'names', q, kind, offset],
    queryFn: () => loadNames({ q, kind, k: PAGE, offset }),
    staleTime: 5 * 60 * 1000,
  });
  const r = res.data;
  const total = r?.ok && r.rows.length ? Number(r.rows[0].total) : 0;
  const submit = (e: FormEvent) => { e.preventDefault(); set({ q: draft.trim() || null, o: null }); };

  return (
    <>
      <header className="mb-6">
        <h1 className="flex items-center gap-3 font-serif text-3xl font-semibold text-foreground">
          <Users className="h-7 w-7 text-burgundy" aria-hidden="true" /> Names in the texts
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          The people, deities, places, peoples, rivers and mountains the translation desk recognised in the
          passages, and where each is named. Recognised by machine, not reviewed: a name can be missed, or two
          figures can share one.
        </p>
      </header>

      <form onSubmit={submit} role="search" aria-label="Search the names" className="mb-4 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="names-q" className="sr-only">Search the names</label>
        <Input id="names-q" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={100} placeholder="e.g. Garuda, Gaṅgā, Hariścandra" />
        <Button type="submit" className="sm:w-32"><Search className="mr-2 h-4 w-4" aria-hidden="true" /> Search</Button>
      </form>
      <div className="mb-6 flex flex-wrap gap-2 text-sm" role="group" aria-label="Kind of name">
        {[null, ...NAME_KINDS].map((k) => (
          <button key={k ?? 'all'} type="button" aria-pressed={kind === k} onClick={() => set({ kind: k, o: null })}
            className={`rounded-full border px-3 py-1 ${kind === k ? 'border-burgundy bg-burgundy text-white' : 'border-border text-muted-foreground hover:text-foreground'}`}>
            {k ? KIND_LABELS[k] : 'All names'}
          </button>
        ))}
      </div>

      {res.isLoading && <div className="space-y-2" aria-busy="true"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>}
      {r && !r.ok && <Problem r={r} what="The names" />}
      {r?.ok && r.rows.length === 0 && <p className="text-sm text-muted-foreground">No name matches. Try another spelling, or all kinds.</p>}
      {r?.ok && r.rows.length > 0 && (
        <>
          <p className="mb-3 text-xs text-muted-foreground">{nf.format(total)} names{q ? <> matching &ldquo;{q}&rdquo;</> : null}, most often named first</p>
          <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
            {r.rows.map((n) => (
              <li key={n.canonical} className="flex items-baseline justify-between gap-3 border-b border-border/60 py-1.5">
                <span className="min-w-0">
                  <Link to={nameHref(n.canonical)} className="font-serif text-foreground hover:text-burgundy" title={n.notes ?? undefined}>{n.canonical}</Link>
                  {n.kind && <span className="ml-2 text-[11px] text-muted-foreground">{n.kind}</span>}
                  {n.variants && n.variants.length > 0 && (
                    <span className="ml-2 truncate text-[11px] italic text-muted-foreground">{n.variants.slice(0, 3).join(', ')}</span>
                  )}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground" title={`${n.mentions} passages in ${n.texts} texts`}>
                  {nf.format(n.mentions)} &middot; {n.texts} {n.texts === 1 ? 'text' : 'texts'}
                </span>
              </li>
            ))}
          </ul>
          <Pager offset={offset} size={PAGE} total={total} go={(o) => set({ o: o ? String(o) : null })} />
        </>
      )}
    </>
  );
}

function NamePage({ canonical }: { canonical: string }) {
  const [offset, setOffset] = useState(0);
  const head = useQuery({
    queryKey: ['mirror', 'names', 'exact', canonical],
    queryFn: () => loadNames({ q: canonical, exact: true, k: 1 }),
    staleTime: 5 * 60 * 1000,
  });
  const hits = useQuery({
    queryKey: ['mirror', 'name', canonical, offset],
    queryFn: () => loadName(canonical, offset, HITS),
    staleTime: 5 * 60 * 1000,
  });
  const e = head.data?.ok ? head.data.rows[0] : undefined;
  const r = hits.data;
  const total = r?.ok && r.rows.length ? Number(r.rows[0].total) : 0;

  return (
    <>
      <Helmet><title>{`${canonical} | Names | Srangam`}</title></Helmet>
      <Link to="/corpus/names" className="mb-4 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="mr-1 h-4 w-4" aria-hidden="true" /> All names
      </Link>
      <header className="mb-6">
        <h1 className="font-serif text-3xl font-semibold text-foreground">{canonical}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          {e?.kind && <Badge variant="secondary">{e.kind}</Badge>}
          {e && <span>named in {nf.format(e.mentions)} passages of {e.texts} {e.texts === 1 ? 'text' : 'texts'}</span>}
        </div>
        {e?.variants && e.variants.length > 0 && <p className="mt-2 text-sm text-muted-foreground">Also written: <span className="italic">{e.variants.join(', ')}</span></p>}
        {e?.notes && <p className="mt-2 max-w-3xl text-sm leading-relaxed text-foreground/90">{e.notes}</p>}
      </header>

      {hits.isLoading && <Skeleton className="h-40 w-full" />}
      {r && !r.ok && <Problem r={r} what="The passages" />}
      {r?.ok && r.rows.length === 0 && <p className="text-sm text-muted-foreground">No passage names {canonical} at present.</p>}
      {r?.ok && r.rows.length > 0 && (
        <>
          <ol className="space-y-4">
            {r.rows.map((h) => (
              <li key={`${h.doc_code}-${h.page_no}-${h.idx}`} className="border-b border-border pb-4 last:border-b-0">
                <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-foreground">
                  <span className="font-serif text-sm text-foreground">{bookTitle({ doc_code: h.doc_code, title: h.title }).title}</span>
                  <span className="font-mono">{passageLabel(h)}</span>
                  {h.surface && h.surface !== canonical && <span>as &ldquo;{h.surface}&rdquo;</span>}
                </div>
                {h.snippet && <p lang="en" className="mt-1 font-serif text-sm leading-relaxed text-foreground">{displayTranslation(h.snippet)}</p>}
                <Link to={mirrorHref(h)} className="mt-1 inline-block text-xs text-burgundy hover:underline">Read it in the text</Link>
              </li>
            ))}
          </ol>
          <Pager offset={offset} size={HITS} total={total} go={(o) => { setOffset(o); window.scrollTo({ top: 0, behavior: 'smooth' }); }} />
        </>
      )}
    </>
  );
}

function Body() {
  const { canonical } = useParams<{ canonical?: string }>();
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <CorpusNav />
      {canonical ? <NamePage key={canonical} canonical={canonical} /> : <NamesIndex />}
    </div>
  );
}

export default function CorpusNames() {
  return (
    <>
      <Helmet>
        <title>Names | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
