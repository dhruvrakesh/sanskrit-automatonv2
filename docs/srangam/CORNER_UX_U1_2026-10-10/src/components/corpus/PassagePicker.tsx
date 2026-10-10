/**
 * Choosing passages in the text itself - CORNER_UX_U1_2026_10_10. Loaded by the Corner when a
 * researcher first opens it under "A story from passages you choose" or "A picture for a passage".
 *
 * The text, a reader page at a time (corpus_reader_page, the reader's own query, so a page read there
 * is not asked for again): each passage with its margin reference (25.7) and its first English words.
 * "From here" and "To here" (a story), or "This one" (a picture), put the reference in the form. Only a
 * translated passage can be chosen, as the desk requires. Nothing is asked of the desk here.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { PASSAGES_PER_PAGE } from '@/lib/corpusDisplay';
import { loadMirrorPage, type MirrorPassage } from '@/lib/corpusMirror';
import { firstWords, type Picked } from '@/lib/cornerGuide';

const SELECT = 'h-8 rounded-md border border-input bg-background px-2 text-sm';

export interface PassagePickerProps {
  doc: string;
  /** The text's passages in all (corpus_reader_docs), for the pages. */
  passages: number;
  mode: 'range' | 'one';
  from?: Picked | null;
  to?: Picked | null;
  at?: Picked | null;
  onPick: (which: 'from' | 'to' | 'at', p: Picked, english: string | null) => void;
  onClose: () => void;
}

const refOf = (p: Pick<MirrorPassage, 'page_no' | 'idx'>): string => `${p.page_no}.${p.idx}`;
const hasEnglish = (p: MirrorPassage): boolean => !!(p.translation ?? '').trim();
/** As corner._passage_ok (C9): a running head or front matter is not a passage the desk takes. */
const NOT_TAKEN: ReadonlySet<string> = new Set(['noise', 'frontmatter']);

export default function PassagePicker({ doc, passages, mode, from = null, to = null, at = null, onPick, onClose }: PassagePickerProps) {
  const pages = Math.max(1, Math.ceil(Math.max(0, passages) / PASSAGES_PER_PAGE));
  const startOrd = (mode === 'range' ? from?.ord : at?.ord) ?? null;
  const [page, setPage] = useState(() => (startOrd ? Math.min(pages, Math.ceil(startOrd / PASSAGES_PER_PAGE)) : 1));
  useEffect(() => { if (page > pages) setPage(pages); }, [page, pages]);
  const q = useQuery({ queryKey: ['mirror', 'page', doc, page], queryFn: () => loadMirrorPage(doc, page), staleTime: 5 * 60 * 1000 });
  const rows = useMemo(() => (q.data?.ok ? q.data.rows : []).filter((p) => p && typeof p.ord === 'number'), [q.data]);
  const first = (page - 1) * PASSAGES_PER_PAGE + 1;
  const last = Math.min(passages || first + rows.length - 1, page * PASSAGES_PER_PAGE);
  const inRange = (ord: number) => !!from && !!to && ord >= from.ord && ord <= to.ord;
  const label = mode === 'range' ? 'Choose the passages in the text' : 'Choose the passage in the text';
  return (
    <section aria-label={label} className="space-y-2 rounded-md border border-burgundy/30 bg-muted/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">
          Passages {first.toLocaleString('en-IN')} to {last.toLocaleString('en-IN')} of {passages.toLocaleString('en-IN')}
        </p>
        <div className="flex flex-wrap items-center gap-1.5">
          <Button type="button" size="sm" variant="outline" className="h-8 px-2" disabled={page <= 1} onClick={() => setPage(page - 1)}
            aria-label="Earlier passages">
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </Button>
          <select aria-label="Go to the page of the text" className={SELECT} value={page} onChange={(e) => setPage(Number(e.target.value))}>
            {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>{`${((n - 1) * PASSAGES_PER_PAGE + 1).toLocaleString('en-IN')}-${Math.min(passages, n * PASSAGES_PER_PAGE).toLocaleString('en-IN')}`}</option>
            ))}
          </select>
          <Button type="button" size="sm" variant="outline" className="h-8 px-2" disabled={page >= pages} onClick={() => setPage(page + 1)}
            aria-label="Later passages">
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button type="button" size="sm" variant="ghost" className="h-8 px-2" onClick={onClose} aria-label="Close the text">
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
      {mode === 'range' && (
        <p className="text-xs text-muted-foreground">
          Choose the first passage with &ldquo;From here&rdquo; and the last with &ldquo;To here&rdquo;; 60 passages at most.
        </p>
      )}
      {q.isLoading && <div className="space-y-2" aria-busy="true"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>}
      {q.data && !q.data.ok && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{q.data.error}</p>}
      {rows.length > 0 && (
        <ol className="max-h-96 space-y-1 overflow-y-auto pr-1">
          {rows.map((p) => {
            const ref = refOf(p);
            const words = hasEnglish(p);
            const aside = words && NOT_TAKEN.has(p.text_type ?? '');
            const en = words && !aside;
            const picked: Picked = { ref, ord: p.ord };
            const chosen = (mode === 'range' && (from?.ord === p.ord || to?.ord === p.ord)) || (mode === 'one' && at?.ord === p.ord);
            return (
              <li key={p.ord}
                className={`flex flex-wrap items-start gap-2 rounded px-2 py-1.5 text-sm ${chosen ? 'bg-burgundy/10 ring-1 ring-burgundy/40' : inRange(p.ord) ? 'bg-burgundy/5' : ''}`}>
                <span className="w-14 shrink-0 font-mono text-xs text-burgundy">{ref}</span>
                <span className={`min-w-0 flex-1 ${en ? 'text-foreground' : 'italic text-muted-foreground'}`}>
                  {words ? firstWords(p.translation) : 'Not translated yet'}
                  {aside && <span className="not-italic"> (a running head or front matter: not taken by the desk)</span>}
                </span>
                {en && mode === 'range' && (
                  <span className="flex shrink-0 gap-1">
                    <Button type="button" size="sm" variant="outline" className="h-6 px-2 text-xs" aria-label={`From here: ${ref}`}
                      onClick={() => onPick('from', picked, p.translation)}>From here</Button>
                    <Button type="button" size="sm" variant="outline" className="h-6 px-2 text-xs" aria-label={`To here: ${ref}`}
                      onClick={() => onPick('to', picked, p.translation)}>To here</Button>
                  </span>
                )}
                {en && mode === 'one' && (
                  <Button type="button" size="sm" variant="outline" className="h-6 shrink-0 px-2 text-xs" aria-label={`This one: ${ref}`}
                    onClick={() => onPick('at', picked, p.translation)}>This one</Button>
                )}
              </li>
            );
          })}
        </ol>
      )}
      {q.data?.ok && rows.length === 0 && <p className="text-sm text-muted-foreground">No passage on this page.</p>}
      <p className="text-xs">
        <Link to={page > 1 ? `/corpus/${encodeURIComponent(doc)}?p=${page}` : `/corpus/${encodeURIComponent(doc)}`}
          className="text-burgundy underline decoration-burgundy/40 underline-offset-2 hover:decoration-burgundy">
          Read this page in the reader
        </Link>
      </p>
    </section>
  );
}
