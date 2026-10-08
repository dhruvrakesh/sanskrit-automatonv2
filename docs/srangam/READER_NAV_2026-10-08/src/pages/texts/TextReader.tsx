/**
 * /texts/:docCode - one published text, verse by verse. TEXTS_READER_2026_09_27.
 *
 * Sanskrit (Devanagari), IAST and English, 50 passages to a page, the page in
 * the URL (?p=3) so a verse can be cited. Every query goes through
 * src/lib/corpusTexts.ts, which keeps "failed" distinct from "empty" and
 * bounds the passage query with .range().
 *
 * READER_NAV_2026_10_08: the same reading bar as /corpus/:docCode (pages, contents, what to show,
 * find in this text by meaning), the reference in the margin, the Sanskrit beside the English on
 * wide screens, misread lines marked, and the next page fetched ahead.
 */
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, ArrowLeft, Info, Loader2, Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import PassageBlock from '@/components/reader/PassageBlock';
import ReaderToolbar, { FootPager } from '@/components/reader/ReaderToolbar';
import ReaderContents, { type ContentsState } from '@/components/reader/ReaderContents';
import { loadPassageKeys, loadPassages, loadTextByDocCode } from '@/lib/corpusTexts';
import {
  PASSAGES_PER_PAGE, displayTranslation, outlineFromKeys, pageFromQuery, passageLabel, readerPageForScan,
} from '@/lib/corpusDisplay';
import { MAX_QUERY, MIN_QUERY, readerHref, searchTexts } from '@/lib/corpusSearch';
import { useReaderPrefs } from '@/lib/readerPrefs';

const nf = new Intl.NumberFormat('en-IN');
const STALE = 5 * 60 * 1000;

