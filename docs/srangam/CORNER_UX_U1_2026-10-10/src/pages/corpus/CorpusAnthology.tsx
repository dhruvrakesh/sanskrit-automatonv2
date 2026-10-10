/**
 * /corpus/anthologies/new and /corpus/anthologies/:collectionId - CORNER_C9_2026_10_09.
 *
 * An anthology: approved stories gathered from any of the texts, in the order its maker chose,
 * with a title and an introduction. Readers of the working corpus read the published ones; a
 * researcher keeps drafts of their own; editors publish them (corner_collection_publish). Each
 * story is shown with its picture, the Sanskrit line it turns on and the passages it is drawn
 * from, every one a link into the text. "Print or save as PDF" prints the anthology alone, one
 * story to a page. ?edit=1 opens the builder for whoever may change it (can_edit).
 */
import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowDown, ArrowLeft, ArrowUp, BookOpen, Pencil, Plus, Printer, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import CorpusGate from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import CorpusImage from '@/components/corpus/CorpusImage';
import { ActionNote, CornerClosed, CornerProblem } from '@/components/corpus/CornerParts';
import { GeneratedNote, MediaStatus } from '@/components/corpus/MediaParts';
import { atHref, bookTitle, isStory, loadStories, storyHref, type StoryRow } from '@/lib/corpusLibrary';
import {
  AUDIENCE_LABEL, AUDIENCES, collectionItems, CORNER_KEY, loadCollection, loadMe, publishCollection, retireCollection,
  saveCollection, type Audience, type CollectionFull, type CollectionItem, type CornerMe,
} from '@/lib/corner';

const KEY = CORNER_KEY;
const SELECT = 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm';
/** The site's own header, footer and bottom bar are left out of the printed anthology. */
const PRINT_CSS = '@media print { header.sticky, body footer, nav.fixed { display: none !important; } main { padding: 0 !important; } }';

function useMe() {
  return useQuery({ queryKey: [...KEY, 'me'], queryFn: loadMe, staleTime: 60 * 1000 });
}

const range = (it: Pick<CollectionItem, 'from_page' | 'from_idx' | 'to_page' | 'to_idx'>) =>
  it.from_page == null ? null : `${it.from_page}.${it.from_idx}${it.to_page != null ? `-${it.to_page}.${it.to_idx}` : ''}`;

// ---- reading --------------------------------------------------------------------------------

function StorySection({ it, first, lang }: { it: CollectionItem; first: boolean; lang: 'both' | 'en' | 'hi' }) {
  const doc = bookTitle({ doc_code: it.doc_code, title: it.doc_title }).title;
  const pic = it.picture;
  const r = range(it);
  const title = it.title || `Story ${it.story_id}`;
  return (
    <section aria-label={title} className={`border-t border-border pt-8 ${first ? '' : 'print:break-before-page'} print:border-0 print:pt-0`}>
      {pic && (
        <figure className="mb-5 max-w-3xl print:max-w-none">
          <CorpusImage sha={pic.sha256} rendition={pic.has_display ? 'display' : 'thumb'} available={pic.has_display || pic.has_thumb}
            width={pic.width} height={pic.height} alt={pic.caption_en ?? title} eager={first} className="print:max-h-[55vh]" />
          <figcaption className="mt-2 space-y-1 text-sm">
            <span className="flex flex-wrap items-center gap-2">
              {pic.caption_en && <span className="font-serif text-foreground">{pic.caption_en}</span>}
              <MediaStatus status={pic.status} />
            </span>
            {pic.caption_hi && lang !== 'en' && <span lang="hi" className="block font-devanagari text-foreground/90">{pic.caption_hi}</span>}
            <GeneratedNote model={pic.model} />
          </figcaption>
        </figure>
      )}
      <h2 className="flex flex-wrap items-center gap-2 font-serif text-2xl font-semibold leading-tight text-foreground">
        <span>{title}</span><MediaStatus status={it.status} />
      </h2>
      {it.title_hi && <p lang="hi" className="mt-1 font-devanagari text-lg text-muted-foreground">{it.title_hi}</p>}

      {it.quote_sa && (
        <blockquote className="my-5 border-l-4 border-burgundy/60 pl-4">
          <p lang="sa" className="whitespace-pre-line font-devanagari text-xl leading-relaxed text-foreground">{it.quote_sa}</p>
          {it.quote_ref && (
            <Link to={atHref(it.doc_code, it.quote_ref)} className="mt-1 inline-block font-mono text-xs text-burgundy hover:underline" title="This line in the text">
              {it.quote_ref}
            </Link>
          )}
        </blockquote>
      )}

      <div className={lang === 'both' ? 'grid gap-8 lg:grid-cols-2 print:block' : ''}>
        {lang !== 'hi' && it.story_en && <div lang="en" className="whitespace-pre-line font-serif text-lg leading-relaxed text-foreground">{it.story_en}</div>}
        {lang !== 'en' && it.story_hi && <div lang="hi" className="whitespace-pre-line font-devanagari text-lg leading-relaxed text-foreground/90 print:mt-6">{it.story_hi}</div>}
      </div>

      <p className="mt-4 text-sm text-muted-foreground">
        From{' '}
        {r && it.from_page != null ? (
          <Link to={atHref(it.doc_code, `${it.from_page}.${it.from_idx}`)} className="text-burgundy hover:underline">{doc}, passages {r}</Link>
        ) : (
          <Link to={`/corpus/${encodeURIComponent(it.doc_code)}`} className="text-burgundy hover:underline">{doc}</Link>
        )}
        <span className="print:hidden">
          {' '}· <Link to={storyHref(it)} className="hover:text-foreground hover:underline">the story in the corpus</Link>
        </span>
        {it.model && <span>. Written by {it.model} from the machine translation and checked against its citations.</span>}
      </p>
    </section>
  );
}

