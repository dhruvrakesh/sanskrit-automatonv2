/**
 * /corpus/:docCode/prose - one text's scholarly English read as prose, for signed-in readers - SCHOLAR_SITE_2026_10_25.
 *
 * The desk's /scholar/<doc>/prose on the site: chapter by chapter, as a book reads; a sentence over verses whole,
 * the verse numbers small (each a link to the verse beside its Sanskrit), a new paragraph where a speaker begins,
 * the notes at each chapter's end, a verse the judge flagged and a person has not yet read underlined. Read from the
 * mirror (corpus_reader_scholar_prose, docs/cloud/C22), PROSE_BATCH rows a call: the first chapters at once, the
 * rest as the reader nears the end (or on "Read on"). Until C22 is pasted the page says so and links the reader.
 */
import { useEffect, useMemo, useRef } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { AlertTriangle, Info, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import { displayTitle } from '@/lib/corpusDisplay';
import { functionMissing, loadMirrorDoc, loadMirrorScholarCount, type MirrorResult } from '@/lib/corpusMirror';
import {
  PROSE_BATCH, loadScholarProse, proseChapters, verseHref, type ProseRow, type ProseSegment, type ProseToken,
} from '@/lib/scholarSite';
import { Emphasised } from '@/components/reader/ScholarEnglish';

const nf = new Intl.NumberFormat('en-IN');
const LINK = 'text-burgundy hover:underline';
const STALE = 5 * 60 * 1000;

function Tokens({ tokens, chapter }: { tokens: ProseToken[]; chapter: string }) {
  return (
    <>
      {tokens.map((t, i) => {
        if ('note' in t) {
          return (
            <sup key={i} className="mx-px text-[0.7em]">
              <a href={`#${chapter}-n${t.note}`} id={`${chapter}-r${t.note}`} className={LINK} aria-label={`Note ${t.note}`}>{t.note}</a>
            </sup>
          );
        }
        return t.em ? <em key={i}>{t.text}</em> : <span key={i}>{t.text}</span>;
      })}
    </>
  );
}

function Segment({ s, docCode, chapter }: { s: ProseSegment; docCode: string; chapter: string }) {
  const body = (
    <>
      {s.label && (
        <Link
          to={verseHref(docCode, s.page, s.idx)}
          className="mr-1 align-super font-mono text-[0.62rem] text-muted-foreground no-underline hover:text-burgundy"
          title="This verse beside its Sanskrit"
        >
          {s.label}
        </Link>
      )}
      <Tokens tokens={s.tokens} chapter={chapter} />
    </>
  );
  return (
    <span id={s.id} data-flag={s.flag ? 'true' : undefined}>
      {s.flag ? (
        <span className="underline decoration-amber-500 decoration-dotted underline-offset-4" title={s.title}>{body}</span>
      ) : body}{' '}
    </span>
  );
}

function Failure({ what, r }: { what: string; r: MirrorResult<unknown> }) {
  if (r.refused) return <CorpusRefused message={r.error} />;
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="pt-6 flex items-start gap-3 text-sm">
        <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">{what} could not be loaded.</p>
          <p className="text-muted-foreground mt-1">This is a loading failure, not missing text. Please try again shortly.</p>
          {r.error && <p className="text-xs text-muted-foreground mt-2 font-mono">{r.error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function CorpusProseBody() {
  const { docCode = '' } = useParams<{ docCode: string }>();
  const docQ = useQuery({ queryKey: ['mirror', 'doc', docCode], queryFn: () => loadMirrorDoc(docCode), staleTime: STALE });
  const doc = docQ.data?.ok ? docQ.data.rows[0] ?? null : null;
  const countQ = useQuery({
    queryKey: ['mirror', 'scholarcount', docCode], queryFn: () => loadMirrorScholarCount(docCode),
    enabled: !!doc, staleTime: 10 * 60 * 1000,
  });
  const count = countQ.data?.ok ? countQ.data.rows[0] ?? null : null;
  const verses = Number(count?.verses ?? 0) || 0;
  const flagged = Number(count?.flagged ?? 0) || 0;

  const proseQ = useInfiniteQuery({
    queryKey: ['mirror', 'scholar-prose', docCode],
    queryFn: ({ pageParam }) => loadScholarProse(docCode, pageParam as { page: number; idx: number } | null),
    initialPageParam: null as { page: number; idx: number } | null,
    getNextPageParam: (last: MirrorResult<ProseRow>) => {
      if (!last.ok || last.rows.length < PROSE_BATCH) return undefined;
      const r = last.rows[last.rows.length - 1];
      return { page: r.page_no, idx: r.idx };
    },
    enabled: !!doc,
    staleTime: STALE,
  });
  const batches = proseQ.data?.pages ?? [];
  const failed = batches.find((b) => !b.ok) ?? null;
  const rows = useMemo(() => batches.flatMap((b) => (b.ok ? b.rows : [])), [batches]);
  const chapters = useMemo(() => proseChapters(rows), [rows]);
  const missing = !!failed && functionMissing(failed, 'corpus_reader_scholar_prose');
  const shownVerses = rows.filter((r) => typeof r.scholar === 'string' && r.scholar.trim()).length;

  // The rest, as the reader nears the end of what is here (where the browser can tell); else "Read on".
  const sentinel = useRef<HTMLDivElement | null>(null);
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = proseQ;
  useEffect(() => {
    const el = sentinel.current;
    if (!el || !hasNextPage || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting) && !isFetchingNextPage) void fetchNextPage();
    }, { rootMargin: '1200px 0px' });
    io.observe(el);
    return () => io.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage, chapters.length]);

  const title = doc ? displayTitle(doc.title, doc.doc_code) : '';
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Helmet><title>{doc ? `${title}, as prose | Working Corpus | Srangam` : 'As prose | Working Corpus | Srangam'}</title></Helmet>
      <CorpusNav />

      {docQ.isLoading && <Skeleton className="h-24 w-full" />}
      {docQ.data && !docQ.data.ok && <Failure what="This text" r={docQ.data} />}
      {docQ.data?.ok && !doc && (
        <div>
          <h1 className="font-serif text-2xl font-semibold">Text not found</h1>
          <p className="text-muted-foreground mt-2">The working corpus has no text with the code <span className="font-mono">{docCode}</span>.</p>
        </div>
      )}

      {doc && (
        <>
          <header className="mb-6">
            <h1 className="font-serif text-3xl font-semibold text-foreground">{title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              The scholarly English, read as prose
              {verses > 0 ? <> &middot; {nf.format(verses)} verses</> : null}
              {flagged > 0 ? <> &middot; {nf.format(flagged)} wait for a person&apos;s reading</> : null}
              {' '}&middot; <Link to={`/corpus/${encodeURIComponent(doc.doc_code)}`} className={LINK}>verse by verse, beside the Sanskrit</Link>
              {' '}&middot; <Link to="/corpus/scholarly" className={LINK}>every text in scholarly English</Link>
            </p>
            <p className="mt-2 flex items-start gap-2 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-burgundy" aria-hidden="true" />
              <span>
                Chapter by chapter, as a book reads: a sentence that runs over verses stands whole, the small numbers are
                the verses (each opens it beside its Sanskrit), the notes are at the end of each chapter. A passage
                underlined was flagged by the judge and waits for a person&apos;s reading. Machine translation, to be read
                beside the Sanskrit.
              </span>
            </p>
            {chapters.length > 1 && (
              <nav aria-label="Chapters" className="mt-3 flex flex-wrap gap-1.5 text-xs">
                {chapters.map((c) => (
                  <a key={c.id} href={`#${c.id}`} className="rounded border border-border px-2 py-0.5 text-muted-foreground hover:text-burgundy">{c.label}</a>
                ))}
              </nav>
            )}
          </header>

          {proseQ.isLoading && (
            <div className="space-y-3" aria-busy="true"><Skeleton className="h-32 w-full" /><Skeleton className="h-32 w-full" /></div>
          )}
          {failed && missing && (
            <Card><CardContent className="pt-6 text-sm text-muted-foreground">
              Reading as prose is not switched on yet. This text&apos;s scholarly English is in{' '}
              <Link to={`/corpus/${encodeURIComponent(doc.doc_code)}`} className={LINK}>the reader</Link>, verse by verse.
            </CardContent></Card>
          )}
          {failed && !missing && <Failure what="The scholarly English" r={failed} />}
          {!proseQ.isLoading && !failed && rows.length === 0 && (
            <p className="text-muted-foreground">This text has no scholarly English on the site yet.</p>
          )}

          {chapters.map((c) => (
            <section key={c.id} id={c.id} aria-labelledby={`${c.id}-h`} className="mb-10">
              <h2 id={`${c.id}-h`} className="mb-3 font-serif text-xl font-semibold text-foreground">{c.label}</h2>
              <div lang="en" className="font-serif text-[1.05rem] leading-8 text-foreground">
                {c.paragraphs.map((p, i) => (
                  <p key={`${c.id}-p${i}`} className="mb-4">
                    {p.map((s) => <Segment key={s.id} s={s} docCode={doc.doc_code} chapter={c.id} />)}
                  </p>
                ))}
              </div>
              {c.notes.length > 0 && (
                <ol aria-label={`Notes, ${c.label}`} className="mt-4 space-y-1 border-t border-border pt-3 text-sm text-muted-foreground">
                  {c.notes.map((n) => (
                    <li key={n.n} id={`${c.id}-n${n.n}`}>
                      <a href={`#${c.id}-r${n.n}`} className={`mr-1 ${LINK}`}>{n.n}.</a>
                      <span className="font-mono text-xs">{n.ref}</span>{' '}
                      {n.anchor && <><span className="font-medium text-foreground"><Emphasised text={n.anchor} /></span>: </>}
                      <Emphasised text={n.note} />
                    </li>
                  ))}
                </ol>
              )}
            </section>
          ))}

          <div ref={sentinel} aria-hidden="true" />
          {hasNextPage && !failed && (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Button type="button" variant="outline" size="sm" onClick={() => void fetchNextPage()} disabled={isFetchingNextPage}>
                {isFetchingNextPage ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Read on
              </Button>
              {verses > 0 && <span>{nf.format(Math.min(shownVerses, verses))} of {nf.format(verses)} verses here</span>}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function CorpusProse() {
  return (
    <>
      <Helmet><meta name="robots" content="noindex, nofollow" /></Helmet>
      <CorpusGate>
        <CorpusProseBody />
      </CorpusGate>
    </>
  );
}
