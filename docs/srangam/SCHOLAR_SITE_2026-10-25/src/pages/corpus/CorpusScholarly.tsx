/**
 * /corpus/scholarly - every text with a scholarly English, for signed-in readers - SCHOLAR_SITE_2026_10_25.
 *
 * The desk's /scholar on the site: each text that has a scholarly English (corpus_reader_scholar_docs, docs/cloud/C22
 * in the automaton repo), how many of its verses have one, how many wait for a person, how many a person accepted,
 * the judge's mean fidelity, and two ways in: verse by verse beside the Sanskrit (the reader, at its first such
 * verse), and as prose (/corpus/<doc>/prose). Until C22 is pasted the page says so and points to the editions; a
 * refusal is a refusal, a failure a failure.
 */
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BookOpenText, Info, ScrollText } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import { displayTitle } from '@/lib/corpusDisplay';
import { functionMissing, mirrorHref, share } from '@/lib/corpusMirror';
import { loadScholarDocs, meanScore, proseHref, type ScholarDoc } from '@/lib/scholarSite';

const nf = new Intl.NumberFormat('en-IN');
const LINK = 'text-burgundy hover:underline';

function made(iso: string | null): string {
  const d = new Date(iso ?? '');
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

function DocRow({ d }: { d: ScholarDoc }) {
  const title = displayTitle(d.title, d.doc_code);
  const verses = Number(d.verses) || 0;
  const flagged = Number(d.flagged) || 0;
  const accepted = Number(d.accepted) || 0;
  const fid = meanScore(d.fidelity);
  const when = made(d.last_made);
  const first = mirrorHref({ doc_code: d.doc_code, page_no: d.first_page, idx: d.first_idx, ord: d.first_ord });
  return (
    <li className="border-b border-border py-4 last:border-b-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-serif text-lg font-semibold text-foreground">
          <Link to={proseHref(d.doc_code)} className="hover:text-burgundy">{title}</Link>
        </h2>
        <div className="flex flex-wrap gap-x-4 text-sm">
          <Link to={proseHref(d.doc_code)} className={`inline-flex items-center gap-1 font-medium ${LINK}`}>
            <BookOpenText className="h-4 w-4" aria-hidden="true" /> As prose
          </Link>
          <Link to={first} className={`inline-flex items-center gap-1 ${LINK}`}>
            <ScrollText className="h-4 w-4" aria-hidden="true" /> Verse by verse, beside the Sanskrit
          </Link>
        </div>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        {nf.format(verses)} verses in scholarly English
        {d.passages ? <> of {nf.format(Number(d.passages) || 0)} passages ({share(verses, Number(d.passages) || 0)})</> : null}
        {flagged > 0 ? <> &middot; {nf.format(flagged)} wait for a person&apos;s reading</> : null}
        {accepted > 0 ? <> &middot; {nf.format(accepted)} read by a person</> : null}
        {fid ? <> &middot; the judge&apos;s mean fidelity {fid} of 5</> : null}
        {d.category ? <> &middot; {d.category}</> : null}
        {when ? <> &middot; last made {when}</> : null}
      </p>
    </li>
  );
}

function CorpusScholarlyBody() {
  const q = useQuery({ queryKey: ['mirror', 'scholar-docs'], queryFn: loadScholarDocs, staleTime: 5 * 60 * 1000 });
  const r = q.data;
  const missing = !!r && functionMissing(r, 'corpus_reader_scholar_docs');
  const total = r?.ok ? r.rows.reduce((a, d) => a + (Number(d.verses) || 0), 0) : 0;
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Helmet><title>Scholarly English | Working Corpus | Srangam</title></Helmet>
      <CorpusNav />
      <header className="mb-6">
        <h1 className="font-serif text-3xl font-semibold text-foreground">Scholarly English</h1>
        <p className="mt-3 text-muted-foreground leading-relaxed">
          A second English beside the working one, made verse by verse in the register of an unabridged translation
          from a critical edition: every word rendered, names and terms kept and explained in notes. Each verse is drafted
          with the verses around it and the text&apos;s glossary, read by a critic and revised, and judged against the
          Sanskrit by a model of another family. Read a text as prose, as a book reads, or verse by verse beside the
          Sanskrit. A flag means a verse waits for a person&apos;s reading.
        </p>
        <p className="mt-2 flex items-start gap-2 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-indigo-dharma" aria-hidden="true" />
          <span>
            Machine translation, to be read beside the Sanskrit. The finished, judged texts are also published to
            everyone as <Link to="/editions" className={LINK}>scholarly editions</Link>.
          </span>
        </p>
      </header>

      {q.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>}

      {r && !r.ok && r.refused && <CorpusRefused message={r.error} />}
      {r && !r.ok && !r.refused && missing && (
        <Card><CardContent className="pt-6 text-sm text-muted-foreground">
          The list of texts in scholarly English is not switched on yet. Each text&apos;s scholarly English is already in
          the reader, verse by verse; the finished ones are at <Link to="/editions" className={LINK}>the editions</Link>.
        </CardContent></Card>
      )}
      {r && !r.ok && !r.refused && !missing && (
        <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
          <CardContent className="pt-6 flex items-start gap-3 text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600" aria-hidden="true" />
            <div>
              <p className="font-semibold">The texts in scholarly English could not be loaded.</p>
              <p className="text-muted-foreground mt-1">This is a loading failure, not an empty list. Please try again shortly.</p>
              {r.error && <p className="text-xs text-muted-foreground mt-2 font-mono">{r.error}</p>}
            </div>
          </CardContent>
        </Card>
      )}

      {r?.ok && r.rows.length === 0 && <p className="text-muted-foreground">No text has a scholarly English on the site yet.</p>}
      {r?.ok && r.rows.length > 0 && (
        <>
          <p className="mb-2 text-sm text-muted-foreground">
            {nf.format(r.rows.length)} {r.rows.length === 1 ? 'text' : 'texts'}, {nf.format(total)} verses in scholarly English.
          </p>
          <ul aria-label="Texts in scholarly English">
            {r.rows.map((d) => <DocRow key={d.doc_code} d={d} />)}
          </ul>
        </>
      )}
    </div>
  );
}

export default function CorpusScholarly() {
  return (
    <>
      <Helmet><meta name="robots" content="noindex, nofollow" /></Helmet>
      <CorpusGate>
        <CorpusScholarlyBody />
      </CorpusGate>
    </>
  );
}
