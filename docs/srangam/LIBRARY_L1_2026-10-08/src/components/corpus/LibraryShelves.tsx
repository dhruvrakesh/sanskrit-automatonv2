/**
 * The library's shelves - CORPUS_LIBRARY_C6_2026_10_08. Used by /corpus.
 *
 * Like the dashboard's Shelf page: every text under its shelf, with its title (confirmed, or
 * derived from the code and marked so), its series, how much of it is in English and Hindi, its
 * pipeline stages with the desk's reasons, and its stories. A filter, a sort, and two narrowings.
 * The stages and the stories come from the C6 functions; without them (C6 not applied, or a
 * failure) the cards simply leave those parts out.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookMarked, BookOpen, Workflow } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { share, type MirrorDoc } from '@/lib/corpusMirror';
import {
  bookTitle, isStory, loadProgress, loadStories, seriesLabel, shelve, STAGE_LABELS, stageSummary, stagesByDoc,
  type StageRow,
} from '@/lib/corpusLibrary';

const nf = new Intl.NumberFormat('en-IN');
type Sort = 'shelf' | 'title' | 'size' | 'english';

const fold = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();

const DOT: Record<string, string> = {
  done: 'bg-emerald-600 border-emerald-600',
  degraded: 'bg-amber-500 border-amber-500',
  blocked: 'bg-red-600 border-red-600',
};

function Meter({ label, part, whole }: { label: string; part: number; whole: number }) {
  const pct = whole ? Math.min(100, Math.round((100 * part) / whole)) : 0;
  return (
    <div className="text-xs text-muted-foreground">
      <div className="flex justify-between"><span>{label}</span><span>{share(part, whole)}</span></div>
      <div className="mt-0.5 h-1.5 rounded bg-muted" role="progressbar" aria-label={`${label}: ${share(part, whole)}`} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-1.5 rounded bg-burgundy/70" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function Stages({ rows }: { rows: StageRow[] }) {
  const s = stageSummary(rows);
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className="flex gap-0.5" aria-hidden="true">
        {rows.map((r) => (
          <span
            key={r.stage}
            className={`inline-block h-2.5 w-2.5 rounded-sm border ${DOT[r.status ?? ''] ?? 'border-muted-foreground/40'}`}
            title={`${STAGE_LABELS[r.stage] ?? r.stage}: ${r.status ?? 'unknown'}${r.reason ? ` — ${r.reason}` : ''}`}
          />
        ))}
      </span>
      <Popover>
        <PopoverTrigger asChild>
          <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" aria-label="The stages of this text">
            <Workflow className="h-3.5 w-3.5" aria-hidden="true" /> {s.done} of {s.total} stages
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-96 max-w-[calc(100vw-2rem)] text-xs leading-relaxed">
          <p className="mb-2 font-medium">The translation desk, stage by stage</p>
          <dl className="grid grid-cols-[auto_auto_minmax(0,1fr)] gap-x-3 gap-y-1">
            {rows.map((r) => (
              <div key={r.stage} className="contents">
                <dt>{STAGE_LABELS[r.stage] ?? r.stage}</dt>
                <dd className={r.status === 'done' ? 'text-emerald-700 dark:text-emerald-400' : r.status === 'degraded' ? 'text-amber-700 dark:text-amber-400' : r.status === 'blocked' ? 'text-red-700 dark:text-red-400' : 'text-muted-foreground'}>{r.status ?? '-'}</dd>
                <dd className="text-muted-foreground">{r.reason ?? ''}</dd>
              </div>
            ))}
          </dl>
        </PopoverContent>
      </Popover>
    </div>
  );
}

function BookCard({ d, stages, stories }: { d: MirrorDoc; stages?: StageRow[]; stories?: number }) {
  const t = bookTitle(d);
  const series = seriesLabel(d.doc_code);
  const href = `/corpus/${encodeURIComponent(d.doc_code)}`;
  return (
    <li>
      <Card className="h-full transition-colors hover:border-burgundy/50">
        <CardContent className="flex h-full flex-col gap-2 pb-4 pt-4">
          <div>
            <Link
              to={href}
              className={`font-serif text-lg leading-snug text-foreground hover:text-burgundy ${t.derived ? 'italic' : ''}`}
              title={t.derived ? 'A title derived from the file name; no title has been confirmed yet' : undefined}
            >
              {t.title}
            </Link>
            {series && <p className="text-xs text-muted-foreground">{series}</p>}
            <p className="break-all font-mono text-[11px] text-muted-foreground">{d.doc_code}</p>
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            {d.category && <Badge variant="secondary">{d.category}</Badge>}
            <span>{nf.format(d.passages)} passages</span>
            {typeof stories === 'number' && stories > 0 && <span>&middot; {stories} {stories === 1 ? 'story' : 'stories'}</span>}
          </div>
          <Meter label="English" part={d.english} whole={d.passages} />
          {d.hindi > 0 && <Meter label="Hindi" part={d.hindi} whole={d.passages} />}
          {stages && stages.length > 0 && <Stages rows={stages} />}
          <div className="mt-auto flex flex-wrap gap-x-4 gap-y-1 pt-1 text-sm">
            <Link to={href} className="inline-flex items-center text-burgundy hover:underline">
              <BookOpen className="mr-1 h-4 w-4" aria-hidden="true" /> Read
            </Link>
            {typeof stories === 'number' && stories > 0 && (
              <Link to={`/corpus/stories?doc=${encodeURIComponent(d.doc_code)}`} className="inline-flex items-center text-burgundy hover:underline">
                <BookMarked className="mr-1 h-4 w-4" aria-hidden="true" /> Stories
              </Link>
            )}
            {d.published && (
              <Link to={`/texts/${encodeURIComponent(d.doc_code)}`} className="text-muted-foreground hover:text-foreground hover:underline" title="This text is also published at /texts">
                published
              </Link>
            )}
          </div>
        </CardContent>
      </Card>
    </li>
  );
}

export default function LibraryShelves({ docs }: { docs: MirrorDoc[] }) {
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState<Sort>('shelf');
  const [onlyStories, setOnlyStories] = useState(false);
  const [onlyPublished, setOnlyPublished] = useState(false);

  const progQ = useQuery({ queryKey: ['mirror', 'progress'], queryFn: loadProgress, staleTime: 5 * 60 * 1000 });
  const storyQ = useQuery({ queryKey: ['mirror', 'stories', 'index'], queryFn: () => loadStories(null, false), staleTime: 5 * 60 * 1000 });
  const stages = useMemo(() => (progQ.data?.ok ? stagesByDoc(progQ.data.rows) : new Map<string, StageRow[]>()), [progQ.data]);
  const storyCount = useMemo(() => {
    const m = new Map<string, number>();
    if (storyQ.data?.ok) for (const s of storyQ.data.rows.filter(isStory)) m.set(s.doc_code, (m.get(s.doc_code) ?? 0) + 1);
    return m;
  }, [storyQ.data]);
  const storiesKnown = !!storyQ.data?.ok;

  const shown = useMemo(() => {
    const f = fold(filter.trim());
    return docs.filter((d) => {
      if (onlyPublished && !d.published) return false;
      if (onlyStories && !(storyCount.get(d.doc_code) ?? 0)) return false;
      if (!f) return true;
      return fold(bookTitle(d).title).includes(f) || fold(d.doc_code).includes(f) || fold(d.category ?? '').includes(f);
    });
  }, [docs, filter, onlyPublished, onlyStories, storyCount]);

  const sorted = useMemo(() => {
    const a = [...shown];
    if (sort === 'title') a.sort((x, y) => bookTitle(x).title.localeCompare(bookTitle(y).title));
    if (sort === 'size') a.sort((x, y) => y.passages - x.passages);
    if (sort === 'english') a.sort((x, y) => (y.passages ? y.english / y.passages : 0) - (x.passages ? x.english / x.passages : 0));
    return a;
  }, [shown, sort]);

  const card = (d: MirrorDoc) => (
    <BookCard key={d.doc_code} d={d} stages={stages.get(d.doc_code)} stories={storiesKnown ? storyCount.get(d.doc_code) ?? 0 : undefined} />
  );

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <label htmlFor="shelf-filter" className="sr-only">Filter the library</label>
        <Input id="shelf-filter" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter by title, code or kind" className="h-9 w-full sm:w-72" />
        <label className="inline-flex items-center gap-2">
          <span className="text-muted-foreground">Sort</span>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} className="h-9 rounded-md border border-input bg-background px-2 text-sm" aria-label="Sort the library">
            <option value="shelf">by shelf</option>
            <option value="title">by title</option>
            <option value="size">largest first</option>
            <option value="english">most translated first</option>
          </select>
        </label>
        {storiesKnown && (
          <label className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <input type="checkbox" checked={onlyStories} onChange={(e) => setOnlyStories(e.target.checked)} /> with stories
          </label>
        )}
        <label className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <input type="checkbox" checked={onlyPublished} onChange={(e) => setOnlyPublished(e.target.checked)} /> published
        </label>
        <span className="text-xs text-muted-foreground" aria-live="polite">{shown.length} of {docs.length} texts</span>
      </div>

      {shown.length === 0 && <p className="text-sm text-muted-foreground">No text matches. Clear the filter to see them all.</p>}

      {sort === 'shelf'
        ? shelve(sorted).map((sec) => (
          <section key={sec.key} aria-labelledby={`shelf-${sec.key}`} className="mb-10">
            <h2 id={`shelf-${sec.key}`} className="flex flex-wrap items-baseline gap-x-3 border-b border-border pb-1 font-serif text-xl font-semibold text-foreground">
              {sec.title}
              {sec.title_sa && <span lang="sa" className="font-devanagari text-base font-normal text-muted-foreground">{sec.title_sa}</span>}
              <span className="text-xs font-normal text-muted-foreground">{sec.books.length} {sec.books.length === 1 ? 'text' : 'texts'}</span>
            </h2>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{sec.books.map(card)}</ul>
          </section>
        ))
        : <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{sorted.map(card)}</ul>}
    </div>
  );
}