function Reader({ id, me }: { id: number; me: CornerMe | undefined }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [lang, setLang] = useState<'both' | 'en' | 'hi'>('both');
  const [armed, setArmed] = useState(false);
  const q = useQuery({ queryKey: [...KEY, 'collection', id], queryFn: () => loadCollection(id), staleTime: 60 * 1000 });
  const c: CollectionFull | undefined = q.data?.ok ? q.data.rows[0] : undefined;
  const items = useMemo(() => collectionItems(c?.items), [c]);
  const editor = !!me?.is_editor;
  const publish = useMutation({
    mutationFn: (on: boolean) => publishCollection(id, on),
    onSuccess: (r) => { if (r.ok) void qc.invalidateQueries({ queryKey: KEY }); },
  });
  const retire = useMutation({
    mutationFn: () => retireCollection(id),
    onSuccess: (r) => {
      setArmed(false);
      if (r.ok) {
        void qc.invalidateQueries({ queryKey: KEY });
        navigate('/corpus/corner?tab=anthologies');
      }
    },
  });
  const said = publish.data ?? retire.data;

  return (
    <>
      <Helmet>
        <title>{c ? `${c.title} | Anthologies | Srangam` : 'Anthologies | Srangam'}</title>
        <style>{PRINT_CSS}</style>
      </Helmet>
      <Link to="/corpus/corner?tab=anthologies" className="mb-4 inline-flex items-center text-sm text-muted-foreground hover:text-foreground print:hidden">
        <ArrowLeft className="mr-1 h-4 w-4" aria-hidden="true" /> The Researchers&apos; Corner
      </Link>
      {q.isLoading && <Skeleton className="h-96 w-full" />}
      {q.data && !q.data.ok && <CornerProblem r={q.data} what="This anthology" />}
      {q.data?.ok && !c && (
        <div>
          <h1 className="font-serif text-2xl font-semibold">Anthology not found</h1>
          <p className="mt-2 text-muted-foreground">It may not be published yet, or it was retired.</p>
        </div>
      )}

      {c && (
        <article className="max-w-4xl print:max-w-none">
          <header className="mb-6">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>An anthology from the working corpus</span>
              {AUDIENCE_LABEL[c.audience] && <span>{AUDIENCE_LABEL[c.audience]}</span>}
              <span>{items.length} {items.length === 1 ? 'story' : 'stories'}</span>
              {c.status !== 'published' && <MediaStatus status={c.status} />}
            </div>
            <h1 className="mt-2 font-serif text-4xl font-semibold leading-tight text-foreground">{c.title}</h1>
            {c.title_hi && <p lang="hi" className="mt-1 font-devanagari text-2xl text-muted-foreground">{c.title_hi}</p>}
            {c.intro && <p className="mt-4 max-w-3xl whitespace-pre-line font-serif text-lg leading-relaxed text-foreground/90">{c.intro}</p>}
          </header>

          <div className="mb-8 flex flex-wrap items-center gap-3 print:hidden">
            <div className="inline-flex rounded-md border border-border p-0.5 text-sm" role="group" aria-label="Language">
              {([['both', 'Both'], ['en', 'English'], ['hi', 'Hindi']] as const).map(([k, label]) => (
                <button key={k} type="button" aria-pressed={lang === k} onClick={() => setLang(k)}
                  className={`rounded px-3 py-1 ${lang === k ? 'bg-burgundy text-white' : 'text-muted-foreground hover:text-foreground'}`}>
                  {label}
                </button>
              ))}
            </div>
            <Button type="button" size="sm" variant="outline" onClick={() => window.print()}>
              <Printer className="h-4 w-4" aria-hidden="true" /> Print or save as PDF
            </Button>
            {c.can_edit && (
              <Link to="?edit=1" className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border px-3 text-sm hover:border-burgundy hover:text-burgundy">
                <Pencil className="h-4 w-4" aria-hidden="true" /> Edit
              </Link>
            )}
            {editor && c.status === 'draft' && (
              <Button type="button" size="sm" disabled={publish.isPending} onClick={() => publish.mutate(true)} className="bg-burgundy text-white hover:bg-burgundy/90">Publish</Button>
            )}
            {editor && c.status === 'published' && (
              <Button type="button" size="sm" variant="outline" disabled={publish.isPending} onClick={() => publish.mutate(false)}>Unpublish</Button>
            )}
            {c.can_edit && (
              <>
                <Button type="button" size="sm" variant="outline" disabled={retire.isPending} aria-pressed={armed}
                  onClick={() => (armed ? retire.mutate() : setArmed(true))}
                  className={armed ? 'border-red-600 text-red-700 dark:text-red-300' : ''}>
                  {armed ? 'Click again to retire it' : 'Retire'}
                </Button>
                {armed && <button type="button" onClick={() => setArmed(false)} className="text-sm text-muted-foreground hover:underline">Keep it</button>}
              </>
            )}
          </div>
          {said && <div className="mb-6 print:hidden"><ActionNote ok={said.ok} text={said.ok ? said.rows[0]?.message : said.error} /></div>}

          {items.length === 0 && <p className="text-sm text-muted-foreground">This anthology has no story yet.</p>}
          <div className="space-y-10">
            {items.map((it, i) => <StorySection key={`${it.doc_code}-${it.story_id}`} it={it} first={i === 0} lang={lang} />)}
          </div>
        </article>
      )}
    </>
  );
}

