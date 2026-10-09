/**
 * /corpus/images - CORPUS_MEDIA_C8_2026_10_09.
 *
 * The pictures the translation desk has drawn for the texts (scripts/images.py), each anchored to
 * the passage it illustrates. A reader sees the APPROVED pictures; an editor (admin) also sees
 * drafts, marked as such. Approval is a person's decision on the desk; scripts/corpus_media.py
 * carries it here. ?doc=<code> shows one text; ?pic=<key> opens one picture (a link to share).
 * The graphic novels' pages are in /corpus/novels, not here.
 */
import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookMarked, ChevronLeft, ChevronRight, Images } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import CorpusImage from '@/components/corpus/CorpusImage';
import { GeneratedNote, MediaProblem, MediaStatus } from '@/components/corpus/MediaParts';
import { atHref, bookTitle, storyHref } from '@/lib/corpusLibrary';
import { anchorRef, isGenerated, isMedia, KIND_LABELS, loadMedia, MEDIA_PAGE, type MediaRow } from '@/lib/corpusMedia';

function Picture({ m, open }: { m: MediaRow; open: () => void }) {
  const ref = anchorRef(m);
  return (
    <Card className="h-full overflow-hidden transition-colors hover:border-burgundy/50">
      <button type="button" onClick={open} className="block w-full text-left" aria-label={`Open the picture: ${m.title ?? m.media_key}`}>
        <CorpusImage sha={m.sha256} available={m.has_thumb} width={m.width} height={m.height} alt={m.title ?? 'A picture'}
          ratio="4 / 3" className="rounded-none" />
      </button>
      <CardContent className="space-y-1 pb-3 pt-3">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{bookTitle({ doc_code: m.doc_code, title: m.doc_title }).title}</span>
          {ref && <Link to={atHref(m.doc_code, ref)} className="font-mono text-burgundy hover:underline" title="The passage it illustrates">{ref}</Link>}
          <MediaStatus status={m.status} />
        </div>
        <button type="button" onClick={open} className="text-left font-serif leading-snug text-foreground hover:text-burgundy">
          {m.title || KIND_LABELS[m.kind] || 'Picture'}
        </button>
      </CardContent>
    </Card>
  );
}

function Lightbox({ list, at, go, close }: { list: MediaRow[]; at: number; go: (i: number) => void; close: () => void }) {
  const m = list[at];
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' && at < list.length - 1) go(at + 1);
      if (e.key === 'ArrowLeft' && at > 0) go(at - 1);
    };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [at, list.length, go]);
  if (!m) return null;
  const ref = anchorRef(m);
  return (
    <Dialog open onOpenChange={(o) => { if (!o) close(); }}>
      <DialogContent className="max-h-[95vh] max-w-5xl overflow-y-auto">
        <DialogTitle className="font-serif text-xl">{m.title || KIND_LABELS[m.kind] || 'Picture'}</DialogTitle>
        <DialogDescription className="sr-only">A picture from {m.doc_title} and its caption</DialogDescription>
        <CorpusImage sha={m.sha256} rendition={m.has_display ? 'display' : 'thumb'} available={m.has_display || m.has_thumb}
          width={m.width} height={m.height} alt={m.title ?? 'A picture'} eager className="max-h-[65vh] w-full" />
        <div className="space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{KIND_LABELS[m.kind] ?? m.kind}</span>
            <Link to={`/corpus/${encodeURIComponent(m.doc_code)}`} className="hover:text-foreground hover:underline">
              {bookTitle({ doc_code: m.doc_code, title: m.doc_title }).title}
            </Link>
            {ref && <Link to={atHref(m.doc_code, ref)} className="font-mono text-burgundy hover:underline">read the passage {ref}</Link>}
            {m.story_id != null && (
              <Link to={storyHref({ doc_code: m.doc_code, story_id: m.story_id })} className="inline-flex items-center gap-1 text-burgundy hover:underline">
                <BookMarked className="h-3 w-3" aria-hidden="true" /> its story
              </Link>
            )}
            <MediaStatus status={m.status} />
          </div>
          {m.caption_en && <p lang="en" className="font-serif text-base leading-relaxed text-foreground">{m.caption_en}</p>}
          {m.caption_hi && <p lang="hi" className="font-devanagari text-base leading-relaxed text-foreground/90">{m.caption_hi}</p>}
          {m.context_note && <p className="whitespace-pre-line text-muted-foreground">{m.context_note}</p>}
          {isGenerated(m.kind) ? <GeneratedNote model={m.model} /> : m.license && <p className="text-xs text-muted-foreground">{m.license}</p>}
          {m.approved_at_local && <p className="text-xs text-muted-foreground">Approved {m.approved_at_local.slice(0, 10)}.</p>}
        </div>
        <nav className="flex justify-between text-sm" aria-label="Other pictures">
          <button type="button" disabled={at === 0} onClick={() => go(at - 1)} className="inline-flex items-center text-burgundy disabled:opacity-30">
            <ChevronLeft className="h-4 w-4" aria-hidden="true" /> Previous
          </button>
          <span className="text-xs text-muted-foreground">{at + 1} of {list.length}</span>
          <button type="button" disabled={at >= list.length - 1} onClick={() => go(at + 1)} className="inline-flex items-center text-burgundy disabled:opacity-30">
            Next <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </nav>
      </DialogContent>
    </Dialog>
  );
}

