/**
 * /corpus/novels and /corpus/novels/:novelId - CORPUS_MEDIA_C8_2026_10_09.
 *
 * Graphic novels drawn on the translation desk (scripts/novel.py) from approved stories: each page
 * a picture with a caption in English and Hindi that cites the passages it retells, the lines
 * spoken (each with its citation), and the scene the artist was asked for. A reader sees APPROVED
 * novels; an editor (admin) also sees novels still being planned or drawn, marked as such.
 * Every citation is a link into the text (?at=page.passage).
 */
import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, BookImage, BookMarked, CheckCircle2, Info } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import CorpusImage from '@/components/corpus/CorpusImage';
import DeskActions from '@/components/corpus/DeskActions';
import { CitedText, GeneratedNote, MediaProblem, MediaStatus } from '@/components/corpus/MediaParts';
import { atHref, bookTitle, storyHref } from '@/lib/corpusLibrary';
import {
  isNovel, loadNovel, loadNovels, novelHref, novelPictures, parseNovelVerify, parsePlan, type NovelFull,
} from '@/lib/corpusMedia';

const NOVEL_STATUS: Record<string, string> = { plan: 'being planned', drawing: 'being drawn' };

function NovelList() {
  const [search, setSearch] = useSearchParams();
  const doc = search.get('doc');
  const q = useQuery({ queryKey: ['mirror', 'novels', 'index'], queryFn: () => loadNovels(null), staleTime: 5 * 60 * 1000 });
  const rows = useMemo(() => (q.data?.ok ? q.data.rows.filter(isNovel) : []), [q.data]);
  const texts = useMemo(() => {
    const m = new Map<string, { title: string; n: number }>();
    for (const r of rows) {
      const cur = m.get(r.doc_code);
      m.set(r.doc_code, { title: cur?.title ?? bookTitle({ doc_code: r.doc_code, title: r.doc_title }).title, n: (cur?.n ?? 0) + 1 });
    }
    return [...m.entries()];
  }, [rows]);
  const shown = doc ? rows.filter((r) => r.doc_code === doc) : rows;

  return (
    <>
      <header className="mb-6">
        <h1 className="flex items-center gap-3 font-serif text-3xl font-semibold text-foreground">
          <BookImage className="h-7 w-7 text-burgundy" aria-hidden="true" /> Graphic novels from the texts
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          Approved stories told again in pictures, page by page. Every caption cites the passages it retells and
          every spoken line cites its verse; the pictures are generated, not historical sources. A person approves
          each novel, page by page, before it appears here.
        </p>
      </header>

      {q.isLoading && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true"><Skeleton className="h-72 w-full" /><Skeleton className="h-72 w-full" /></div>}
      {q.data && !q.data.ok && <MediaProblem r={q.data} what="The graphic novels" />}
      {q.data?.ok && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No graphic novel has been approved yet. They appear here as they are approved on the translation desk.
        </p>
      )}

      {texts.length > 1 && (
        <div className="mb-6 flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Novels of one text">
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
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((n) => (
            <li key={n.novel_id}>
              <Card className="h-full overflow-hidden transition-colors hover:border-burgundy/50">
                <Link to={novelHref(n.novel_id)} aria-label={`Read ${n.title ?? 'the novel'}`}>
                  <CorpusImage sha={n.cover_sha} available={n.cover_has_thumb} width={3} height={4} alt={`The first page of ${n.title ?? 'the novel'}`} className="rounded-none" />
                </Link>
                <CardContent className="space-y-1 pb-4 pt-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{bookTitle({ doc_code: n.doc_code, title: n.doc_title }).title}</span>
                    {n.pages != null && <span>{n.pages} pages</span>}
                    {n.status !== 'approved' && <MediaStatus status={NOVEL_STATUS[n.status] ?? n.status} />}
                  </div>
                  <Link to={novelHref(n.novel_id)} className="block font-serif text-lg leading-snug text-foreground hover:text-burgundy">
                    {n.title || `Graphic novel ${n.novel_id}`}
                  </Link>
                  {n.title_hi && <p lang="hi" className="font-devanagari text-sm text-muted-foreground">{n.title_hi}</p>}
                  {n.story_id != null && (
                    <Link to={storyHref({ doc_code: n.doc_code, story_id: n.story_id })} className="inline-flex items-center gap-1 text-xs text-burgundy hover:underline">
                      <BookMarked className="h-3 w-3" aria-hidden="true" /> from the story {n.story_title ? `"${n.story_title}"` : n.story_id}
                    </Link>
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

function NovelReader({ id }: { id: number }) {
  const [lang, setLang] = useState<'en' | 'hi' | 'both'>('both');
  const q = useQuery({ queryKey: ['mirror', 'novel', id], queryFn: () => loadNovel(id), staleTime: 5 * 60 * 1000 });
  const n: NovelFull | undefined = q.data?.ok ? q.data.rows[0] : undefined;
  const plan = useMemo(() => parsePlan(n?.plan), [n]);
  const v = useMemo(() => parseNovelVerify(n?.verify), [n]);
  const pics = useMemo(() => novelPictures(n?.media), [n]);
  const docTitle = n ? bookTitle({ doc_code: n.doc_code, title: n.doc_title }).title : '';
  const title = n?.title || plan.title || `Graphic novel ${id}`;
  const young = n?.audience === 'young';
  const jump = (p: number) => document.getElementById(`page-${p}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  return (
    <>
      <Helmet><title>{n ? `${title} | Graphic novels | Srangam` : 'Graphic novels | Srangam'}</title></Helmet>
      <Link to="/corpus/novels" className="mb-4 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="mr-1 h-4 w-4" aria-hidden="true" /> All graphic novels
      </Link>
      {q.isLoading && <Skeleton className="h-96 w-full" />}
      {q.data && !q.data.ok && <MediaProblem r={q.data} what="This graphic novel" />}
      {q.data?.ok && !n && (
        <div>
          <h1 className="font-serif text-2xl font-semibold">Graphic novel not found</h1>
          <p className="mt-2 text-muted-foreground">It may not be approved yet, or it was retired.</p>
        </div>
      )}

      {n && (
        <article>
          <header className="mb-6">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Link to={`/corpus/${encodeURIComponent(n.doc_code)}`} className="hover:text-foreground hover:underline">{docTitle}</Link>
              {n.story_id != null && (
                <Link to={storyHref({ doc_code: n.doc_code, story_id: n.story_id })} className="inline-flex items-center gap-1 text-burgundy hover:underline">
                  <BookMarked className="h-3 w-3" aria-hidden="true" /> the story {n.story_title ? `"${n.story_title}"` : ''}
                </Link>
              )}
              {young && <span>for young readers</span>}
              {n.status !== 'approved' && <MediaStatus status={NOVEL_STATUS[n.status] ?? n.status} />}
            </div>
            <h1 className="mt-2 font-serif text-3xl font-semibold leading-tight text-foreground">{title}</h1>
            {(n.title_hi || plan.title_hi) && <p lang="hi" className="mt-1 font-devanagari text-xl text-muted-foreground">{n.title_hi || plan.title_hi}</p>}
          </header>

          <div className="mb-6 flex flex-wrap items-center gap-3">
            <div className="inline-flex rounded-md border border-border p-0.5 text-sm" role="group" aria-label="Language">
              {([['both', 'Both'], ['en', 'English'], ['hi', 'Hindi']] as const).map(([k, label]) => (
                <button key={k} type="button" aria-pressed={lang === k} onClick={() => setLang(k)}
                  className={`rounded px-3 py-1 ${lang === k ? 'bg-burgundy text-white' : 'text-muted-foreground hover:text-foreground'}`}>
                  {label}
                </button>
              ))}
            </div>
            {plan.pages.length > 1 && (
              <nav className="flex flex-wrap gap-1 text-xs" aria-label="Pages">
                {plan.pages.map((p) => (
                  <button key={p.n} type="button" onClick={() => jump(p.n)}
                    className="h-7 min-w-[1.75rem] rounded border border-border px-1.5 font-mono text-muted-foreground hover:border-burgundy hover:text-foreground">
                    {p.n}
                  </button>
                ))}
              </nav>
            )}
          </div>
          <DeskActions target={{ type: 'novel', doc_code: n.doc_code, novel_id: n.novel_id, status: n.status, pages: n.pages }} />

          {plan.cast.length > 0 && (
            <section className="mb-8" aria-label="The cast">
              <h2 className="mb-2 text-sm font-semibold text-foreground">The cast</h2>
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
                {plan.cast.map((c, i) => {
                  const m = pics.cast.get(i + 1);
                  return (
                    <li key={i} className="text-xs">
                      <CorpusImage sha={m?.sha256} available={!!m?.has_thumb} width={m?.width ?? 1} height={m?.height ?? 1} alt={c.name ?? 'A figure'} />
                      <p className="mt-1 font-medium text-foreground">{c.name}</p>
                      {c.look && <p className="line-clamp-3 text-muted-foreground" title={c.look}>{c.look}</p>}
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          <ol className="space-y-10">
            {plan.pages.map((p) => {
              const m = pics.pages.get(p.n);
              return (
                <li key={p.n} id={`page-${p.n}`} className="scroll-mt-20">
                  <section className="grid items-start gap-5 lg:grid-cols-2" aria-label={`Page ${p.n}`}>
                    <CorpusImage sha={m?.sha256} rendition={m?.has_display ? 'display' : 'thumb'} available={!!(m?.has_display || m?.has_thumb)}
                      width={m?.width ?? 3} height={m?.height ?? 4} alt={`Page ${p.n}: ${p.scene ?? p.caption ?? ''}`.slice(0, 300)}
                      eager={p.n <= 2} className="max-h-[85vh]" />
                    <div className="rounded-md border border-amber-200/70 bg-amber-50/40 p-4 dark:border-amber-900/50 dark:bg-amber-950/10 lg:sticky lg:top-6">
                      <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
                        <span className="font-mono">page {p.n}</span>
                        {m && <MediaStatus status={m.status} />}
                      </div>
                      <DeskActions target={{ type: 'novel', doc_code: n.doc_code, novel_id: n.novel_id, status: n.status, page: p.n, page_status: m?.status ?? null }} className="mb-3" />
                      {lang !== 'hi' && p.caption && (
                        <p className={`font-serif leading-relaxed text-foreground ${young ? 'text-xl' : 'text-lg'}`}>
                          <CitedText text={p.caption} docCode={n.doc_code} lang="en" />
                        </p>
                      )}
                      {p.speech.length > 0 && (
                        <ul className="mt-3 space-y-1">
                          {p.speech.map((s, i) => (
                            <li key={i} className="italic text-foreground/90">
                              <b className="not-italic">{s.who}:</b> &ldquo;{s.line}&rdquo;
                              {s.cite && <> <CitedText text={`[${s.cite}]`} docCode={n.doc_code} /></>}
                            </li>
                          ))}
                        </ul>
                      )}
                      {lang !== 'en' && p.caption_hi && (
                        <p className={`mt-3 font-devanagari leading-relaxed text-foreground/90 ${young ? 'text-xl' : 'text-lg'}`}>
                          <CitedText text={p.caption_hi} docCode={n.doc_code} lang="hi" />
                        </p>
                      )}
                      {p.scene && (
                        <details className="mt-3 text-xs text-muted-foreground">
                          <summary className="cursor-pointer select-none">The scene the artist was asked for</summary>
                          <p className="mt-1 whitespace-pre-line">{p.scene}</p>
                        </details>
                      )}
                    </div>
                  </section>
                </li>
              );
            })}
          </ol>
          {plan.pages.length === 0 && <p className="text-sm text-muted-foreground">This novel has no pages planned yet.</p>}

          <footer className="mt-10 space-y-3 border-t border-border pt-4">
            {v.cited.length > 0 && (
              <section>
                <h2 className="text-sm font-semibold text-foreground">The passages it retells</h2>
                <p className="mt-2 flex flex-wrap gap-1.5">
                  {v.cited.map((c) => (
                    <Link key={c} to={atHref(n.doc_code, c)} className="rounded border border-border px-1.5 py-0.5 font-mono text-xs text-burgundy hover:border-burgundy">{c}</Link>
                  ))}
                </p>
              </section>
            )}
            <p className="flex items-start gap-2 text-xs text-muted-foreground">
              {v.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" /> : <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
              <span>
                {v.ok === true && 'Checked against its citations: every caption and line cites the text.'}
                {v.ok === false && `The check against its citations found: ${v.problems.join('; ') || 'problems; see the desk'}.`}
                {v.ok === null && 'Not checked against its citations yet.'}
                {' '}Written by {n.model ?? 'a model'} from the machine translation{n.approved_at_local ? `; approved ${n.approved_at_local.slice(0, 10)}` : ''}.
              </span>
            </p>
            <GeneratedNote model={n.image_model} />
          </footer>
        </article>
      )}
    </>
  );
}

function Body() {
  const { novelId } = useParams<{ novelId?: string }>();
  const id = Number.parseInt(novelId ?? '', 10);
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <CorpusNav />
      {novelId && Number.isFinite(id) && id > 0 ? <NovelReader id={id} /> : <NovelList />}
    </div>
  );
}

export default function CorpusNovels() {
  return (
    <>
      <Helmet>
        <title>Graphic novels | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
