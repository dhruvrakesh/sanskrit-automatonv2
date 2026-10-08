/**
 * /corpus/:docCode - one text of the working corpus, for signed-in readers. CORPUS_READER_C5_2026_10_08.
 * READER_NAV_2026_10_08: a reading bar that stays in view (pages, contents, what to show, find in
 * this text), the reference in the margin, the Sanskrit beside the translations on wide screens,
 * misread lines and scanner noise marked rather than shown as text, and the next page fetched ahead.
 *
 * 50 passages to a page, ?p=3 in the URL, #p<page>-<idx> anchors (links from search land on them).
 * For each passage, the passages nearest in meaning across the whole corpus (stored vectors; no AI call).
 */
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, ArrowLeft, Info, Loader2, Search, Sparkles, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import PassageBlock from '@/components/reader/PassageBlock';
import ReaderToolbar, { FootPager } from '@/components/reader/ReaderToolbar';
import ReaderContents, { type ContentsState } from '@/components/reader/ReaderContents';
import {
  PASSAGES_PER_PAGE, displayTitle, displayTranslation, pageFromQuery, passageLabel, readerPageForScan,
  type PageStart,
} from '@/lib/corpusDisplay';
import {
  loadMirrorDoc, loadMirrorOutline, loadMirrorPage, mirrorHref, outlineMissing, searchMirrorMeaning,
  searchMirrorWords, similarPassages, snippetParts, type MirrorOutlineRow, type MirrorPassage, type MirrorResult,
} from '@/lib/corpusMirror';
import { useReaderPrefs } from '@/lib/readerPrefs';

const nf = new Intl.NumberFormat('en-IN');
const STALE = 2 * 60 * 1000;

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

function Similar({ docCode, p }: { docCode: string; p: MirrorPassage }) {
  const q = useQuery({
    queryKey: ['mirror', 'similar', docCode, p.page_no, p.idx],
    queryFn: () => similarPassages(docCode, p.page_no, p.idx),
    staleTime: 10 * 60 * 1000,
  });
  if (q.isLoading) return <p className="text-xs text-muted-foreground"><Loader2 className="inline w-3 h-3 mr-1 animate-spin" aria-hidden="true" />Looking across the corpus...</p>;
  const r = q.data;
  if (!r) return null;
  if (!r.ok) return <p role="alert" className="text-xs text-amber-800 dark:text-amber-200">{r.error}</p>;
  if (r.rows.length === 0) return <p className="text-xs text-muted-foreground">This passage has no meaning vector yet (it is embedded after it is translated).</p>;
  return (
    <ol className="mt-2 space-y-2 border-l-2 border-border pl-3">
      {r.rows.map((h) => (
        <li key={`${h.doc_code}-${h.page_no}-${h.idx}`} className="text-xs">
          <Link to={mirrorHref(h)} className="text-burgundy hover:underline">
            {displayTitle(h.title, h.doc_code)} <span className="font-mono">{passageLabel(h)}</span>
          </Link>
          {typeof h.similarity === 'number' && <span className="text-muted-foreground"> &middot; {Math.round(h.similarity * 100)}%</span>}
          {h.snippet && <p lang="en" className="mt-0.5 font-serif text-sm text-muted-foreground line-clamp-2">{displayTranslation(h.snippet)}</p>}
        </li>
      ))}
    </ol>
  );
}