function Body() {
  const [search, setSearch] = useSearchParams();
  const doc = search.get('doc');
  const pic = search.get('pic');
  const [pages, setPages] = useState(1);
  useEffect(() => setPages(1), [doc]);

  const index = useQuery({ queryKey: ['mirror', 'media', 'index'], queryFn: () => loadMedia({ k: 200 }), staleTime: 5 * 60 * 1000 });
  const list = useQuery({
    queryKey: ['mirror', 'media', doc ?? '*', pages],
    queryFn: () => loadMedia({ doc, k: MEDIA_PAGE * pages }),
    staleTime: 5 * 60 * 1000,
    placeholderData: (prev) => prev,
  });
  const all = useMemo(() => (index.data?.ok ? index.data.rows.filter(isMedia) : []), [index.data]);
  const rows = useMemo(() => (list.data?.ok ? list.data.rows.filter(isMedia) : []), [list.data]);
  const total = rows[0]?.total ?? 0;
  const texts = useMemo(() => {
    const m = new Map<string, { title: string; n: number }>();
    for (const r of all) {
      const cur = m.get(r.doc_code);
      m.set(r.doc_code, { title: cur?.title ?? bookTitle({ doc_code: r.doc_code, title: r.doc_title }).title, n: (cur?.n ?? 0) + 1 });
    }
    return [...m.entries()];
  }, [all]);
  const at = pic ? rows.findIndex((r) => r.media_key === pic) : -1;
  const set = (o: Record<string, string | null>) => {
    const next = new URLSearchParams(search);
    for (const [k, v] of Object.entries(o)) { if (v) next.set(k, v); else next.delete(k); }
    setSearch(next, { replace: 'pic' in o && !('doc' in o) });
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <CorpusNav />
      <header className="mb-6">
        <h1 className="flex items-center gap-3 font-serif text-3xl font-semibold text-foreground">
          <Images className="h-7 w-7 text-burgundy" aria-hidden="true" /> Pictures from the texts
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          Illustrations drawn on the translation desk for passages of the texts, each linked to the passage it
          illustrates. They are generated pictures, not historical sources; a person approves each one before it
          appears here. Pictures open at full size; the first view of each may take a moment.
        </p>
      </header>

      {(list.isLoading || index.isLoading) && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
          <Skeleton className="h-56 w-full" /><Skeleton className="h-56 w-full" /><Skeleton className="h-56 w-full" />
        </div>
      )}
      {list.data && !list.data.ok && <MediaProblem r={list.data} what="The pictures" />}

      {texts.length > 1 && (
        <div className="mb-6 flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Pictures of one text">
          <button type="button" onClick={() => set({ doc: null, pic: null })} aria-pressed={!doc}
            className={`rounded-full border px-3 py-1 ${!doc ? 'border-burgundy bg-burgundy text-white' : 'border-border text-muted-foreground hover:text-foreground'}`}>
            All texts{all.length < 200 ? ` (${all.length})` : ''}
          </button>
          {texts.map(([code, t]) => (
            <button key={code} type="button" onClick={() => set({ doc: code, pic: null })} aria-pressed={doc === code}
              className={`rounded-full border px-3 py-1 ${doc === code ? 'border-burgundy bg-burgundy text-white' : 'border-border text-muted-foreground hover:text-foreground'}`}>
              {t.title}{all.length < 200 ? ` (${t.n})` : ''}
            </button>
          ))}
        </div>
      )}

      {list.data?.ok && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No picture has been approved yet. They appear here as they are approved on the translation desk.
        </p>
      )}

      {rows.length > 0 && (
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((m) => (
            <li key={m.media_key}><Picture m={m} open={() => set({ pic: m.media_key })} /></li>
          ))}
        </ol>
      )}
      {rows.length > 0 && rows.length < total && (
        <div className="mt-6 text-center">
          <button type="button" onClick={() => setPages((p) => p + 1)} disabled={list.isFetching}
            className="rounded-md border border-border px-4 py-2 text-sm text-burgundy hover:border-burgundy disabled:opacity-50">
            {list.isFetching ? 'Loading...' : `More pictures (${rows.length} of ${total})`}
          </button>
        </div>
      )}

      {at >= 0 && <Lightbox list={rows} at={at} go={(i) => set({ pic: rows[i]?.media_key ?? null })} close={() => set({ pic: null })} />}
    </div>
  );
}

export default function CorpusImages() {
  return (
    <>
      <Helmet>
        <title>Pictures | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
