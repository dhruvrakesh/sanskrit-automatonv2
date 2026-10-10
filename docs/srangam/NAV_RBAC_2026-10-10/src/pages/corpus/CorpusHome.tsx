/**
 * /corpus - the working corpus for signed-in readers. CORPUS_READER_C5_2026_10_08.
 * CORPUS_LIBRARY_C6_2026_10_08: the library. Every text on its shelf (the desk's own shelves),
 * with its titles, series, how far it is translated, its pipeline stages (each with the desk's own
 * reason, as a tooltip), its stories, and a filter and a sort; the sections Stories and Names.
 *
 * Every document in the private mirror (not only the published ones), with its counts, and two
 * searches over all of it: by words (database full-text search, English stemmed and IAST) and by
 * meaning (the edge function search-corpus). Reads only through src/lib/corpusMirror.ts, whose
 * database functions check the reader; a refusal is shown as a refusal, a failure as a failure.
 */
import { FormEvent, useMemo, useState } from 'react';
import CorpusNav from '@/components/corpus/CorpusNav';
import LibraryShelves from '@/components/corpus/LibraryShelves';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertTriangle, Info, Layers, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import { displayTitle, passageLabel } from '@/lib/corpusDisplay';   // READER_NAV_2026_10_08: displayTitle
import {
  listMirrorDocs, MAX_QUERY, MIN_WORDS, mirrorHref, type MirrorHit, type MirrorResult,
  searchMirrorMeaning, searchMirrorWords, share, snippetParts,
} from '@/lib/corpusMirror';

const nf = new Intl.NumberFormat('en-IN');
type Mode = 'words' | 'meaning';

function Snippet({ text }: { text: string | null }) {
  return (
    <>
      {snippetParts(text).map((p, i) =>
        p.mark ? <mark key={i} className="bg-amber-100 dark:bg-amber-900/50 text-foreground rounded px-0.5">{p.text}</mark>
               : <span key={i}>{p.text}</span>)}
    </>
  );
}

function Hits({ r }: { r: MirrorResult<MirrorHit> }) {
  if (!r.ok) {
    return r.refused ? <CorpusRefused message={r.error} /> : (
      <p role="alert" className="flex items-start gap-2 text-sm text-amber-800 dark:text-amber-200">
        <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
        <span>{r.error}</span>
      </p>
    );
  }
  if (r.rows.length === 0) return <p className="text-sm text-muted-foreground">Nothing matched. Try other words.</p>;
  return (
    <ol className="space-y-4">
      {r.rows.map((h) => (
        <li key={`${h.doc_code}-${h.page_no}-${h.idx}`} className="border-b border-border pb-4 last:border-b-0">
          <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-foreground">
            <span className="font-serif text-sm text-foreground">{displayTitle(h.title, h.doc_code)}</span>
            <span className="font-mono">{passageLabel(h)}</span>
            {typeof h.similarity === 'number' && <span>meaning match {Math.round(h.similarity * 100)}%</span>}
          </div>
          <p lang="en" className="mt-1 font-serif text-sm leading-relaxed whitespace-pre-line text-foreground">
            <Snippet text={h.snippet} />
          </p>
          <Link to={mirrorHref(h)} className="mt-1 inline-block text-xs text-burgundy hover:underline">
            Read it in the corpus
          </Link>
        </li>
      ))}
    </ol>
  );
}

function CorpusSearch() {
  const [mode, setMode] = useState<Mode>('words');
  const [q, setQ] = useState('');
  const m = useMutation({
    mutationFn: ({ query, how }: { query: string; how: Mode }) =>
      how === 'words' ? searchMirrorWords(query) : searchMirrorMeaning(query),
  });
  const ready = q.trim().length >= (mode === 'words' ? MIN_WORDS : 3);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (ready && !m.isPending) m.mutate({ query: q, how: mode });
  };
  return (
    <Card className="mb-8">
      <CardContent className="pt-6">
        <h2 className="font-serif text-lg font-semibold text-foreground">Search the whole corpus</h2>
        <div className="mt-3 inline-flex rounded-md border border-border p-0.5 text-sm" role="group" aria-label="Search by">
          {(['words', 'meaning'] as Mode[]).map((x) => (
            <button
              key={x}
              type="button"
              aria-pressed={mode === x}
              onClick={() => { setMode(x); m.reset(); }}
              className={`rounded px-3 py-1 ${mode === x ? 'bg-burgundy text-white' : 'text-muted-foreground hover:text-foreground'}`}
            >
              {x === 'words' ? 'By words' : 'By meaning'}
            </button>
          ))}
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          {mode === 'words'
            ? 'Finds the words in the English (any form: "sacrifice" finds "sacrificed") and in the IAST as written.'
            : 'Ask in plain English. Finds the passages closest in meaning, across every text.'}
        </p>
        <form onSubmit={submit} role="search" className="mt-3 flex flex-col sm:flex-row gap-2">
          <label htmlFor="corpus-q" className="sr-only">Search the working corpus</label>
          <Input
            id="corpus-q"
            value={q}
            maxLength={MAX_QUERY}
            onChange={(e) => setQ(e.target.value)}
            placeholder={mode === 'words' ? 'e.g. cremation ground' : 'e.g. why did the king sell his wife and son?'}
          />
          <Button type="submit" disabled={!ready || m.isPending} className="sm:w-32">
            {m.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />
                         : <Search className="w-4 h-4 mr-2" aria-hidden="true" />}
            Search
          </Button>
        </form>
        <div aria-live="polite" className="mt-4">{m.data && <Hits r={m.data} />}</div>
      </CardContent>
    </Card>
  );
}

