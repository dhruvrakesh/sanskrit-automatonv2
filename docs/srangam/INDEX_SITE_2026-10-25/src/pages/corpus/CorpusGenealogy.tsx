/**
 * /corpus/genealogies/:source/:entry - one person of one index, the line up and down - INDEX_SITE_2026_10_25.
 *
 * The desk's /vamsa?src=&entry= on the site (corpus_reader_index_tree, docs/cloud/C21 in the automaton repo): the line
 * as the desk draws it (the father's line before the mother's, then the better attested, then the longer), each rung
 * with its generation, its spouses, its other parents (?via= draws the line up through one of them) and its siblings;
 * between the rungs each step with what it rests on, and, chosen, the step's evidence: the index's statements with
 * their words and references, the Sanskrit verses where both names stand (GRETIL; the names marked), the epics' verses
 * that name both (the Mahabharata's counted, never quoted), our own passages that name both, each a link into the
 * reader; then the children and grandchildren. Nothing from the database is rendered as HTML.
 */
import { useMemo, useState, type ReactNode } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowLeft, GitBranch } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import IndexCredits from '@/components/corpus/IndexCredits';
import { bookTitle } from '@/lib/corpusLibrary';
import {
  citeBlocks, citedNote, collapseNames, epicLine, GENEALOGIES, generationLabel, loadIndexTree, markForms, nameHrefOf,
  personHref, placeHref, relationLabel, SOURCE_SHORT, stepChips, TEXT_SHORT, VERSE_CLAMP, type Chip, type Rung,
  type Statement, type Step, type Tree,
} from '@/lib/indexSite';

const LINK = 'text-burgundy hover:underline';
const TONE: Record<Chip['tone'], string> = {
  ok: 'border-emerald-600/40 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300',
  half: 'border-amber-500/40 bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300',
  no: 'border-border bg-muted text-muted-foreground',
  ep: 'border-indigo-400/40 bg-indigo-50 text-indigo-800 dark:bg-indigo-950/30 dark:text-indigo-300',
};

function Chips({ chips }: { chips: Chip[] }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      {chips.map((c) => (
        <span key={c.label} title={c.title} className={`rounded border px-1.5 py-0.5 text-[11px] leading-none ${TONE[c.tone]}`}>{c.label}</span>
      ))}
    </span>
  );
}

/** The part of a long verse to show closed: from a little before the first name it marks, else from its start. */
function clampAt(words: string, forms: string[]): [number, number] {
  const ks = forms.map((f) => (f ? words.indexOf(f) : -1)).filter((k) => k >= 0);
  const from = ks.length ? Math.max(0, Math.min(...ks) - 80) : 0;
  const a = from > 0 ? words.indexOf(' ', from) + 1 || from : 0;
  return [a, Math.min(words.length, a + VERSE_CLAMP)];
}

function Verse({ text, refLabel, words, forms }: { text: string; refLabel: string; words: string; forms: string[] }) {
  const [open, setOpen] = useState(false);
  const long = words.length > VERSE_CLAMP + 40;
  const [a, b] = long && !open ? clampAt(words, forms) : [0, words.length];
  const part = words.slice(a, b);
  return (
    <blockquote className="my-1.5 rounded-md border-l-4 border-amber-500/60 bg-muted/50 px-3 py-1.5">
      <span className="block font-mono text-[11px] text-muted-foreground">{TEXT_SHORT[text] ?? text} {refLabel}</span>
      <span lang="sa-Latn" className="font-serif text-sm text-foreground">
        {a > 0 ? '… ' : ''}
        {markForms(part, forms).map((p, i) => (p.mark ? <mark key={i} className="rounded bg-amber-200/60 px-0.5 dark:bg-amber-700/40">{p.text}</mark> : <span key={i}>{p.text}</span>))}
        {b < words.length ? ' …' : ''}
      </span>
      {long && (
        <button type="button" onClick={() => setOpen((o) => !o)} className="mt-1 block text-xs text-burgundy hover:underline" aria-expanded={open}>
          {open ? 'Show less' : `Show the whole passage (${words.length.toLocaleString('en-IN')} characters)`}
        </button>
      )}
    </blockquote>
  );
}

