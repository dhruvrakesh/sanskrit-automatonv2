/**
 * /corpus/genealogies/vamsas - the Sūryavaṃśa and the Candravaṃśa across the texts, for signed-in readers -
 * VAMSA_WAYIN_2026_11_18.
 *
 * Asked on 17 and 18 Nov: "have we made it easy for the user find geneaologies of kings via well known texts and king /
 * vansha names . surya and chandravanshas", and that the genealogies carry tooltips and the references of Dikshitar,
 * Raychaudhuri and B. C. Law. The Dynasties page draws one text's lines at a time; this page begins from the vaṃśa:
 * each dynasty from its founder (Ikṣvāku, Purūravas, Yadu, Kuru ...), generation by generation, as every text that tells
 * it names each king (the automaton's vamsa_align.py, G6c), each name linked to its text's line on the Dynasties page,
 * each generation with Dikshitar's person in the Purāṇa Index and Raychaudhuri's claims the site already carries
 * (docs/cloud/C29_index_vamsas_2026-11-18.sql in the automaton repo). The list comes without the generations (light);
 * a dynasty's generations come when it is opened, kept 10 minutes. B. C. Law's book is in copyright: not here.
 * Until C29 is pasted the page says so; a refusal is a refusal, a failure a failure. Nothing from the database is
 * rendered as HTML.
 *
 * VAMSA_FINDINGS_SITE_2026_11_19: and our findings on each dynasty, those a person approved (the desk's R1, read with
 * Dikshitar, Raychaudhuri and B. C. Law), each source with its words on hover: the verse, the Index's entry,
 * Raychaudhuri's claim; Law by page only (in copyright). One small read for every dynasty (C31's
 * corpus_reader_index_vamsa_findings), kept 10 minutes; until C31 is pasted nothing is shown and nothing else changes.
 */
import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BookOpen, ChevronLeft, HelpCircle, Lightbulb, Moon, Search, Sun } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import {
  DYNASTIES, dynastyLineHref, dynastyPersonHref, foldPlain, GEN_STATUS, GENEALOGIES, INDEX_SAYS, loadVamsas,
  nameHrefOf, VAMSA_ABOUT, VAMSA_CREDIT, VAMSA_GUIDE, VAMSA_ORDER, VAMSA_TITLE, vamsaClaimPage, vamsaCountsText,
  WORK_ORDER, WORK_TITLE, type Chip, type VamsaGen, type VamsaRow,
  FINDING_KIND, findingCiteText, findingMade, loadVamsaFindings, type VamsaFinding, type VamsaFindingCite,
} from '@/lib/indexSite';

const LINK = 'text-burgundy hover:underline';
const TONE: Record<Chip['tone'], string> = {
  ok: 'border-emerald-600/40 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300',
  half: 'border-amber-500/40 bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300',
  no: 'border-border bg-muted text-muted-foreground',
  ep: 'border-indigo-400/40 bg-indigo-50 text-indigo-800 dark:bg-indigo-950/30 dark:text-indigo-300',
};
const RAYCHAUDHURI = 'H. C. Raychaudhuri, Political History of Ancient India (1923)';
const byWork = (a: string, b: string) => {
  const i = WORK_ORDER.indexOf(a); const j = WORK_ORDER.indexOf(b);
  return (i < 0 ? 99 : i) - (j < 0 ? 99 : j) || a.localeCompare(b);
};

function ChipOf({ chip }: { chip?: Chip }) {
  return chip ? <span title={chip.title} className={`rounded border px-1.5 py-0.5 text-[11px] leading-none ${TONE[chip.tone]}`}>{chip.label}</span> : null;
}

