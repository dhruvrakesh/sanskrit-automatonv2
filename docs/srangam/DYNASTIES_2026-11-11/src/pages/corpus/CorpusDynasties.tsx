/**
 * /corpus/genealogies/dynasties - the dynasties as the Purāṇas trace them, for signed-in readers - DYNASTIES_2026_11_11.
 *
 * Asked on 10 and 11 Nov: "we cant even get the genealogy of Kaunteya (Arjun) right, not to say what will happen if we
 * start looking for specific dynasties, vanshas ... has to be an API call thing". The genealogy pages draw what the
 * indexes say of a person; this page draws what the Purāṇas themselves say, verse by verse: the automaton's
 * scripts/vamsa_read.py (the Viṣṇupurāṇa's book 4, the Bhāgavatapurāṇa's books 9 and 12.1, read by a model chapter by
 * chapter and each statement checked against its verse by machine) and scripts/vamsa_join.py (each person looked for in
 * the Purāṇa Index), sent by index_sync.py into corpus.index_dynasties (docs/cloud/C28 in the automaton repo).
 * Until C28 is pasted the page says so; before the desk's first send it says that nothing has been sent; a refusal is a
 * refusal, a failure a failure. Nothing from the database is rendered as HTML.
 */
import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ChevronLeft, Crown, HelpCircle, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import {
  DYNASTY_GUIDE, dynastyCountsText, dynastyPersonHref, foldName, GENEALOGIES, INDEX_SAYS, loadDynasties,
  WORK_ORDER, WORK_TITLE, type Chip, type DynastyRow, type DynastyStep,
} from '@/lib/indexSite';

const LINK = 'text-burgundy hover:underline';
const SHOWN = 15;
const TONE: Record<Chip['tone'], string> = {
  ok: 'border-emerald-600/40 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300',
  half: 'border-amber-500/40 bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300',
  no: 'border-border bg-muted text-muted-foreground',
  ep: 'border-indigo-400/40 bg-indigo-50 text-indigo-800 dark:bg-indigo-950/30 dark:text-indigo-300',
};

