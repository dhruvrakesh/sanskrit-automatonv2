/**
 * /corpus/stories and /corpus/stories/:docCode/:storyId - CORPUS_LIBRARY_C6_2026_10_08.
 *
 * The stories the translation desk has drawn from the texts (scripts/stories.py): each retold in
 * English and Hindi from passages it cites, with the Sanskrit line it turns on. A reader sees the
 * APPROVED stories; an editor (admin) also sees drafts and candidates, marked as such. Approval is
 * a person's decision on the desk; the two-hourly mirror run carries it here. Every citation is a
 * link into the text (?at=page.passage).
 * CORPUS_MEDIA_C8_2026_10_09: a story's picture heads its page, with a link to its graphic novel when it has one
 * (src/components/corpus/StoryPlate.tsx; quiet when there is none).
 * CORNER_C10_MAIL_2026_10_09: the desk's bar is given the story's titles and texts, so its Edit form
 * starts from them.
 */
import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowLeft, BookMarked, CheckCircle2, ChevronLeft, ChevronRight, Info, ShieldAlert } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import StoryPlate from '@/components/corpus/StoryPlate';
import DeskActions from '@/components/corpus/DeskActions';
import {
  atHref, bookTitle, fromHref, isStory, loadStories, parseCites, parseVerify, storyHref, type LibResult, type StoryRow,
} from '@/lib/corpusLibrary';

