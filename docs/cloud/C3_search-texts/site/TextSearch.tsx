/**
 * Search the published texts by meaning - SEARCH_TEXTS_C3A_2026_10_07.
 * Shown on /texts. Results are passages (with their reference and a link to the right page of the
 * reader), never a generated answer.
 */
import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { AlertTriangle, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { displayTranslation, passageLabel } from '@/lib/corpusDisplay';
import { MAX_QUERY, MIN_QUERY, readerHref, searchTexts } from '@/lib/corpusSearch';

const SNIPPET = 420;

export default function TextSearch({ docCodes }: { docCodes?: string[] }) {
  const [q, setQ] = useState('');
  const m = useMutation({ mutationFn: (query: string) => searchTexts(query, { k: 10, docCodes }) });
  const r = m.data;
  const ready = q.trim().length >= MIN_QUERY;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (ready && !m.isPending) m.mutate(q);
  };

  return (
    <section aria-labelledby="text-search-heading" className="mb-8">
      <Card>
        <CardContent className="pt-6">
          <h2 id="text-search-heading" className="font-serif text-lg font-semibold text-foreground">
            Search the texts by meaning
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Ask in plain English. This finds passages whose translation is closest in meaning, not only
            the same words. The passages are shown as published; nothing is written for you.
          </p>
          <form onSubmit={submit} role="search" className="mt-4 flex flex-col sm:flex-row gap-2">
            <label htmlFor="text-search-q" className="sr-only">Search the texts</label>
            <Input
              id="text-search-q"
              value={q}
              maxLength={MAX_QUERY}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. why did the king sell his wife and son?"
            />
            <Button type="submit" disabled={!ready || m.isPending} className="sm:w-32">
              {m.isPending
                ? <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />
                : <Search className="w-4 h-4 mr-2" aria-hidden="true" />}
              Search
            </Button>
          </form>

          <div aria-live="polite" className="mt-4">
            {r && !r.ok && (
              <p role="alert" className="flex items-start gap-2 text-sm text-amber-800 dark:text-amber-200">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
                <span>{r.error}</span>
              </p>
            )}
            {r && r.ok && r.rows.length === 0 && (
              <p className="text-sm text-muted-foreground">No passage of a published text matched. Try other words.</p>
            )}
            {r && r.ok && r.rows.length > 0 && (
              <ol className="space-y-4">
                {r.rows.map((h) => {
                  const t = displayTranslation(h.translation);
                  return (
                    <li key={`${h.doc_code}-${h.ref}`} className="border-b border-border pb-4 last:border-b-0">
                      <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-foreground">
                        <span className="font-serif text-sm text-foreground">{h.title}</span>
                        <span className="font-mono">{passageLabel(h)}</span>
                      </div>
                      <p lang="en" className="mt-1 font-serif text-sm leading-relaxed whitespace-pre-line text-foreground">
                        {t.length > SNIPPET ? `${t.slice(0, SNIPPET).trimEnd()}...` : t}
                      </p>
                      <Link to={readerHref(h)} className="mt-1 inline-block text-xs text-burgundy hover:underline">
                        Read it in the text
                      </Link>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