function CorpusHomeBody() {
  const q = useQuery({ queryKey: ['mirror', 'docs'], queryFn: listMirrorDocs, staleTime: 2 * 60 * 1000 });
  const r = q.data;
  const totals = useMemo(() => {
    const rows = r?.ok ? r.rows : [];
    const sum = (k: 'passages' | 'english' | 'hindi' | 'vectors') => rows.reduce((a, d) => a + Number(d[k] || 0), 0);
    const last = rows.reduce<string | null>((a, d) => (d.synced_at && (!a || d.synced_at > a) ? d.synced_at : a), null);
    return { docs: rows.length, passages: sum('passages'), english: sum('english'), hindi: sum('hindi'), vectors: sum('vectors'), last };
  }, [r]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <CorpusNav />
      <header className="mb-6">
        <h1 className="font-serif text-3xl font-semibold text-foreground flex items-center gap-3">
          <Layers className="w-7 h-7 text-burgundy" aria-hidden="true" />
          The working corpus
        </h1>
        <p className="mt-3 text-muted-foreground leading-relaxed max-w-3xl">
          Every text on the translation desk, as it stands today: Devanagari, IAST, the English and the
          Hindi. Published texts are also at <Link to="/texts" className="text-burgundy hover:underline">/texts</Link>.
        </p>
        {/* NAV_RBAC_2026_10_10: where to start */}
        <p className="mt-2 text-sm text-muted-foreground">
          New here? <Link to="/corpus/learn" className="text-burgundy hover:underline">Learn</Link> walks you
          through every tool in short quests; the <Link to="/corpus/corner" className="text-burgundy hover:underline">Researchers&apos; Corner</Link> is
          where you ask the desk for stories, pictures and graphic novels.
        </p>
      </header>

      <Card className="mb-6">
        <CardContent className="pt-6 flex items-start gap-3 text-sm text-muted-foreground">
          <Info className="w-5 h-5 shrink-0 text-indigo-dharma" aria-hidden="true" />
          <p>
            Nothing here has been reviewed. The Sanskrit is what the scanner read, damage included; the
            English and Hindi are machine translations made from it. The corpus follows the translation
            desk every two hours{totals.last ? <> (last update {new Date(totals.last).toLocaleString('en-IN')})</> : null}.
          </p>
        </CardContent>
      </Card>

      {r?.ok && r.rows.length > 0 && <CorpusSearch />}

      {q.isLoading && (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" />
        </div>
      )}
      {r && !r.ok && (r.refused ? <CorpusRefused message={r.error} /> : (
        <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
          <CardContent className="pt-6 flex items-start gap-3 text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600" aria-hidden="true" />
            <div>
              <p className="font-semibold">The working corpus could not be loaded.</p>
              <p className="text-muted-foreground mt-1">This is a loading failure, not an empty corpus. Please try again shortly.</p>
              <p className="text-xs text-muted-foreground mt-2 font-mono">{r.error}</p>
            </div>
          </CardContent>
        </Card>
      ))}

      {r?.ok && (
        <>
          <p className="mb-4 text-sm text-muted-foreground">
            {nf.format(totals.docs)} texts &middot; {nf.format(totals.passages)} passages &middot;{' '}
            {nf.format(totals.english)} in English ({share(totals.english, totals.passages)}) &middot;{' '}
            {nf.format(totals.hindi)} in Hindi &middot; {nf.format(totals.vectors)} searchable by meaning
          </p>
          <LibraryShelves docs={r.rows} />
        </>
      )}
    </div>
  );
}

export default function CorpusHome() {
  return (
    <>
      <Helmet>
        <title>Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <CorpusHomeBody />
      </CorpusGate>
    </>
  );
}