function Problem({ r, what }: { r: LibResult<unknown>; what: string }) {
  if (r.refused) return <CorpusRefused message={r.error} />;
  if (r.missing) {
    return (
      <p className="flex items-start gap-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        The stories are not available here yet.
      </p>
    );
  }
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">{what} could not be loaded.</p>
          <p className="mt-1 text-muted-foreground">This is a loading failure. Please try again shortly.</p>
          {r.error && <p className="mt-2 font-mono text-xs text-muted-foreground">{r.error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: string | null }) {
  if (status === 'approved') return null;
  return (
    <span
      className="inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
      title="Not approved yet: editors see it, readers do not"
    >
      <ShieldAlert className="h-3 w-3" aria-hidden="true" /> {status ?? 'unreviewed'}
    </span>
  );
}

function StoryList() {
  const [search, setSearch] = useSearchParams();
  const doc = search.get('doc');
  const q = useQuery({ queryKey: ['mirror', 'stories', 'index'], queryFn: () => loadStories(null, false), staleTime: 5 * 60 * 1000 });
  const rows = useMemo(() => (q.data?.ok ? q.data.rows.filter(isStory) : []), [q.data]);
  const texts = useMemo(() => {
    const m = new Map<string, { title: string; n: number }>();
    for (const s of rows) {
      const cur = m.get(s.doc_code);
      m.set(s.doc_code, { title: cur?.title ?? bookTitle({ doc_code: s.doc_code, title: s.doc_title }).title, n: (cur?.n ?? 0) + 1 });
    }
    return [...m.entries()];
  }, [rows]);
  const shown = doc ? rows.filter((s) => s.doc_code === doc) : rows;

  return (
    <>
      <header className="mb-6">
        <h1 className="flex items-center gap-3 font-serif text-3xl font-semibold text-foreground">
          <BookMarked className="h-7 w-7 text-burgundy" aria-hidden="true" /> Stories from the texts
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          Episodes retold in English and Hindi from the passages they cite, each with the Sanskrit line it turns
          on. They are machine-written from machine translations and checked against their citations; a person
          approves each one before it appears here.
        </p>
      </header>

      {q.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /></div>}
      {q.data && !q.data.ok && <Problem r={q.data} what="The stories" />}

      {q.data?.ok && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No story has been approved yet. They appear here as they are approved on the translation desk.
        </p>
      )}

      {texts.length > 1 && (
        <div className="mb-6 flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Stories of one text">
          <button type="button" onClick={() => setSearch({})} aria-pressed={!doc}
            className={`rounded-full border px-3 py-1 ${!doc ? 'border-burgundy bg-burgundy text-white' : 'border-border text-muted-foreground hover:text-foreground'}`}>
            All texts ({rows.length})
          </button>
          {texts.map(([code, t]) => (
            <button key={code} type="button" onClick={() => setSearch({ doc: code })} aria-pressed={doc === code}
              className={`rounded-full border px-3 py-1 ${doc === code ? 'border-burgundy bg-burgundy text-white' : 'border-border text-muted-foreground hover:text-foreground'}`}>
              {t.title} ({t.n})
            </button>
          ))}
        </div>
      )}

      {shown.length > 0 && (
        <ol className="grid gap-3 sm:grid-cols-2">
          {shown.map((s) => (
            <li key={`${s.doc_code}-${s.story_id}`}>
              <Card className="h-full transition-colors hover:border-burgundy/50">
                <CardContent className="flex h-full flex-col gap-1.5 pb-4 pt-4">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{bookTitle({ doc_code: s.doc_code, title: s.doc_title }).title}</span>
                    {s.from_page != null && <span className="font-mono">{s.from_page}.{s.from_idx}{s.to_page != null ? `–${s.to_page}.${s.to_idx}` : ''}</span>}
                    <StatusBadge status={s.status} />
                  </div>
                  <Link to={storyHref(s)} className="font-serif text-lg leading-snug text-foreground hover:text-burgundy">
                    {s.title || `Story ${s.story_id}`}
                  </Link>
                  {s.title_hi && <p lang="hi" className="font-devanagari text-sm text-muted-foreground">{s.title_hi}</p>}
                  {s.quote_sa && (
                    <p lang="sa" className="mt-1 line-clamp-2 font-devanagari text-sm text-foreground/80">
                      {s.quote_sa} {s.quote_ref && <span className="font-mono text-xs text-muted-foreground">({s.quote_ref})</span>}
                    </p>
                  )}
                </CardContent>
              </Card>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

function StoryPage({ docCode, storyId }: { docCode: string; storyId: number }) {
  const [lang, setLang] = useState<'en' | 'hi' | 'both'>('both');
  const q = useQuery({
    queryKey: ['mirror', 'stories', 'doc', docCode],
    queryFn: () => loadStories(docCode, true),
    staleTime: 5 * 60 * 1000,
  });
  const rows = useMemo(() => (q.data?.ok ? q.data.rows.filter(isStory) : []), [q.data]);
  const i = rows.findIndex((s) => s.story_id === storyId);
  const s: StoryRow | undefined = rows[i];
  const prev = i > 0 ? rows[i - 1] : null;
  const next = i >= 0 && i < rows.length - 1 ? rows[i + 1] : null;
  const cites = parseCites(s?.cites);
  const v = parseVerify(s?.verify);
  const docTitle = s ? bookTitle({ doc_code: s.doc_code, title: s.doc_title }).title : docCode;

  return (
    <>
      <Helmet><title>{s?.title ? `${s.title} | Stories | Srangam` : 'Stories | Srangam'}</title></Helmet>
      <Link to={`/corpus/stories?doc=${encodeURIComponent(docCode)}`} className="mb-4 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="mr-1 h-4 w-4" aria-hidden="true" /> Stories from {docTitle}
      </Link>

      {q.isLoading && <Skeleton className="h-64 w-full" />}
      {q.data && !q.data.ok && <Problem r={q.data} what="This story" />}
      {q.data?.ok && !s && (
        <div>
          <h1 className="font-serif text-2xl font-semibold">Story not found</h1>
          <p className="mt-2 text-muted-foreground">It may not be approved yet, or it was retired.</p>
        </div>
      )}

      {s && (
        <article className="max-w-4xl">
          <header className="mb-5">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Link to={`/corpus/${encodeURIComponent(s.doc_code)}`} className="hover:text-foreground hover:underline">{docTitle}</Link>
              {s.from_page != null && (
                <Link to={fromHref(s)} className="font-mono text-burgundy hover:underline" title="Read the passages this story is drawn from">
                  {s.from_page}.{s.from_idx}{s.to_page != null ? `–${s.to_page}.${s.to_idx}` : ''}
                </Link>
              )}
              <StatusBadge status={s.status} />
            </div>
            <h1 className="mt-2 font-serif text-3xl font-semibold leading-tight text-foreground">{s.title || `Story ${s.story_id}`}</h1>
            {s.title_hi && <p lang="hi" className="mt-1 font-devanagari text-xl text-muted-foreground">{s.title_hi}</p>}
          </header>

          <StoryPlate docCode={s.doc_code} storyId={s.story_id} />
          <DeskActions target={{
            type: 'story', doc_code: s.doc_code, story_id: s.story_id, status: s.status,
            title: s.title, title_hi: s.title_hi, story_en: s.story_en, story_hi: s.story_hi,
          }} />

          {s.quote_sa && (
            <blockquote className="mb-6 border-l-4 border-burgundy/60 pl-4">
              <p lang="sa" className="whitespace-pre-line font-devanagari text-xl leading-relaxed text-foreground">{s.quote_sa}</p>
              {s.quote_ref && (
                <Link to={atHref(s.doc_code, s.quote_ref)} className="mt-1 inline-block font-mono text-xs text-burgundy hover:underline" title="This line in the text">
                  {s.quote_ref}
                </Link>
              )}
            </blockquote>
          )}

          {(s.story_en || s.story_hi) && (
            <>
              <div className="mb-3 inline-flex rounded-md border border-border p-0.5 text-sm" role="group" aria-label="Language">
                {([['both', 'Both'], ['en', 'English'], ['hi', 'Hindi']] as const).map(([k, label]) => (
                  <button key={k} type="button" aria-pressed={lang === k} onClick={() => setLang(k)}
                    className={`rounded px-3 py-1 ${lang === k ? 'bg-burgundy text-white' : 'text-muted-foreground hover:text-foreground'}`}>
                    {label}
                  </button>
                ))}
              </div>
              <div className={lang === 'both' ? 'grid gap-8 lg:grid-cols-2' : ''}>
                {lang !== 'hi' && s.story_en && <div lang="en" className="whitespace-pre-line font-serif text-lg leading-relaxed text-foreground">{s.story_en}</div>}
                {lang !== 'en' && s.story_hi && <div lang="hi" className="whitespace-pre-line font-devanagari text-lg leading-relaxed text-foreground/90">{s.story_hi}</div>}
              </div>
            </>
          )}

          {s.why && (
            <section className="mt-8 rounded-md bg-muted/50 p-4 text-sm">
              <h2 className="font-semibold text-foreground">Why this episode</h2>
              <p className="mt-1 whitespace-pre-line text-muted-foreground">{s.why}</p>
            </section>
          )}

          {cites.length > 0 && (
            <section className="mt-6">
              <h2 className="text-sm font-semibold text-foreground">The passages it cites</h2>
              <p className="mt-2 flex flex-wrap gap-1.5">
                {cites.map((c) => (
                  <Link key={c} to={atHref(s.doc_code, c)} className="rounded border border-border px-1.5 py-0.5 font-mono text-xs text-burgundy hover:border-burgundy" title={`Scan page ${c.split('.')[0]}, passage ${c.split('.')[1]}`}>
                    {c}
                  </Link>
                ))}
              </p>
            </section>
          )}

          <p className="mt-6 flex items-start gap-2 text-xs text-muted-foreground">
            {v.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" /> : <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
            <span>
              {v.ok === true && `Checked against its ${cites.length} cited passages: every citation is in the text${v.words ? `; ${v.words} words` : ''}.`}
              {v.ok === false && `The check against its citations found problems: ${v.problems.join('; ') || 'see the desk'}.`}
              {v.ok === null && 'Not checked against its citations yet.'}
              {' '}Written by {s.model ?? 'a model'} from the machine translation{s.approved_at_local ? `; approved ${s.approved_at_local.slice(0, 10)}` : ''}.
            </span>
          </p>

          <nav className="mt-8 flex justify-between gap-4 border-t border-border pt-4 text-sm" aria-label="Other stories of this text">
            {prev ? <Link to={storyHref(prev)} className="inline-flex items-center text-burgundy hover:underline"><ChevronLeft className="h-4 w-4" aria-hidden="true" />{prev.title || `Story ${prev.story_id}`}</Link> : <span />}
            {next ? <Link to={storyHref(next)} className="inline-flex items-center text-right text-burgundy hover:underline">{next.title || `Story ${next.story_id}`}<ChevronRight className="h-4 w-4" aria-hidden="true" /></Link> : <span />}
          </nav>
        </article>
      )}
    </>
  );
}

function Body() {
  const { docCode, storyId } = useParams<{ docCode?: string; storyId?: string }>();
  const id = Number.parseInt(storyId ?? '', 10);
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <CorpusNav />
      {docCode && Number.isFinite(id) ? <StoryPage docCode={docCode} storyId={id} /> : <StoryList />}
    </div>
  );
}

export default function CorpusStories() {
  return (
    <>
      <Helmet>
        <title>Stories | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