function StatementView({ it, tree }: { it: Statement; tree: Tree }) {
  const blocks = citeBlocks(it, tree.verses ?? {});
  const shown = blocks.reduce((a, b) => a + b.verses.length, 0);
  const epics = epicLine(it.together);
  const places = it.places ?? [];
  return (
    <li className="border-b border-border py-3 last:border-b-0">
      <p className="text-sm text-foreground">
        {it.subject} <i>{relationLabel(it.relation)}</i> {it.object}{' '}
        <span className="text-xs text-muted-foreground">
          in the entry {it.stated_in}{it.n > 1 ? `, stated ${it.n} times` : ''}
        </span>
      </p>
      {it.words && (
        <p className="mt-1 font-serif text-sm text-foreground/90">
          &ldquo;{it.words}&rdquo;{it.refs && it.refs.length ? <span className="text-muted-foreground"> ({it.refs.join('; ')})</span> : null}
        </p>
      )}
      {blocks.map((b) => (
        <div key={`${b.text}|${b.ref}`}>
          {b.verses.map((v) => <Verse key={v.ref} text={b.text} refLabel={v.ref} words={v.words} forms={v.forms} />)}
          <p className="text-xs text-muted-foreground">
            {b.verdict === 'both' ? 'Both names' : 'One name'} in {TEXT_SHORT[b.text] ?? b.text} {b.ref}
            {b.printed ? ` (the index prints ${b.printed})` : ''}
          </p>
        </div>
      ))}
      {!shown && citedNote(it.cited) && <p className="text-xs text-muted-foreground">{citedNote(it.cited)}</p>}
      {epics && <p className="text-xs text-muted-foreground">Both names in one verse of {epics}</p>}
      {(['hv', 'ram'] as const).map((code) => {
        const e = it.together?.[code];
        const ref = e && e[0] > 0 ? e[1] : '';
        const w = ref ? tree.verses?.[`${code}|${ref}`] : undefined;
        return w ? <Verse key={code} text={code} refLabel={ref} words={w} forms={[]} /> : null;
      })}
      {it.ours && it.ours !== 'not tied' && (
        <p className="mt-1 text-xs text-muted-foreground">
          Our own passages: {it.ours}{it.passages ? ` (${it.passages} ${it.passages === 1 ? 'passage' : 'passages'})` : ''}
          {places.length > 0 && <>: {places.map((p, i) => (
            <span key={`${p.doc}-${p.page}-${p.idx}`}>
              {i > 0 ? ', ' : ''}<Link to={placeHref(p)} className={LINK}>{bookTitle({ doc_code: p.doc }).title}{p.ref ? ` ${p.ref}` : ''}</Link>
            </span>
          ))}</>}
        </p>
      )}
      {(it.subject_canonical || it.object_canonical) && (
        <p className="mt-1 text-xs text-muted-foreground">
          In our texts:{' '}
          {[it.subject_canonical, it.object_canonical].filter((c, i, a): c is string => !!c && a.indexOf(c) === i).map((c, i) => (
            <span key={c}>{i > 0 ? ', ' : ''}<Link to={nameHrefOf(c)} className={LINK}>{c}</Link></span>
          ))}
        </p>
      )}
    </li>
  );
}

function Evidence({ tree, at }: { tree: Tree; at: number }) {
  if (!tree.steps.length) {
    return <p className="text-sm text-muted-foreground">This person has no parent or child in the index.</p>;
  }
  const st: Step = tree.steps[at];
  const p = tree.line[at];
  const c = tree.line[at + 1];
  return (
    <>
      <p className="text-sm text-muted-foreground">
        <b className="text-foreground">{p.head}</b> &rarr; <b className="text-foreground">{c.head}</b> &middot;{' '}
        {st.both_entries ? 'both entries state it' : 'one entry states it'}
      </p>
      {st.joined === 'verse' && <p className="mt-1 text-xs text-muted-foreground">The name has several entries in the index; the one whose entry cites the same verse was taken.</p>}
      {st.joined === 'named' && <p className="mt-1 text-xs text-muted-foreground">The index names this person, but its entries of that name cannot be told apart.</p>}
      <ul aria-label="The statements">{st.items.map((it) => <StatementView key={it.key} it={it} tree={tree} />)}</ul>
    </>
  );
}

function Names({ label, names, source }: { label: string; names: { entry: number; head: string }[]; source: string }) {
  return (
    <span>
      {label}{' '}
      {collapseNames(names).map((n, i) => (
        <span key={n.entry}>
          {i > 0 ? ', ' : ''}<Link to={personHref(source, n.entry)} className={LINK}>{n.head}</Link>
          {n.times > 1 ? <span title="Named in several places without an entry of its own"> &times;{n.times}</span> : null}
        </span>
      ))}
    </span>
  );
}

