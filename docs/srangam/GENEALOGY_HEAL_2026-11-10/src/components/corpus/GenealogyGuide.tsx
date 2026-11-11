/**
 * GENEALOGY_HEAL_2026_11_10 - the genealogy pages in plain words, and an epithet sent to the person it names.
 *
 * GenealogyGuide: "How to read this page", closed until opened: what a line is, the numbers, the strip, the chips,
 * two fathers, epithets, "a name only", and what a line is not yet (src/lib/indexSite.ts GUIDE).
 * EpithetNote: for an entry the index defines as another ("Kaunteya, the son of Kuntī, = Arjuna"; C26), the person or
 * persons it names, each a link to that person's own line. Nothing from the database is rendered as HTML.
 */
import { Link } from 'react-router-dom';
import { HelpCircle, Users } from 'lucide-react';
import { epithetHow, epithetKind, GUIDE, personHref, type IndexPerson } from '@/lib/indexSite';

const LINK = 'text-burgundy hover:underline';

export function GenealogyGuide({ open = false }: { open?: boolean }) {
  return (
    <details className="mb-5 rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm" open={open}>
      <summary className="flex cursor-pointer items-center gap-2 font-medium text-foreground">
        <HelpCircle className="h-4 w-4 text-burgundy" aria-hidden="true" /> How to read this page
      </summary>
      <dl className="mt-2 space-y-2 pb-1">
        {GUIDE.map((g) => (
          <div key={g.term}>
            <dt className="font-semibold text-foreground">{g.term}</dt>
            <dd className="text-muted-foreground">{g.text}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

export function EpithetNote({ person, source }: { person: Pick<IndexPerson, 'head' | 'same_as' | 'gloss'>; source: string }) {
  const kind = epithetKind(person);
  if (!kind) return null;
  const xs = person.same_as ?? [];
  const gloss = person.gloss ? <> (&ldquo;{person.gloss}&rdquo;)</> : null;
  const links = xs.map((x, i) => (
    <span key={x.entry}>
      {i > 0 ? (i === xs.length - 1 ? (kind === 'unsure' ? ' or ' : ' and ') : ', ') : ''}
      <Link to={personHref(source, x.entry)} className={`font-semibold ${LINK}`} title={`Told apart by: ${epithetHow(x.how)}`}>{x.head}</Link>
    </span>
  ));
  return (
    <div className="mb-4 flex items-start gap-2 rounded-md border border-indigo-400/40 bg-indigo-50/60 px-3 py-2 text-sm text-foreground dark:bg-indigo-950/30" role="note" aria-label="An epithet">
      <Users className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" aria-hidden="true" />
      <p>
        {kind === 'one' && <>{person.head}{gloss} is another name for {links}, not a person of its own (the index&apos;s entry reads &ldquo;= {xs[0].head}&rdquo;). Open it for the line.</>}
        {kind === 'group' && <>{person.head}{gloss} names {xs.length} persons: {links}. Open each for the line.</>}
        {kind === 'unsure' && <>{person.head}{gloss} is a name for {links}: the index has several entries of that name and does not say which is meant.</>}
      </p>
    </div>
  );
}