function Guide() {
  return (
    <details className="mb-5 rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm">
      <summary className="flex cursor-pointer items-center gap-2 font-medium text-foreground">
        <HelpCircle className="h-4 w-4 text-burgundy" aria-hidden="true" /> How to read this page
      </summary>
      <dl className="mt-2 space-y-2 pb-1">
        {VAMSA_GUIDE.map((g) => (
          <div key={g.term}>
            <dt className="font-semibold text-foreground">{g.term}</dt>
            <dd className="text-muted-foreground">{g.text}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

/** What the scholars say of one generation: Dikshitar's person, Raychaudhuri on the name and on the two. */
function Scholars({ g, before }: { g: VamsaGen; before: string }) {
  const pui = g.pui;
  const href = pui ? dynastyPersonHref({ person: pui.person, page: pui.page }) : null;
  const said = pui?.index ? INDEX_SAYS[pui.index] : undefined;
  if (!pui && !g.ray_name_n && !g.ray?.length) return null;
  return (
    <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
      {pui && (
        <span title={`V. R. Ramachandra Dikshitar, The Purāṇa Index (Madras, 1951-55): the entry ${pui.head}${said ? `. ${said.title}` : ''}`}>
          <BookOpen className="mr-1 inline h-3 w-3 text-muted-foreground" aria-hidden="true" />
          Purāṇa Index:{' '}
          {href ? <Link to={href} className={LINK}>{pui.head}</Link> : <span className="text-foreground">{pui.head}</span>}
          {said && <> <ChipOf chip={said} /></>}
        </span>
      )}
      {!!g.ray_name_n && (
        <span title={`${RAYCHAUDHURI}: ${g.ray_name_n} of his claims name ${g.canonical ?? g.name}. A name may be more than one person: read them on the name's page.`}>
          Raychaudhuri:{' '}
          {g.canonical
            ? <Link to={nameHrefOf(g.canonical)} className={LINK}>{g.ray_name_n} claims on the name</Link>
            : <span className="text-foreground">{g.ray_name_n} claims on the name</span>}
        </span>
      )}
      {!!g.ray?.length && (
        <details className="w-full">
          <summary className="cursor-pointer text-burgundy">Raychaudhuri names {before} and {g.name} together ({g.ray_n ?? g.ray.length})</summary>
          <ul className="mt-1 space-y-1 pl-4">
            {g.ray.map((c) => (
              <li key={c.key} className="text-muted-foreground">
                <span className="text-foreground">{c.claim}</span> <span className="whitespace-nowrap">({vamsaClaimPage(c)})</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

/** VAMSA_FINDINGS_SITE_2026_11_19: a generation's place on the page, for a finding's source to point at. */
const genAnchor = (k: string, gen: number) => `vamsa-${k}-g${gen}`;

function Generation({ g, before, k }: { g: VamsaGen; before: string; k?: string }) {
  const works = Object.keys(g.cells).sort(byWork);
  return (
    <li id={k ? genAnchor(k, g.gen) : undefined} className="border-l-2 border-burgundy/30 py-2 pl-3">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-xs text-muted-foreground">{g.gen === 0 ? 'the founder' : `generation ${g.gen}`}</span>
        <span className="font-semibold text-foreground">{g.name}</span>
        <ChipOf chip={GEN_STATUS[g.status]} />
      </div>
      <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm" aria-label={`The texts on ${g.name}`}>
        {works.map((w) => {
          const c = g.cells[w];
          const tip = [c.ref, c.words].filter(Boolean).join(': ') || undefined;
          const label = <><span className="text-muted-foreground">{WORK_TITLE[w] ?? w}:</span> {c.name}</>;
          return (
            <li key={w} title={tip}>
              {c.line ? <Link to={dynastyLineHref(w, c.line)} className={LINK}>{label}</Link> : label}
            </li>
          );
        })}
      </ul>
      <Scholars g={g} before={before} />
    </li>
  );
}

function Generations({ k }: { k: string }) {
  const q = useQuery({ queryKey: ['index-vamsa', k], queryFn: () => loadVamsas(k), staleTime: 10 * 60 * 1000 });
  const r = q.data;
  if (q.isLoading) return <Skeleton className="mt-2 h-24 w-full" />;
  if (r && !r.ok) return <p className="mt-2 text-sm text-amber-700" role="alert">The generations could not be read: {r.error ?? 'no answer'}</p>;
  const gens = (r && r.ok ? r.rows.find((x) => x.key === k)?.rows : undefined) ?? [];
  if (!gens.length) return <p className="mt-2 text-sm text-muted-foreground">No generation of this dynasty has been sent from the desk yet.</p>;
  return (
    <ol className="mt-2 space-y-0.5">
      {gens.map((g, i) => <Generation key={`${k}:${g.gen}`} g={g} before={i > 0 ? gens[i - 1].name : ''} k={k} />)}
    </ol>
  );
}

/** VAMSA_FINDINGS_SITE_2026_11_19: one source of a finding: its label, its words on hover, its link when there is one. */
function Source({ k, c }: { k: string; c: VamsaFindingCite }) {
  const { label, title } = findingCiteText(c);
  const cls = 'rounded border border-border bg-background px-1.5 py-0.5';
  if (c.t === 'gen') return <li><a href={`#${genAnchor(k, c.gen)}`} title={title} className={`${cls} ${LINK}`}>{label}</a></li>;
  if (c.t === 'verse' && c.line) return <li><Link to={dynastyLineHref(c.work, c.line)} title={title} className={`${cls} ${LINK}`}>{label}</Link></li>;
  if (c.t === 'index') {
    const href = dynastyPersonHref({ person: c.person, page: c.page });
    if (href) return <li><Link to={href} title={title} className={`${cls} ${LINK}`}>{label}</Link></li>;
  }
  return <li><span title={title} className={`${cls} text-muted-foreground`}>{label}</span></li>;
}

/** VAMSA_FINDINGS_SITE_2026_11_19: our findings on one dynasty, those a person approved. */
function Findings({ k, items }: { k: string; items: VamsaFinding[] }) {
  if (!items.length) return null;
  return (
    <section className="mt-3 rounded-md border border-burgundy/20 bg-burgundy/5 px-3 py-2" aria-label={`Our findings on ${k}`}>
      <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
        <Lightbulb className="h-4 w-4 text-burgundy" aria-hidden="true" /> Our findings ({items.length})
      </h3>
      <ol className="mt-1 space-y-3">
        {items.map((f) => (
          <li key={f.n} className="text-sm">
            <p className="leading-relaxed"><ChipOf chip={FINDING_KIND[f.kind]} /> <span className="text-foreground">{f.text}</span></p>
            {f.cites.length > 0 && (
              <ul className="mt-1 flex flex-wrap gap-1.5 text-[11px]" aria-label="Its sources">
                {f.cites.map((c, i) => <Source key={`${f.n}:${i}`} k={k} c={c} />)}
              </ul>
            )}
            <p className="mt-0.5 text-[11px] text-muted-foreground">{findingMade(f)}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function DynastyCard({ d, find, findings = [] }: { d: VamsaRow; find: string; findings?: VamsaFinding[] }) {
  const [open, setOpen] = useState(false);
  const hits = find.length >= 2 ? d.names.filter((n) => foldPlain(n).includes(find)) : [];
  return (
    <li className="mb-3">
      <details className="rounded-lg border border-border bg-card px-4 py-2" onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
        <summary className="cursor-pointer text-sm">
          <span className="font-semibold text-foreground">{d.title || d.key}</span>
          <span className="ml-2 text-muted-foreground">from {d.anchor}{d.father ? `, son of ${d.father}` : ''}</span>
          <span className="ml-2 text-xs text-muted-foreground" title={d.works.map((w) => WORK_TITLE[w] ?? w).join('; ')}>
            told by {d.works.length} text{d.works.length === 1 ? '' : 's'}
          </span>
          {hits.length > 0 && <span className="ml-2 text-xs text-burgundy">found: {hits.slice(0, 4).join(', ')}</span>}
          {findings.length > 0 && <span className="ml-2 text-xs text-burgundy">{findings.length} finding{findings.length === 1 ? '' : 's'}</span>}
        </summary>
        <p className="mt-1 text-xs text-muted-foreground">{vamsaCountsText(d.counts)}</p>
        {open && <Findings k={d.key} items={findings} />}
        {open && <Generations k={d.key} />}
      </details>
    </li>
  );
}

function Failure({ error }: { error: string | null }) {
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <p>The vaṃśas could not be read: {error ?? 'no answer'}</p>
      </CardContent>
    </Card>
  );
}

function Body() {
  const [find, setFind] = useState('');
  const q = useQuery({ queryKey: ['index-vamsas'], queryFn: () => loadVamsas(null), staleTime: 10 * 60 * 1000 });
  const r = q.data;
  // VAMSA_FINDINGS_SITE_2026_11_19: one read for every dynasty's findings; nothing shown until C31 is pasted
  const fq = useQuery({ queryKey: ['index-vamsa-findings'], queryFn: loadVamsaFindings, staleTime: 10 * 60 * 1000 });
  const findingsOf = useMemo(() => {
    const m: Record<string, VamsaFinding[]> = {};
    if (fq.data && fq.data.ok) for (const x of fq.data.rows) m[x.key] = Array.isArray(x.findings) ? x.findings : [];
    return m;
  }, [fq.data]);
  const f = foldPlain(find);
  const all = useMemo(() => (r && r.ok ? [...r.rows].sort((a, b) => a.ord - b.ord || a.key.localeCompare(b.key)) : []), [r]);
  const shown = f.length >= 2
    ? all.filter((d) => d.names.some((n) => foldPlain(n).includes(f)) || foldPlain(d.anchor).includes(f) || foldPlain(d.title).includes(f))
    : all;
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Helmet><title>Sūryavaṃśa and Candravaṃśa | Working Corpus | Srangam</title></Helmet>
      <CorpusNav />
      <p className="mb-2 flex flex-wrap gap-4 text-sm">
        <Link to={GENEALOGIES} className={`inline-flex items-center gap-1 ${LINK}`}><ChevronLeft className="h-4 w-4" aria-hidden="true" />Genealogies</Link>
        <Link to={DYNASTIES} className={LINK}>The dynasties, one text at a time</Link>
      </p>
      <header className="mb-6">
        <h1 className="flex items-center gap-2 font-serif text-3xl font-semibold text-foreground">
          <Sun className="h-7 w-7 text-burgundy" aria-hidden="true" /> Sūryavaṃśa and Candravaṃśa
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          The great dynasties from their founders, generation by generation, as each text that tells them names each king:
          the Viṣṇupurāṇa, the Bhāgavatapurāṇa, the Harivaṃśa, the Rāmāyaṇa, the Mahābhārata&apos;s Ādiparvan and the
          other Purāṇas the desk reads. Open a dynasty to see where the texts agree and where they differ, each name with its
          verse, and what Dikshitar&apos;s Purāṇa Index and Raychaudhuri say beside it.
        </p>
      </header>
      <Guide />

      {q.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>}
      {r && !r.ok && r.refused && <CorpusRefused message={r.error} />}
      {r && !r.ok && !r.refused && r.missing && (
        <Card><CardContent className="pt-6 text-sm text-muted-foreground">
          The vaṃśas are not switched on yet. The dynasties of each text are at <Link to={DYNASTIES} className={LINK}>Dynasties</Link>.
        </CardContent></Card>
      )}
      {r && !r.ok && !r.refused && !r.missing && <Failure error={r.error} />}
      {r && r.ok && all.length === 0 && <p className="text-muted-foreground">No vaṃśa has been sent from the desk yet.</p>}
      {r && r.ok && all.length > 0 && (
        <>
          <label className="mb-4 flex max-w-md items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span className="sr-only">Find a king in the dynasties</span>
            <Input value={find} onChange={(e) => setFind(e.target.value)} placeholder="Find a king (Rama, Harishchandra, Yudhishthira, Bharata)" />
          </label>
          {shown.length === 0 && <p className="text-muted-foreground">No dynasty here has that name.</p>}
          {VAMSA_ORDER.map((v) => {
            const ds = shown.filter((d) => d.vamsa === v);
            if (!ds.length) return null;
            const Icon = v === 'surya' ? Sun : Moon;
            return (
              <section key={v} className="mb-6" aria-label={VAMSA_TITLE[v]}>
                <h2 className="flex items-center gap-2 font-serif text-xl font-semibold text-foreground">
                  <Icon className="h-5 w-5 text-burgundy" aria-hidden="true" /> {VAMSA_TITLE[v]}
                </h2>
                <p className="mb-3 mt-1 text-sm text-muted-foreground">{VAMSA_ABOUT[v]}</p>
                <ul aria-label={`The dynasties of the ${VAMSA_TITLE[v]}`}>
                  {ds.map((d) => <DynastyCard key={d.key} d={d} find={f} findings={findingsOf[d.key]} />)}
                </ul>
              </section>
            );
          })}
          <p className="mt-6 text-xs text-muted-foreground">{VAMSA_CREDIT}</p>
        </>
      )}
    </div>
  );
}

export default function CorpusVamsas() {
  return (
    <>
      <Helmet><meta name="robots" content="noindex, nofollow" /></Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}