function Guide() {
  return (
    <details className="mb-5 rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm">
      <summary className="flex cursor-pointer items-center gap-2 font-medium text-foreground">
        <HelpCircle className="h-4 w-4 text-burgundy" aria-hidden="true" /> How to read this page
      </summary>
      <dl className="mt-2 space-y-2 pb-1">
        {DYNASTY_GUIDE.map((g) => (
          <div key={g.term}>
            <dt className="font-semibold text-foreground">{g.term}</dt>
            <dd className="text-muted-foreground">{g.text}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function Name({ s }: { s: DynastyStep }) {
  const href = dynastyPersonHref(s);
  return href
    ? <Link to={href} className={`font-semibold ${LINK}`} title={s.index_head ? `The Purāṇa Index: ${s.index_head}` : undefined}>{s.name}</Link>
    : <span className="font-semibold text-foreground">{s.name}</span>;
}

function StepItem({ s, first }: { s: DynastyStep; first: boolean }) {
  const chip = s.index ? INDEX_SAYS[s.index] : undefined;
  return (
    <li className="border-l-2 border-burgundy/30 py-1.5 pl-3">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <Name s={s} />
        {first
          ? <span className="text-xs text-muted-foreground">the line begins here: the text names no father for him in these chapters</span>
          : <span className="text-xs text-muted-foreground">son of {s.father}{s.ref ? <>, <span className="font-mono">{s.ref}</span></> : null}</span>}
        {chip && <span title={chip.title} className={`rounded border px-1.5 py-0.5 text-[11px] leading-none ${TONE[chip.tone]}`}>{chip.label}</span>}
        {s.joined === 'index' && <span className="text-[11px] text-indigo-700 dark:text-indigo-300" title="The father is named in another chapter; the Purāṇa Index shows they are one person">joined by the index</span>}
      </div>
      {s.words && <p className="mt-0.5 font-serif text-sm italic text-foreground/80" lang="sa-Latn">{s.words}</p>}
    </li>
  );
}

function LineCard({ l, open }: { l: DynastyRow; open: boolean }) {
  const first = l.steps[0]?.name ?? '';
  const last = l.steps[l.steps.length - 1]?.name ?? '';
  const agree = l.steps.filter((s) => s.index === 'agrees').length;
  return (
    <li className="mb-3">
      <details className="rounded-lg border border-border bg-card px-4 py-2" open={open}>
        <summary className="cursor-pointer text-sm">
          <span className="font-semibold text-foreground">A line of {l.length}</span>
          {l.label && <span className="ml-2 text-burgundy">{l.label}</span>}
          <span className="ml-2 text-muted-foreground">{first} to {last}</span>
          <span className="ml-2 text-xs text-muted-foreground">({agree} of {Math.max(0, l.length - 1)} steps as the index has them)</span>
        </summary>
        <ol className="mt-2 space-y-0.5" aria-label={`The line from ${first} to ${last}`}>
          {l.steps.map((s, i) => <StepItem key={`${l.key}:${i}`} s={s} first={i === 0} />)}
        </ol>
      </details>
    </li>
  );
}

function Failure({ error }: { error: string | null }) {
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <p>The dynasties could not be read: {error ?? 'no answer'}</p>
      </CardContent>
    </Card>
  );
}

function Body() {
  const q = useQuery({ queryKey: ['index-dynasties'], queryFn: () => loadDynasties(null), staleTime: 10 * 60 * 1000 });
  const r = q.data;
  const rows = useMemo(() => (r && r.ok ? r.rows : []), [r]);
  const works = useMemo(() => {
    const have = new Set(rows.map((x) => x.work));
    return [...WORK_ORDER.filter((w) => have.has(w)), ...[...have].filter((w) => !WORK_ORDER.includes(w)).sort()];
  }, [rows]);
  const [work, setWork] = useState<string | null>(null);
  const [find, setFind] = useState('');
  const [all, setAll] = useState(false);
  const w = work && works.includes(work) ? work : works[0] ?? null;
  const head = rows.find((x) => x.work === w && x.n === 0);
  const f = foldName(find);
  const lines = rows.filter((x) => x.work === w && x.n > 0)
    .filter((x) => f.length < 2 || x.steps.some((s) => foldName(s.name).includes(f)))
    .sort((a, b) => a.n - b.n);
  const shown = all || f.length >= 2 ? lines : lines.slice(0, SHOWN);
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Helmet><title>Dynasties | Working Corpus | Srangam</title></Helmet>
      <CorpusNav />
      <p className="mb-2 text-sm"><Link to={GENEALOGIES} className={`inline-flex items-center gap-1 ${LINK}`}><ChevronLeft className="h-4 w-4" aria-hidden="true" />Genealogies</Link></p>
      <header className="mb-6">
        <h1 className="flex items-center gap-2 font-serif text-3xl font-semibold text-foreground">
          <Crown className="h-7 w-7 text-burgundy" aria-hidden="true" /> Dynasties
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          The lines of kings and sages as the Purāṇas themselves trace them, verse by verse: the Viṣṇupurāṇa&apos;s fourth
          book and the Bhāgavatapurāṇa&apos;s ninth and twelfth. Each step is a statement of the text, shown with its verse
          and the Sanskrit words that make it, and with what Dikshitar&apos;s Purāṇa Index says of the same person.
        </p>
      </header>
      <Guide />

      {q.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>}
      {r && !r.ok && r.refused && <CorpusRefused message={r.error} />}
      {r && !r.ok && !r.refused && r.missing && (
        <Card><CardContent className="pt-6 text-sm text-muted-foreground">
          The dynasties are not switched on yet. The indexes&apos; lines are at <Link to={GENEALOGIES} className={LINK}>Genealogies</Link>.
        </CardContent></Card>
      )}
      {r && !r.ok && !r.refused && !r.missing && <Failure error={r.error} />}
      {r && r.ok && rows.length === 0 && <p className="text-muted-foreground">No dynasty has been sent from the desk yet.</p>}
      {r && r.ok && rows.length > 0 && (
        <>
          <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Which text">
            {works.map((x) => (
              <Button key={x} size="sm" variant={x === w ? 'default' : 'outline'} aria-pressed={x === w} onClick={() => { setWork(x); setAll(false); }}>
                {WORK_TITLE[x] ?? rows.find((y) => y.work === x)?.title ?? x}
              </Button>
            ))}
          </div>
          {head && <p className="mb-4 text-sm text-muted-foreground" aria-label="The counts">{dynastyCountsText(head.counts)}</p>}
          <label className="mb-4 flex max-w-md items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span className="sr-only">Find a name in the lines</span>
            <Input value={find} onChange={(e) => setFind(e.target.value)} placeholder="Find a name in the lines (Ikṣvāku, Yadu, Pūru)" />
          </label>
          {lines.length === 0
            ? <p className="text-muted-foreground">No line of this text has that name.</p>
            : <ul aria-label="The lines">{shown.map((l, i) => <LineCard key={l.key} l={l} open={i === 0 && f.length < 2} />)}</ul>}
          {!all && f.length < 2 && lines.length > SHOWN && (
            <Button size="sm" variant="outline" onClick={() => setAll(true)}>Show all {lines.length} lines</Button>
          )}
          {head && (
            <p className="mt-6 text-xs text-muted-foreground">
              The verses: {head.source}. The persons: V. R. Ramachandra Dikshitar, The Purāṇa Index (Madras, 1951-55). The
              statements were read by a model and each checked by machine against its verse; a verse says where to read,
              and the reader judges.
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default function CorpusDynasties() {
  return (
    <>
      <Helmet><meta name="robots" content="noindex, nofollow" /></Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