/** Find in this text: words (English and IAST) or meaning (search-corpus), this document only. */
function FindInText({ docCode }: { docCode: string }) {
  const [q, setQ] = useState('');
  const [mode, setMode] = useState<'words' | 'meaning'>('words');
  const [shown, setShown] = useState(false);
  const m = useMutation({
    mutationFn: (v: { q: string; mode: 'words' | 'meaning' }) =>
      v.mode === 'words' ? searchMirrorWords(v.q, docCode) : searchMirrorMeaning(v.q, [docCode]),
  });
  const ready = q.trim().length >= (mode === 'words' ? 2 : 3);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!ready || m.isPending) return;
    setShown(true);
    m.mutate({ q, mode });
  };
  const r = m.data;
  return (
    <div className="relative">
      <form onSubmit={submit} role="search" aria-label="Search this text" className="flex items-center gap-1.5">
        <label htmlFor="find-in-text" className="sr-only">Find in this text</label>
        <Input id="find-in-text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find in this text" className="h-9 w-full sm:w-56" maxLength={200} />
        <label htmlFor="find-mode" className="sr-only">Find by</label>
        <select
          id="find-mode"
          value={mode}
          onChange={(e) => setMode(e.target.value as 'words' | 'meaning')}
          className="h-9 rounded-md border border-input bg-background px-1.5 text-xs"
          title="Words: the English and the IAST, as written. Meaning: the passages closest in meaning."
        >
          <option value="words">words</option>
          <option value="meaning">meaning</option>
        </select>
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
            <p className="text-xs text-muted-foreground">
              {r.ok ? `${r.rows.length} passage${r.rows.length === 1 ? '' : 's'} in this text` : ''}
            </p>
            <button type="button" onClick={() => setShown(false)} aria-label="Close the results" className="rounded p-0.5 text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          {!r.ok && <p role="alert" className="text-xs text-amber-800 dark:text-amber-200">{r.error}</p>}
          {r.ok && r.rows.length === 0 && <p className="text-xs text-muted-foreground">Nothing in this text matches. Try other words, or find by meaning.</p>}
          {r.ok && r.rows.length > 0 && (
            <ol className="space-y-2">
              {r.rows.map((h) => (
                <li key={`${h.page_no}-${h.idx}`}>
                  <Link to={mirrorHref(h)} onClick={() => setShown(false)} className="font-mono text-xs text-burgundy hover:underline">{passageLabel(h)}</Link>
                  {typeof h.similarity === 'number' && <span className="text-xs text-muted-foreground"> &middot; {Math.round(h.similarity * 100)}%</span>}
                  {h.snippet && (
                    <p lang="en" className="mt-0.5 font-serif text-sm text-foreground/90 line-clamp-3">
                      {snippetParts(displayTranslation(h.snippet)).map((s, i) => (s.mark ? <mark key={i}>{s.text}</mark> : <span key={i}>{s.text}</span>))}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

const toStarts = (rows: MirrorOutlineRow[]): PageStart[] =>
  rows.filter((r) => r.kind === 'page').map((r) => ({
    reader_page: r.reader_page, page_no: r.page_no, idx: r.idx, last_page_no: r.last_page_no,
  }));

function CorpusDocBody() {
  const { docCode = '' } = useParams<{ docCode: string }>();
  const [search, setSearch] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [prefs, setPrefs] = useReaderPrefs();
  const [open, setOpen] = useState<string | null>(null);
  const [contentsOpen, setContentsOpen] = useState(false);
  const [scanTarget, setScanTarget] = useState<number | null>(null);

  const docQ = useQuery({
    queryKey: ['mirror', 'doc', docCode],
    queryFn: () => loadMirrorDoc(docCode),
    staleTime: STALE,
  });
  const doc = docQ.data?.ok ? docQ.data.rows[0] ?? null : null;
  const total = doc?.passages ?? 0;
  const page = pageFromQuery(search.get('p'), total);
  const lastPage = Math.max(1, Math.ceil(total / PASSAGES_PER_PAGE));
  const title = doc ? displayTitle(doc.title, doc.doc_code) : '';

  const passQ = useQuery({
    queryKey: ['mirror', 'page', docCode, page],
    queryFn: () => loadMirrorPage(docCode, page),
    enabled: !!doc,
    staleTime: STALE,
  });
  const passages = passQ.data;

  // The next page is fetched while this one is read, so "Next" is instant.
  useEffect(() => {
    if (!doc || !passages?.ok || page >= lastPage) return;
    void qc.prefetchQuery({
      queryKey: ['mirror', 'page', docCode, page + 1],
      queryFn: () => loadMirrorPage(docCode, page + 1),
      staleTime: STALE,
    });
  }, [doc, passages, page, lastPage, docCode, qc]);

  // Contents: read only when asked for (the panel, or a scan page to go to).
  const [wantOutline, setWantOutline] = useState(false);
  const outQ = useQuery({
    queryKey: ['mirror', 'outline', docCode],
    queryFn: () => loadMirrorOutline(docCode),
    enabled: !!doc && wantOutline,
    staleTime: 10 * 60 * 1000,
  });
  const contents: ContentsState = useMemo(() => {
    const r = outQ.data;
    if (!r) return { loading: outQ.isFetching, error: null, pages: [], landmarks: [] };
    if (!r.ok) {
      return {
        loading: false,
        error: outlineMissing(r) ? 'Scan-page ranges and chapter ends are not available yet; the pages are listed.' : r.error,
        pages: [],
        landmarks: [],
      };
    }
    return {
      loading: false,
      error: null,
      pages: toStarts(r.rows),
      landmarks: r.rows.filter((x) => x.kind === 'colophon').map((x) => ({
        reader_page: x.reader_page, page_no: x.page_no, idx: x.idx, label: displayTranslation(x.label) || 'Colophon',
      })),
    };
  }, [outQ.data, outQ.isFetching]);

  const go = useCallback((p: number) => {
    setSearch(p > 1 ? { p: String(p) } : {});
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [setSearch]);

  const goPassage = (rp: number, pageNo: number, idx: number) => {
    navigate({ search: rp > 1 ? `?p=${rp}` : '', hash: `#p${pageNo}-${idx}` });
  };

  const goScan = async (scan: number): Promise<boolean> => {
    setWantOutline(true);
    const r = await qc.fetchQuery({
      queryKey: ['mirror', 'outline', docCode],
      queryFn: () => loadMirrorOutline(docCode),
      staleTime: 10 * 60 * 1000,
    });
    if (!r.ok) return false;
    const rp = readerPageForScan(toStarts(r.rows), scan);
    if (!rp) return false;
    setScanTarget(scan);
    if (rp !== page) go(rp);
    return true;
  };

  // Arriving at a passage: from a link (#p<page>-<idx>) or from "go to a scan page". The anchor is
  // looked for before the passages exist, so once they are here, scroll to it and mark it.
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

  const anyNoise = !!(passages?.ok && passages.rows.some((p) => p.text_type === 'noise'));
  const hasHindi = (doc?.hindi ?? 0) > 0 || !!(passages?.ok && passages.rows.some((p) => p.hindi && p.hindi.trim()));

  return (
    <div className={`${prefs.layout === 'side' ? 'max-w-6xl' : 'max-w-3xl'} mx-auto px-4 sm:px-6 lg:px-8 py-8`}>
      <Helmet>
        <title>{doc ? `${title} | Working Corpus | Srangam` : 'Working Corpus | Srangam'}</title>
      </Helmet>
      <Link to="/corpus" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4 mr-1" aria-hidden="true" /> The working corpus
      </Link>

      {docQ.isLoading && <Skeleton className="h-24 w-full" />}
      {docQ.data && !docQ.data.ok && <Failure what="This text" r={docQ.data} />}
      {docQ.data?.ok && !doc && (
        <div>
          <h1 className="font-serif text-2xl font-semibold">Text not found</h1>
          <p className="text-muted-foreground mt-2">
            The working corpus has no text with the code <span className="font-mono">{docCode}</span>.
          </p>
        </div>
      )}

      {doc && (
        <>
          <header className="mb-4">
            <h1 className="font-serif text-3xl font-semibold text-foreground">{title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {nf.format(doc.passages)} passages &middot; {nf.format(doc.english)} in English
              {doc.hindi > 0 ? <> &middot; {nf.format(doc.hindi)} in Hindi</> : null}
              {doc.category ? <> &middot; {doc.category}</> : null}
              {doc.published ? <> &middot; <Link to={`/texts/${encodeURIComponent(doc.doc_code)}`} className="text-burgundy hover:underline">published reader</Link></> : null}
            </p>
            <p className="mt-2 flex items-start gap-2 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-indigo-dharma" aria-hidden="true" />
              <span>
                Working text, not reviewed: the Sanskrit as the scanner read it, and machine translations into
                English and Hindi. Passages not yet translated show the Sanskrit alone. The margin gives the scan
                page and passage; hover over anything marked for a note.
              </span>
            </p>
          </header>

          <ReaderToolbar
            page={page} lastPage={lastPage} perPage={PASSAGES_PER_PAGE} total={total} go={go}
            prefs={prefs} setPrefs={setPrefs} hindi={hasHindi} noise={anyNoise}
            onContents={() => { setWantOutline(true); setContentsOpen(true); }}
          >
            <FindInText docCode={docCode} />
          </ReaderToolbar>

          <ReaderContents
            open={contentsOpen} onOpenChange={setContentsOpen} title={title} state={contents}
            current={page} lastPage={lastPage} goPage={go} goPassage={goPassage} goScan={goScan}
          />

          {passQ.isLoading && (
            <div className="space-y-4" aria-busy="true">
              <Skeleton className="h-32 w-full" /><Skeleton className="h-32 w-full" /><Skeleton className="h-32 w-full" />
            </div>
          )}
          {passages && !passages.ok && <Failure what="The passages" r={passages} />}

          {passages?.ok && (
            <ol aria-label={`Passages, page ${page}`}>
              {passages.rows.map((p) => {
                const id = `p${p.page_no}-${p.idx}`;
                const hasEn = !!displayTranslation(p.translation);
                return (
                  <PassageBlock
                    key={id}
                    p={p}
                    prefs={prefs}
                    highlighted={arrived === id}
                    extra={hasEn ? (
                      <>
                        <button
                          type="button"
                          onClick={() => setOpen(open === id ? null : id)}
                          aria-expanded={open === id}
                          className="inline-flex items-center text-burgundy hover:underline"
                          title="Passages nearest in meaning, across the whole corpus (from stored vectors)"
                        >
                          <Sparkles className="w-3 h-3 mr-1" aria-hidden="true" />
                          {open === id ? 'Hide similar passages' : 'Similar passages in the corpus'}
                        </button>
                        {open === id && <div className="basis-full"><Similar docCode={docCode} p={p} /></div>}
                      </>
                    ) : null}
                  />
                );
              })}
            </ol>
          )}

          <FootPager page={page} lastPage={lastPage} perPage={PASSAGES_PER_PAGE} total={total} go={go} />
        </>
      )}
    </div>
  );
}

export default function CorpusDoc() {
  return (
    <>
      <Helmet><meta name="robots" content="noindex, nofollow" /></Helmet>
      <CorpusGate>
        <CorpusDocBody />
      </CorpusGate>
    </>
  );
}
