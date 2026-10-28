/**
 * A name of ours in the indexes - INDEX_SITE_2026_10_25: on /corpus/names/:canonical, the persons of the three indexes
 * tied to this name (each a link to its line of descent, /corpus/genealogies/:source/:entry) and what the indexes state
 * of it, with the entry's own words and references (corpus_reader_index_of_name, docs/cloud/C21 in the automaton repo).
 * Shown only when there is something to show: before C21, or for a name the indexes do not tie, nothing is drawn.
 * B2_SITE_2026_10_28 (docs/cloud/C23): and what the historians say of the name, in the book's order, with the book's
 * words and page ("What the historians say"); before C23, or for a name they do not speak of, nothing more is drawn.
 */
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { GitBranch, ScrollText } from 'lucide-react';
import ScholarClaims from '@/components/corpus/ScholarClaims';
import {
  GENEALOGIES, groupStatements, loadIndexOfName, nameHrefOf, personHref, relationLabel, SOURCE_SHORT, SOURCES,
} from '@/lib/indexSite';

const LINK = 'text-burgundy hover:underline';
const SHOWN = 12;
const CLAIMS_SHOWN = 8;

/** A name in a statement: a link to its page when it is another of our names. */
function nameOf(n: string, c: string | null, here: string) {
  return c && c !== here
    ? <Link to={nameHrefOf(c)} className={LINK}>{n}</Link>
    : <span className="text-foreground">{n}</span>;
}

export default function InTheIndexes({ canonical }: { canonical: string }) {
  const q = useQuery({
    queryKey: ['mirror', 'index-of-name', canonical],
    queryFn: () => loadIndexOfName(canonical),
    staleTime: 10 * 60 * 1000,
  });
  const v = q.data?.ok ? q.data.value : null;
  const claims = v?.claims ?? [];
  if (!v || (!v.persons.length && !v.statements.length && !claims.length)) return null;
  const claimsMore = (Number(v.claims_n) || claims.length) - Math.min(claims.length, CLAIMS_SHOWN);
  const historians = claims.length > 0 && (
    <section aria-labelledby="historians-say" className="mb-8">
      <h2 id="historians-say" className="mb-1 flex items-center gap-2 font-serif text-xl font-semibold text-foreground">
        <ScrollText className="h-5 w-5 text-burgundy" aria-hidden="true" /> What the historians say
      </h2>
      <p className="mb-2 max-w-3xl text-sm text-muted-foreground">
        {claims.every((c) => c.work === 'phai1923')
          ? <>The claims of Hemchandra Raychaudhuri&apos;s Political History of Ancient India (1923) that speak of {canonical},</>
          : <>The claims of the historians&apos; works that speak of {canonical},</>}{' '}
        in the book&apos;s order, each with the book&apos;s words as the scan reads them and its page.
      </p>
      <ScholarClaims claims={claims.slice(0, CLAIMS_SHOWN)} here={canonical} label={`What the historians say of ${canonical}`} />
      {claimsMore > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">and {claimsMore} more {claimsMore === 1 ? 'claim' : 'claims'} of the book.</p>
      )}
    </section>
  );
  if (!v.persons.length && !v.statements.length) return <>{historians}</>;
  const order = (s: string) => { const i = (SOURCES as readonly string[]).indexOf(s); return i < 0 ? 9 : i; };
  const lined = v.persons.filter((p) => p.has_line).sort((a, b) => order(a.source) - order(b.source));
  const said = v.statements.slice(0, SHOWN);
  const more = (Number(v.statements_n) || 0) - said.length;
  return (
    <>
    <section aria-labelledby="in-the-indexes" className="mb-8">
      <h2 id="in-the-indexes" className="mb-1 flex items-center gap-2 font-serif text-xl font-semibold text-foreground">
        <GitBranch className="h-5 w-5 text-burgundy" aria-hidden="true" /> In the indexes
      </h2>
      <p className="mb-3 max-w-3xl text-sm text-muted-foreground">
        The persons of the Purāṇa Index, the Mahābhārata index and the Vedic Index tied to {canonical}, and what the
        indexes state of the name, in the entries&apos; own words. <Link to={GENEALOGIES} className={LINK}>All genealogies</Link>.
      </p>
      {lined.length > 0 && (
        <ul className="mb-3 flex flex-wrap gap-2" aria-label="Lines of descent">
          {lined.map((p) => (
            <li key={`${p.source}:${p.entry}`} className="rounded-md border border-border px-2.5 py-1.5 text-sm">
              <Link to={personHref(p.source, p.entry)} className="font-serif text-foreground hover:text-burgundy">{p.head}</Link>
              <span className="ml-1.5 text-xs text-muted-foreground">
                {SOURCE_SHORT[p.source] ?? p.source} &middot; {p.parents} {p.parents === 1 ? 'parent' : 'parents'}, {p.children}{' '}
                {p.children === 1 ? 'child' : 'children'}
              </span>
            </li>
          ))}
        </ul>
      )}
      {said.length > 0 && (
        <div role="group" aria-label="What the indexes state">
          {groupStatements(said).map((g) => (
            <div key={g.key} className="mb-2">
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{g.label}</h3>
              <ul className="space-y-1.5 text-sm">
                {g.rows.map((s) => (
                  <li key={s.key}>
                    {nameOf(s.subject, s.subject_canonical, canonical)} <i>{relationLabel(s.relation)}</i>{' '}
                    {nameOf(s.object, s.object_canonical, canonical)}
                    <span className="text-xs text-muted-foreground">
                      {' '}&middot; {SOURCE_SHORT[s.source] ?? s.source}, the entry {s.stated_in}
                      {s.words ? <> &middot; &ldquo;{s.words}&rdquo;</> : null}
                      {s.refs?.length ? ` (${s.refs.join('; ')})` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
      {more > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">and {more} more {more === 1 ? 'statement' : 'statements'} in the indexes.</p>
      )}
    </section>
    {historians}
    </>
  );
}