function Failure({ what, error }: { what: string; error: string | null }) {
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="pt-6 flex items-start gap-3 text-sm">
        <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">{what} could not be loaded.</p>
          <p className="text-muted-foreground mt-1">This is a loading failure, not missing text. Please try again shortly.</p>
          {error && <p className="text-xs text-muted-foreground mt-2 font-mono">{error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

/** Find in this text by meaning (the edge function search-texts, this text only). */
function FindInText({ docCode }: { docCode: string }) {
  const [q, setQ] = useState('');
  const [shown, setShown] = useState(false);
  const m = useMutation({ mutationFn: (query: string) => searchTexts(query, { k: 10, docCodes: [docCode] }) });
  const ready = q.trim().length >= MIN_QUERY;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!ready || m.isPending) return;
    setShown(true);
    m.mutate(q);
  };
  const r = m.data;
  return (
    <div className="relative">
      <form onSubmit={submit} role="search" aria-label="Search this text" className="flex items-center gap-1.5">
        <label htmlFor="find-in-text" className="sr-only">Find in this text by meaning</label>
        <Input
          id="find-in-text" value={q} onChange={(e) => setQ(e.target.value)} maxLength={MAX_QUERY}
          placeholder="Find in this text by meaning" className="h-9 w-full sm:w-64"
          title="Ask in plain English: this finds the passages closest in meaning, not only the same words."
        />
        <Button type="submit" size="sm" variant="outline" disabled={!ready || m.isPending} aria-label="Find">
          {m.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Search className="h-4 w-4" aria-hidden="true" />}
        </Button>
      </form>
      {shown && r && (
        <div
          className="absolute right-0 z-40 mt-2 max-h-[60vh] w-[min(36rem,calc(100vw-2rem))] overflow-y-auto rounded-md border border-border bg-popover p-3 text-sm shadow-lg"
          aria-live="polite"
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">{r.ok ? `${r.rows.length} passage${r.rows.length === 1 ? '' : 's'} closest in meaning` : ''}</p>
            <button type="button" onClick={() => setShown(false)} aria-label="Close the results" className="rounded p-0.5 text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          {!r.ok && <p role="alert" className="text-xs text-amber-800 dark:text-amber-200">{r.error}</p>}
          {r.ok && r.rows.length === 0 && <p className="text-xs text-muted-foreground">No passage matched. Try other words.</p>}
          {r.ok && r.rows.length > 0 && (
            <ol className="space-y-2">
              {r.rows.map((h) => (
                <li key={`${h.page_no}-${h.idx}`}>
                  <Link to={readerHref(h)} onClick={() => setShown(false)} className="font-mono text-xs text-burgundy hover:underline">{passageLabel(h)}</Link>
                  <span className="text-xs text-muted-foreground"> &middot; {Math.round(h.similarity * 100)}%</span>
                  <p lang="en" className="mt-0.5 font-serif text-sm text-foreground/90 line-clamp-3">{displayTranslation(h.translation)}</p>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

export default function TextReader() {
  const { docCode } = useParams<{ docCode: string }>();
  const [search, setSearch] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [prefs, setPrefs] = useReaderPrefs();
  const [contentsOpen, setContentsOpen] = useState(false);
  const [scanTarget, setScanTarget] = useState<number | null>(null);

  const textQ = useQuery({
    queryKey: ['corpus', 'text', docCode],
    queryFn: () => loadTextByDocCode(docCode),
    staleTime: STALE,
  });
  const text = textQ.data?.ok ? textQ.data.row : null;
  const total = text?.passage_count ?? 0;
  const page = pageFromQuery(search.get('p'), total);
  const lastPage = Math.max(1, Math.ceil(total / PASSAGES_PER_PAGE));

  const passQ = useQuery({
    queryKey: ['corpus', 'passages', text?.id, page],
    queryFn: () => loadPassages(text?.id, { offset: (page - 1) * PASSAGES_PER_PAGE, limit: PASSAGES_PER_PAGE }),
    enabled: !!text?.id,
    staleTime: STALE,
  });
  const passages = passQ.data;

  // READER_NAV_2026_10_08: the next page is fetched while this one is read.
  useEffect(() => {
    if (!text?.id || !passages?.ok || page >= lastPage) return;
    void qc.prefetchQuery({
      queryKey: ['corpus', 'passages', text.id, page + 1],
      queryFn: () => loadPassages(text.id, { offset: page * PASSAGES_PER_PAGE, limit: PASSAGES_PER_PAGE }),
      staleTime: STALE,
    });
  }, [text?.id, passages, page, lastPage, qc]);

  // Contents: the keys of the whole text (two integers a passage), read only when asked for.
  const [wantKeys, setWantKeys] = useState(false);
  const keysQ = useQuery({
    queryKey: ['corpus', 'keys', text?.id],
    queryFn: () => loadPassageKeys(text?.id, total),
    enabled: !!text?.id && wantKeys,
    staleTime: STALE,
  });
  const contents: ContentsState = useMemo(() => {
    const r = keysQ.data;
    if (!r) return { loading: keysQ.isFetching, error: null, pages: [], landmarks: [] };
    if (!r.ok) return { loading: false, error: r.error, pages: [], landmarks: [] };
    return { loading: false, error: null, pages: outlineFromKeys(r.rows), landmarks: [] };
  }, [keysQ.data, keysQ.isFetching]);

  const go = useCallback((p: number) => {
    setSearch(p > 1 ? { p: String(p) } : {});
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [setSearch]);

  const goPassage = (rp: number, pageNo: number, idx: number) => {
    navigate({ search: rp > 1 ? `?p=${rp}` : '', hash: `#p${pageNo}-${idx}` });
  };

  const goScan = async (scan: number): Promise<boolean> => {
    if (!text?.id) return false;
    setWantKeys(true);
    const r = await qc.fetchQuery({
      queryKey: ['corpus', 'keys', text.id],
      queryFn: () => loadPassageKeys(text.id, total),
      staleTime: STALE,
    });
    if (!r.ok) return false;
    const rp = readerPageForScan(outlineFromKeys(r.rows), scan);
    if (!rp) return false;
    setScanTarget(scan);
    if (rp !== page) go(rp);
    return true;
  };

  // SEARCH_TEXTS_C3A_2026_10_07: a link from search lands here with #p<page>-<idx>. The browser looks
  // for that anchor before the passages exist (and :target never applies to a later element), so
  // once they have arrived, scroll to it and mark it. READER_NAV_2026_10_08: also when the anchor
  // changes on the same page (a find result), and for "go to a scan page".
  const [arrived, setArrived] = useState<string | null>(null);
  useEffect(() => {
    if (!passages || !passages.ok) return;
    let el: HTMLElement | null = null;
    if (scanTarget != null) {
      const first = passages.rows.find((r) => r.page_no >= scanTarget);
      setScanTarget(null);
      if (first) el = document.getElementById(`p${first.page_no}-${first.idx}`);
    } else if (/^#p\d+-\d+$/.test(location.hash)) {
      el = document.getElementById(location.hash.slice(1));
    }
    if (!el) return;
    setArrived(el.id);
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [passages, location.hash, scanTarget]);

  return (
    <div className={`${prefs.layout === 'side' ? 'max-w-6xl' : 'max-w-3xl'} mx-auto px-4 sm:px-6 lg:px-8 py-8`}>
      <Helmet>
        <title>{text ? `${text.title} | Sanskrit Texts | Srangam` : 'Sanskrit Texts | Srangam'}</title>
        {text && (
          <meta
            name="description"
            content={`${text.title}: ${nf.format(text.passage_count)} passages in Devanagari, IAST and English, from the Srangam corpus.`}
          />
        )}
      </Helmet>

      <Link to="/texts" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4 mr-1" aria-hidden="true" /> All texts
      </Link>

      {textQ.isLoading && <Skeleton className="h-24 w-full" />}
      {textQ.data && !textQ.data.ok && <Failure what="This text" error={textQ.data.error} />}
      {textQ.data?.ok && !text && (
        <div>
          <h1 className="font-serif text-2xl font-semibold">Text not found</h1>
          <p className="text-muted-foreground mt-2">
            No published text has the code <span className="font-mono">{docCode}</span>. It may not be published yet.
          </p>
        </div>
      )}

      {text && (
        <>
          <header className="mb-4">
            <h1 className="font-serif text-3xl font-semibold text-foreground">{text.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {nf.format(text.passage_count)} passages
              {text.category ? <> &middot; {text.category}</> : null}
            </p>
            <div className="mt-2 flex items-start gap-2 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-indigo-dharma" aria-hidden="true" />
              <div className="space-y-1">
                {text.source_note && <p>{text.source_note}</p>}
                <p>
                  The English is an AI-assisted translation
                  {text.translation_engine ? <> ({text.translation_engine})</> : null}, made directly from the
                  Sanskrit and not yet reviewed by a scholar. <span className="font-mono">[ILLEGIBLE]</span> marks
                  words the scan does not show; passages from hard-to-read pages are flagged. The margin gives the
                  scan page and passage.
                </p>
              </div>
            </div>
          </header>

          <ReaderToolbar
            page={page} lastPage={lastPage} perPage={PASSAGES_PER_PAGE} total={total} go={go}
            prefs={prefs} setPrefs={setPrefs}
            onContents={() => { setWantKeys(true); setContentsOpen(true); }}
          >
            {docCode && <FindInText docCode={docCode} />}
          </ReaderToolbar>

          <ReaderContents
            open={contentsOpen} onOpenChange={setContentsOpen} title={text.title} state={contents}
            current={page} lastPage={lastPage} goPage={go} goPassage={goPassage} goScan={goScan}
          />

          {passQ.isLoading && (
            <div className="space-y-4" aria-busy="true">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {passages && !passages.ok && <Failure what="The passages" error={passages.error} />}

          {passages?.ok && (
            <ol aria-label={`Passages, page ${page}`}>
              {passages.rows.map((p) => (
                <PassageBlock key={p.id} p={p} prefs={prefs} highlighted={arrived === `p${p.page_no}-${p.idx}`} />
              ))}
            </ol>
          )}

          <FootPager page={page} lastPage={lastPage} perPage={PASSAGES_PER_PAGE} total={total} go={go} />
        </>
      )}
    </div>
  );
}
