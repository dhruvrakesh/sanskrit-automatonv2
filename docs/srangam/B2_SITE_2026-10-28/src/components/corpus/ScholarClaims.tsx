/**
 * The scholars' claims - B2_SITE_2026_10_28 (docs/cloud/C23 in the automaton repo).
 *
 * A claim of a scholar's work as the desk read it from the work's scan (scholar_claims.py): the claim in words, the
 * book's own words for it as the scan reads them (found on the page: exactly, or nearly), the page as the book prints
 * it, the stance (the book asserts it, reports it from its sources, doubts it or rejects it), the names it speaks of
 * tied to ours (certain: the same name, or with its number; probable: a spelling, a variant, a plural), and the works
 * it cites, with ours linked where we hold them. Public-domain works only (Hemchandra Raychaudhuri, 1923). Nothing
 * from the database is rendered as HTML.
 */
import { Link } from 'react-router-dom';
import { bookTitle } from '@/lib/corpusLibrary';
import { claimPage, nameHrefOf, tieLabel, WORK_SHORT, type Claim } from '@/lib/indexSite';

const LINK = 'text-burgundy hover:underline';

const STANCE: Record<string, string> = {
  reports: 'reports it from his sources',
  doubts: 'doubts it',
  rejects: 'rejects it',
};

/** One of the claim's names, tied to one of ours: a link to the name's page (unless it is this page's name). */
function Tie({ name, canonical, how, here }: { name: string; canonical: string | null; how: string | null; here?: string | null }) {
  const t = tieLabel(how);
  if (!canonical || !t) return null;
  const label = canonical === name ? canonical : `${name} as ${canonical}`;
  return (
    <span title={`Tied to our name by ${how}`}>
      {canonical === here ? <span className="text-foreground">{label}</span> : <Link to={nameHrefOf(canonical)} className={LINK}>{label}</Link>}
      <span className="text-muted-foreground"> ({t})</span>
    </span>
  );
}

export function ClaimItem({ c, here, compact = false }: { c: Claim; here?: string | null; compact?: boolean }) {
  const who = WORK_SHORT[c.work] ?? c.work;
  const stance = c.stance ? STANCE[c.stance] : undefined;
  const ties = [
    { k: 's', name: c.subject, canonical: c.subject_canonical, how: c.subject_how },
    { k: 'o', name: c.object ?? '', canonical: c.object_canonical, how: c.object_how },
  ].filter((x, i, a) => x.canonical && tieLabel(x.how) && a.findIndex((y) => y.canonical === x.canonical) === i);
  const cites = (c.cites ?? []).filter((x) => x && (x.printed || x.work)).slice(0, compact ? 2 : 6);
  return (
    <li className="border-b border-border py-2 last:border-b-0">
      <p className="text-sm text-foreground">{c.claim}</p>
      {c.quote && (
        <blockquote lang="en" className="my-1 rounded-md border-l-4 border-violet-400/60 bg-muted/50 px-3 py-1 font-serif text-sm text-foreground/90">
          &ldquo;{c.quote}&rdquo;
        </blockquote>
      )}
      <p className="text-xs text-muted-foreground">
        {who}, {claimPage(c)}
        {c.quote_check === 'exact' ? ' · the words as on the page' : c.quote_check === 'close' ? ' · the words nearly as on the page' : ''}
        {stance ? ` · ${who} ${stance}` : ''}
        {c.hedge ? ` · "${c.hedge}"` : ''}
      </p>
      {ties.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Our names:{' '}
          {ties.map((x, i) => <span key={x.k}>{i > 0 ? ', ' : ''}<Tie name={x.name} canonical={x.canonical} how={x.how} here={here} /></span>)}
        </p>
      )}
      {cites.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Cites:{' '}
          {cites.map((x, i) => (
            <span key={`${x.printed ?? ''}-${i}`}>
              {i > 0 ? '; ' : ''}{x.work ?? ''}{x.printed && x.printed !== x.work ? ` ${x.printed}` : ''}
              {x.ours ? <> (<Link to={`/corpus/${encodeURIComponent(x.ours)}`} className={LINK}>ours: {bookTitle({ doc_code: x.ours }).title}</Link>)</> : null}
            </span>
          ))}
        </p>
      )}
    </li>
  );
}

export default function ScholarClaims({ claims, here, label, compact = false }: {
  claims: Claim[]; here?: string | null; label: string; compact?: boolean;
}) {
  if (!claims.length) return null;
  return (
    <ul aria-label={label}>
      {claims.map((c) => <ClaimItem key={c.key} c={c} here={here} compact={compact} />)}
    </ul>
  );
}