function RungBox({ r, me, source }: { r: Rung; me: boolean; source: string }) {
  const side: ReactNode[] = [];
  if (r.named_only) side.push(<span key="n">named in the index; its entries of this name cannot be told apart</span>);
  if (r.spouses?.length) side.push(<Names key="s" label="married to" names={r.spouses} source={source} />);
  if (r.other_parents?.length) {
    side.push(
      <span key="o">
        also the child of{' '}
        {collapseNames(r.other_parents).map((o, i) => (
          <span key={o.entry}>
            {i > 0 ? ', ' : ''}<Link to={personHref(source, o.entry)} className={LINK}>{o.head}</Link>
            {o.times > 1 ? <span title="Named in several places without an entry of its own"> &times;{o.times}</span> : null}
            {o.entry > 0 && (
              <> (<Link to={personHref(source, r.entry, o.entry)} className={LINK} title="Draw the line up through this parent">line through</Link>)</>
            )}
          </span>
        ))}
      </span>,
    );
  }
  if (r.siblings_n > 0) {
    side.push(
      <span key="b">
        <Names label={r.siblings_n === 1 ? '1 sibling:' : `${r.siblings_n} siblings:`} names={r.siblings} source={source} />
        {r.siblings_n > r.siblings.length ? ' …' : ''}
      </span>,
    );
  }
  return (
    <div className={`rounded-md border px-3 py-2 ${me ? 'border-burgundy bg-burgundy/5' : 'border-border'}`}>
      <div className="flex flex-wrap items-baseline gap-x-2">
        {me
          ? <span className="font-serif text-base font-semibold text-foreground" aria-current="true">{r.head}</span>
          : <Link to={personHref(source, r.entry)} className="font-serif text-base text-foreground hover:text-burgundy">{r.head}</Link>}
        {r.sex === 'f' && <span className="text-xs text-muted-foreground">(f.)</span>}
        {r.canonical && <Link to={nameHrefOf(r.canonical)} className={`text-xs ${LINK}`} title="This person in our texts, on the Names page">in our texts &rarr;</Link>}
      </div>
      {side.length > 0 && (
        <div className="mt-1 text-xs text-muted-foreground">
          {side.map((s, i) => <span key={i}>{i > 0 ? ' · ' : ''}{s}</span>)}
        </div>
      )}
    </div>
  );
}