// ---- making ---------------------------------------------------------------------------------

interface Chosen { doc_code: string; story_id: number; title: string | null; doc_title: string | null; status: string | null }

const keyOf = (s: { doc_code: string; story_id: number }) => `${s.doc_code}:${s.story_id}`;

function Builder({ me, start }: { me: CornerMe; start: { id: number | null; title: string; title_hi: string; intro: string; audience: Audience; items: Chosen[] } }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [title, setTitle] = useState(start.title);
  const [titleHi, setTitleHi] = useState(start.title_hi);
  const [intro, setIntro] = useState(start.intro);
  const [audience, setAudience] = useState<Audience>(start.audience);
  const [chosen, setChosen] = useState<Chosen[]>(start.items);
  const [filter, setFilter] = useState('');
  const stories = useQuery({ queryKey: ['mirror', 'stories', 'index'], queryFn: () => loadStories(null, false), staleTime: 5 * 60 * 1000 });
  const save = useMutation({
    mutationFn: () => saveCollection({ id: start.id, title, title_hi: titleHi, intro, audience, items: chosen }),
    onSuccess: (r) => {
      if (!r.ok) return;
      void qc.invalidateQueries({ queryKey: KEY });
      const id = r.rows[0]?.collection_id ?? start.id;
      if (id) navigate(`/corpus/anthologies/${id}`);
    },
  });

  const have = new Set(chosen.map(keyOf));
  // CORNER_UX_U1_2026_10_10: a researcher's anthology holds approved stories only (corner_collection_save
  // refuses any other from her), so once C13 shows her the drafts they are still not offered here.
  const editor = me.is_editor;
  const pool = useMemo(() => (stories.data?.ok ? stories.data.rows.filter(isStory) : [])
    .filter((s: StoryRow) => s.status !== 'candidate' && s.status !== 'retired' && s.status !== 'rejected')
    .filter((s: StoryRow) => editor || s.status === 'approved'), [stories.data, editor]);
  const groups = useMemo(() => {
    const f = filter.trim().toLowerCase();
    const m = new Map<string, { title: string; rows: StoryRow[] }>();
    for (const s of pool) {
      const doc = bookTitle({ doc_code: s.doc_code, title: s.doc_title }).title;
      if (f && !`${s.title ?? ''} ${s.title_hi ?? ''} ${doc}`.toLowerCase().includes(f)) continue;
      const g = m.get(s.doc_code) ?? { title: doc, rows: [] };
      g.rows.push(s);
      m.set(s.doc_code, g);
    }
    return [...m.entries()].sort((a, b) => a[1].title.localeCompare(b[1].title));
  }, [pool, filter]);

  const add = (s: StoryRow) => setChosen((c) => (have.has(keyOf(s)) ? c : [...c, { doc_code: s.doc_code, story_id: s.story_id, title: s.title, doc_title: s.doc_title, status: s.status }]));
  const move = (i: number, by: number) => setChosen((c) => {
    const j = i + by;
    if (j < 0 || j >= c.length) return c;
    const n = [...c];
    [n[i], n[j]] = [n[j], n[i]];
    return n;
  });
  const drop = (i: number) => setChosen((c) => c.filter((_, k) => k !== i));
  const name = (s: { title: string | null; story_id: number }) => s.title || `Story ${s.story_id}`;

  return (
    <>
      <Helmet><title>{start.id ? 'Edit the anthology | Srangam' : 'A new anthology | Srangam'}</title></Helmet>
      <Link to={start.id ? `/corpus/anthologies/${start.id}` : '/corpus/corner?tab=anthologies'} className="mb-4 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="mr-1 h-4 w-4" aria-hidden="true" /> {start.id ? 'Back to the anthology' : "The Researchers' Corner"}
      </Link>
      <h1 className="mb-2 font-serif text-3xl font-semibold text-foreground">{start.id ? 'Edit the anthology' : 'A new anthology'}</h1>
      <p className="mb-6 max-w-3xl text-sm text-muted-foreground">
        Gather approved stories from any of the texts, in the order they should be read.{' '}
        {me.is_editor ? 'You see drafts too, marked as such; an anthology is published with approved stories only.' : 'An editor publishes it to the readers of the working corpus.'}
      </p>

      <form aria-label="The anthology" className="grid gap-8 lg:grid-cols-2" onSubmit={(e) => { e.preventDefault(); if (title.trim()) save.mutate(); }}>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="anth-title">Title</Label>
            <Input id="anth-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="anth-title-hi">Title in Hindi (optional)</Label>
            <Input id="anth-title-hi" lang="hi" className="font-devanagari" value={titleHi} onChange={(e) => setTitleHi(e.target.value)} maxLength={300} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="anth-intro">Introduction (optional)</Label>
            <Textarea id="anth-intro" rows={6} value={intro} onChange={(e) => setIntro(e.target.value)} maxLength={8000} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="anth-audience">For</Label>
            <select id="anth-audience" className={SELECT} value={audience} onChange={(e) => setAudience(e.target.value as Audience)}>
              {AUDIENCES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
            </select>
          </div>

          <section aria-labelledby="anth-chosen">
            <h2 id="anth-chosen" className="mb-2 text-sm font-semibold text-foreground">Its stories, in order ({chosen.length})</h2>
            {chosen.length === 0 && <p className="text-sm text-muted-foreground">None yet: add stories from the list.</p>}
            <ol className="space-y-1.5" aria-label="Its stories">
              {chosen.map((s, i) => (
                <li key={keyOf(s)} className="flex items-center gap-2 rounded-md border border-border px-2 py-1.5 text-sm">
                  <span className="w-6 text-right font-mono text-xs text-muted-foreground">{i + 1}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-foreground">{name(s)} <MediaStatus status={s.status} /></span>
                    <span className="block truncate text-xs text-muted-foreground">{bookTitle({ doc_code: s.doc_code, title: s.doc_title }).title}</span>
                  </span>
                  <button type="button" onClick={() => move(i, -1)} disabled={i === 0} aria-label={`Move "${name(s)}" up`} className="rounded p-1 text-muted-foreground hover:text-foreground disabled:opacity-30">
                    <ArrowUp className="h-4 w-4" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => move(i, 1)} disabled={i === chosen.length - 1} aria-label={`Move "${name(s)}" down`} className="rounded p-1 text-muted-foreground hover:text-foreground disabled:opacity-30">
                    <ArrowDown className="h-4 w-4" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => drop(i)} aria-label={`Remove "${name(s)}"`} className="rounded p-1 text-muted-foreground hover:text-red-700">
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ol>
          </section>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={!title.trim() || save.isPending} className="bg-burgundy text-white hover:bg-burgundy/90">
              {save.isPending ? 'Saving...' : 'Save'}
            </Button>
            {save.data && !save.data.ok && <ActionNote ok={false} text={save.data.error} />}
          </div>
        </div>

        <section aria-labelledby="anth-pool" className="space-y-3">
          <h2 id="anth-pool" className="text-sm font-semibold text-foreground">The stories</h2>
          <div className="space-y-1.5">
            <Label htmlFor="anth-filter">Find a story</Label>
            <Input id="anth-filter" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="A title or a text" maxLength={100} />
          </div>
          {stories.isLoading && <Skeleton className="h-40 w-full" />}
          {stories.data && !stories.data.ok && <CornerProblem r={stories.data} what="The stories" />}
          {stories.data?.ok && groups.length === 0 && <p className="text-sm text-muted-foreground">{filter ? 'No story matches.' : 'No approved story yet.'}</p>}
          <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
            {groups.map(([code, g]) => (
              <div key={code}>
                <h3 className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <BookOpen className="h-3.5 w-3.5" aria-hidden="true" /> {g.title}
                </h3>
                <ul className="space-y-1">
                  {g.rows.map((s) => {
                    const on = have.has(keyOf(s));
                    return (
                      <li key={keyOf(s)} className="flex items-center gap-2 text-sm">
                        <button type="button" onClick={() => add(s)} disabled={on} aria-label={`Add "${name(s)}"`}
                          className="inline-flex items-center rounded border border-border p-1 text-burgundy hover:border-burgundy disabled:opacity-30">
                          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                        <span className="min-w-0 flex-1 truncate text-foreground">{name(s)}</span>
                        {s.from_page != null && <span className="font-mono text-xs text-muted-foreground">{s.from_page}.{s.from_idx}</span>}
                        <MediaStatus status={s.status} />
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </section>
      </form>
    </>
  );
}

const EMPTY = { id: null, title: '', title_hi: '', intro: '', audience: 'general' as Audience, items: [] as Chosen[] };

function Editing({ id, me }: { id: number; me: CornerMe }) {
  const q = useQuery({ queryKey: [...KEY, 'collection', id], queryFn: () => loadCollection(id), staleTime: 60 * 1000 });
  const c = q.data?.ok ? q.data.rows[0] : undefined;
  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.data && !q.data.ok) return <CornerProblem r={q.data} what="This anthology" />;
  if (!c || !c.can_edit) {
    return (
      <div>
        <h1 className="font-serif text-2xl font-semibold">This anthology cannot be changed here</h1>
        <p className="mt-2 text-muted-foreground">Only its maker changes a draft; an editor changes a published one.</p>
        <Link to={`/corpus/anthologies/${id}`} className="mt-3 inline-block text-burgundy hover:underline">Read it</Link>
      </div>
    );
  }
  const items = collectionItems(c.items).map((it) => ({ doc_code: it.doc_code, story_id: it.story_id, title: it.title, doc_title: it.doc_title, status: it.status }));
  const audience = (['general', 'young', 'scholar'].includes(c.audience) ? c.audience : 'general') as Audience;
  return <Builder key={`${id}-${c.updated_at}`} me={me} start={{ id, title: c.title, title_hi: c.title_hi ?? '', intro: c.intro ?? '', audience, items }} />;
}

function Body() {
  const { collectionId } = useParams<{ collectionId?: string }>();
  const [search] = useSearchParams();
  const me = useMe();
  const row = me.data?.ok ? me.data.rows[0] : undefined;
  const id = Number.parseInt(collectionId ?? '', 10);
  const making = !collectionId || search.get('edit') === '1';

  let inner;
  if (making && me.isLoading) inner = <Skeleton className="h-96 w-full" />;
  else if (making && me.data && !me.data.ok) inner = <CornerProblem r={me.data} what="The Researchers' Corner" />;
  else if (making && !row?.can_request) inner = <CornerClosed />;
  else if (!collectionId && row) inner = <Builder me={row} start={EMPTY} />;
  else if (Number.isFinite(id) && id > 0 && making && row) inner = <Editing id={id} me={row} />;
  else if (Number.isFinite(id) && id > 0) inner = <Reader id={id} me={row} />;
  else inner = <h1 className="font-serif text-2xl font-semibold">Anthology not found</h1>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 print:max-w-none print:p-0">
      <div className="print:hidden"><CorpusNav /></div>
      {inner}
    </div>
  );
}

export default function CorpusAnthology() {
  return (
    <>
      <Helmet>
        <title>Anthologies | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
