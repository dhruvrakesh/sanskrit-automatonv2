/**
 * A search in the scholarly English - X1C_SITE_2026_10_28 (docs/cloud/C24 in the automaton repo).
 *
 * The words in the scholarly English of every text that has one, or of one of them (corpus_reader_scholar_search:
 * English stemmed, so "sacrifice" finds "sacrificed", and every word as written; live verses of live texts only), the
 * best first, each with its words marked and two ways to it: beside the Sanskrit (the reader) and in the prose. Used
 * on /corpus/scholarly and as the third way of the search on /corpus. Until C24 is pasted it says so, quietly; a
 * refusal is a refusal, a failure a failure. Nothing from the database is rendered as HTML.
 */
import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { AlertTriangle, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CorpusRefused } from '@/components/corpus/CorpusGate';
import { displayTitle, passageLabel } from '@/lib/corpusDisplay';
import { MAX_QUERY, MIN_WORDS, mirrorHref, snippetParts } from '@/lib/corpusMirror';
import { proseHref, searchScholar, type ScholarSearchResult } from '@/lib/scholarSite';

const LINK = 'text-burgundy hover:underline';

export function ScholarHits({ r }: { r: ScholarSearchResult }) {
  if (!r.ok) {
    if (r.refused) return <CorpusRefused message={r.error} />;
    if (r.missing) return <p className="text-sm text-muted-foreground">{r.error}</p>;
    return (
      <p role="alert" className="flex items-start gap-2 text-sm text-amber-800 dark:text-amber-200">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>{r.error}</span>
      </p>
    );
  }
  if (r.rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No verse of the scholarly English has these words. Try other words.</p>;
  }
  return (
    <ol className="space-y-4" aria-label="Verses of the scholarly English found">
      {r.rows.map((h) => (
        <li key={`${h.doc_code}-${h.page_no}-${h.idx}`} className="border-b border-border pb-4 last:border-b-0">
          <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-foreground">
            <span className="font-serif text-sm text-foreground">{displayTitle(h.title, h.doc_code)}</span>
            <span className="font-mono">{passageLabel(h)}</span>
          </div>
          <p lang="en" className="mt-1 whitespace-pre-line font-serif text-sm leading-relaxed text-foreground">
            {snippetParts(h.snippet).map((p, i) =>
              p.mark ? <mark key={i} className="rounded bg-amber-100 px-0.5 text-foreground dark:bg-amber-900/50">{p.text}</mark>
                     : <span key={i}>{p.text}</span>)}
          </p>
          <p className="mt-1 flex flex-wrap gap-x-4 text-xs">
            <Link to={mirrorHref(h)} className={LINK}>Beside the Sanskrit</Link>
            <Link to={proseHref(h.doc_code)} className={LINK}>The text as prose</Link>
          </p>
        </li>
      ))}
    </ol>
  );
}

export default function ScholarSearch({ docs = [] }: { docs?: { doc_code: string; title: string }[] }) {
  const [q, setQ] = useState('');
  const [doc, setDoc] = useState('');
  const m = useMutation({ mutationFn: ({ query, d }: { query: string; d: string }) => searchScholar(query, d || null) });
  const ready = q.trim().length >= MIN_WORDS;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (ready && !m.isPending) m.mutate({ query: q, d: doc });
  };
  return (
    <section aria-labelledby="scholar-search" className="mb-8">
      <h2 id="scholar-search" className="font-serif text-lg font-semibold text-foreground">Search the scholarly English</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Any form of a word (&ldquo;sacrifice&rdquo; finds &ldquo;sacrificed&rdquo;), and names as the English writes them.
      </p>
      <form onSubmit={submit} role="search" className="mt-3 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="scholar-q" className="sr-only">Search the scholarly English</label>
        <Input id="scholar-q" value={q} maxLength={MAX_QUERY} onChange={(e) => setQ(e.target.value)} placeholder="e.g. the eighth Manu" />
        {docs.length > 1 && (
          <select
            aria-label="In which text"
            value={doc}
            onChange={(e) => { setDoc(e.target.value); m.reset(); }}
            className="h-10 rounded-md border border-input bg-background px-2 text-sm sm:w-56"
          >
            <option value="">Every text</option>
            {docs.map((d) => <option key={d.doc_code} value={d.doc_code}>{displayTitle(d.title, d.doc_code)}</option>)}
          </select>
        )}
        <Button type="submit" disabled={!ready || m.isPending} className="sm:w-32">
          {m.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                       : <Search className="mr-2 h-4 w-4" aria-hidden="true" />}
          Search
        </Button>
      </form>
      <div aria-live="polite" className="mt-4">{m.data && <ScholarHits r={m.data} />}</div>
    </section>
  );
}