function Ladder({ tree, at, choose }: { tree: Tree; at: number; choose: (i: number) => void }) {
  return (
    <ol aria-label="The line" className="space-y-0">
      {tree.line.map((r, i) => (
        <li key={`${r.entry}-${i}`}>
          <div className="flex items-start gap-3">
            <div className="w-9 shrink-0 pt-2 text-right font-mono text-xs text-muted-foreground" aria-label={`generation ${generationLabel(r.generation)}`}>
              {generationLabel(r.generation)}
            </div>
            <div className="min-w-0 flex-1"><RungBox r={r} me={i === tree.me} source={tree.source} /></div>
          </div>
          {i < tree.steps.length && (
            <div className="flex items-stretch gap-3">
              <div className="w-9 shrink-0" />
              <div className={`ml-4 border-l-2 ${tree.steps[i].both_entries ? 'border-solid' : 'border-dashed'} border-muted-foreground/40 py-1.5 pl-3`}>
                <button
                  type="button"
                  onClick={() => choose(i)}
                  aria-pressed={at === i}
                  aria-label={`What the step from ${r.head} to ${tree.line[i + 1].head} rests on`}
                  className={`rounded px-1 py-0.5 text-left ${at === i ? 'ring-2 ring-burgundy/60' : 'hover:bg-muted'}`}
                >
                  <Chips chips={stepChips(tree.steps[i])} />
                </button>
              </div>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

function Down({ tree }: { tree: Tree }) {
  if (!tree.down?.length) return null;
  const me = tree.line[tree.me];
  return (
    <section aria-label="Descendants" className="mt-6">
      {tree.down.map((gen, gi) => (
        <div key={gi} className="mb-3">
          <h3 className="mb-1 font-serif text-base font-semibold text-foreground">
            {gi === 0 ? `Children of ${me.head}` : `Generation ${generationLabel(gi + 1)}`}
          </h3>
          <ul className="flex flex-wrap gap-1.5">
            {gen.map((n) => (
              <li key={`${n.of}-${n.entry}`}>
                <Link
                  to={personHref(tree.source, n.entry)}
                  title={n.evidence?.cited === 'both' ? 'both names in the cited verse' : undefined}
                  className={`inline-block rounded-md border px-2 py-1 text-sm hover:border-burgundy ${n.on_line ? 'border-burgundy/60 bg-burgundy/5' : 'border-border'}`}
                >
                  {n.head}{n.evidence?.cited === 'both' ? ' ✓' : ''}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

function firstStep(tree: Tree): number {
  if (!tree.steps.length) return 0;
  if (tree.me > 0) return tree.me - 1;
  const f = tree.steps.findIndex((s) => s.cited === 'both');
  return f >= 0 ? f : 0;
}

function TreeView({ tree }: { tree: Tree }) {
  const [chosen, setChosen] = useState<number | null>(null);
  const at = chosen ?? firstStep(tree);
  const me = tree.line[tree.me] ?? tree.person;
  const verified = useMemo(() => tree.steps.filter((s) => s.cited === 'both').length, [tree]);
  const texts = Object.entries(tree.texts ?? {}).map(([code, t]) => ({ code, ...t }));
  return (
    <>
      <Helmet><title>{`${me.head} | Genealogies | Srangam`}</title></Helmet>
      <header className="mb-5">
        <h1 className="flex flex-wrap items-baseline gap-x-3 font-serif text-3xl font-semibold text-foreground">
          {me.head}
          {me.canonical && <Link to={nameHrefOf(me.canonical)} className={`text-sm font-normal ${LINK}`}>{me.canonical} in our texts &rarr;</Link>}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {tree.title ?? SOURCE_SHORT[tree.source] ?? tree.source} &middot; {tree.line.length} generations shown &middot;{' '}
          {verified} of {tree.steps.length} steps with both names in the cited verse
        </p>
      </header>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <section aria-label="The line of descent">
          <Ladder tree={tree} at={at} choose={setChosen} />
          <Down tree={tree} />
        </section>
        <section aria-labelledby="evidence" className="lg:sticky lg:top-20 lg:self-start">
          <Card>
            <CardContent className="pt-5">
              <h2 id="evidence" className="mb-2 font-serif text-xl font-semibold text-foreground">What the step rests on</h2>
              <Evidence tree={tree} at={Math.max(0, Math.min(tree.steps.length - 1, at))} />
            </CardContent>
          </Card>
        </section>
      </div>
      <IndexCredits texts={texts} />
    </>
  );
}

function Body() {
  const { source = '', entry = '' } = useParams<{ source: string; entry: string }>();
  const [params] = useSearchParams();
  const e = Number(entry);
  const v = params.get('via');
  const via = v != null && v !== '' && Number.isInteger(Number(v)) ? Number(v) : null;
  const ok = !!source && Number.isInteger(e);
  const q = useQuery({
    queryKey: ['mirror', 'index-tree', source, e, via],
    queryFn: () => loadIndexTree(source, e, via, 2),
    enabled: ok,
    staleTime: 10 * 60 * 1000,
  });
  const r = q.data;
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <CorpusNav />
      <Link to={GENEALOGIES} className="mb-4 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="mr-1 h-4 w-4" aria-hidden="true" /> All genealogies
      </Link>
      {!ok && <p className="text-muted-foreground">No person was named.</p>}
      {q.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-64 w-full" /></div>}
      {r && !r.ok && r.refused && <CorpusRefused message={r.error} />}
      {r && !r.ok && !r.refused && r.missing && (
        <Card><CardContent className="pt-6 text-sm text-muted-foreground">The genealogies are not switched on yet.</CardContent></Card>
      )}
      {r && !r.ok && !r.refused && !r.missing && r.error === 'no such person in the index' && (
        <p className="flex items-center gap-2 text-muted-foreground">
          <GitBranch className="h-4 w-4" aria-hidden="true" /> This person is not in the index the site has. Find the name
          on{' '}<Link to={GENEALOGIES} className={LINK}>the genealogies page</Link>.
        </p>
      )}
      {r && !r.ok && !r.refused && !r.missing && r.error !== 'no such person in the index' && (
        <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
          <CardContent className="flex items-start gap-3 pt-6 text-sm">
            <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
            <div>
              <p className="font-semibold">The line could not be loaded.</p>
              {r.error && <p className="mt-2 font-mono text-xs text-muted-foreground">{r.error}</p>}
            </div>
          </CardContent>
        </Card>
      )}
      {r?.ok && r.value && <TreeView key={`${source}:${e}:${via ?? ''}`} tree={r.value} />}
    </div>
  );
}

export default function CorpusGenealogy() {
  return (
    <>
      <Helmet>
        <title>Genealogies | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
