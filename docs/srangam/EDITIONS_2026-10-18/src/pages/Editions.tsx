/**
 * /editions - the scholarly editions, open to everyone - EDITIONS_SITE_2026_10_18.
 *
 * Each edition is a static page the automaton writes (scripts/publish_editions.py): the Sanskrit beside a scholarly
 * English, with notes at the end of each chapter, its credits and its licence. This page lists them from
 * public/scholarly/index.json (src/lib/editions.ts). A failed load is shown as a failure, never as "none".
 */
import type { ReactNode } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BookOpen } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { loadEditions, madeOn, megabytes, type Edition } from '@/lib/editions';

const nf = new Intl.NumberFormat('en-IN');
const LINK = 'text-burgundy underline decoration-burgundy/40 underline-offset-2 hover:decoration-burgundy';

function Ext({ href, children }: { href?: string; children: ReactNode }) {
  if (!href) return <>{children}</>;
  return <a href={href} className={LINK} target="_blank" rel="noopener noreferrer">{children}</a>;
}

function EditionCard({ e }: { e: Edition }) {
  const made = madeOn(e.made_at);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="font-serif text-2xl">
          <a href={e.file} className="hover:text-burgundy">{e.title}</a>
        </CardTitle>
        {e.subtitle && <p className="text-muted-foreground">{e.subtitle}</p>}
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{nf.format(e.verses)} verses in scholarly English</Badge>
          <Badge variant="outline">{nf.format(e.passed)} passed the judge</Badge>
          {e.flagged > 0 && <Badge variant="outline">{nf.format(e.flagged)} marked &#8224; for a reader</Badge>}
        </div>
        {e.source.name && (
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">The Sanskrit: </span>
            <Ext href={e.source.url}>{e.source.name}</Ext>
            {e.source.credit && <>; {e.source.credit}</>}
            {e.source.licence && <>. <Ext href={e.source.licence_url}>{e.source.licence}</Ext></>}.
          </p>
        )}
        <p className="text-muted-foreground">
          <span className="font-medium text-foreground">The English: </span>
          made by {e.engines || 'the Sanskrit Automaton'}, judged verse by verse by {e.judge || 'a judge of another model family'}
          {e.licence.name && <>; shared under <Ext href={e.licence.url}>{e.licence.name}</Ext></>}.
        </p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-1">
          <a href={e.file} className={`font-medium ${LINK}`}>Read the edition</a>
          <span className="text-xs text-muted-foreground">
            {megabytes(e.bytes)}{made && <> &middot; made {made}</>}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Editions() {
  const q = useQuery({ queryKey: ['editions'], queryFn: () => loadEditions(), staleTime: 5 * 60 * 1000 });
  const r = q.data;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <Helmet>
        <title>Scholarly Editions | Srangam</title>
        <meta
          name="description"
          content="Sanskrit texts beside a scholarly English translation, with notes on each chapter and the credits of every source: the Devimahatmya and more, open to everyone."
        />
      </Helmet>

      <header className="mb-8">
        <h1 className="font-serif text-3xl font-semibold text-foreground flex items-center gap-3">
          <BookOpen className="w-7 h-7 text-burgundy" aria-hidden="true" />
          Scholarly Editions
        </h1>
        <p className="mt-3 text-muted-foreground leading-relaxed max-w-3xl">
          Each edition gives the Sanskrit beside an English in the register of an unabridged translation made from a
          critical edition, with notes at the end of each chapter and the translator's doubts about the reading. The
          English is a machine translation: Claude drafts it and a critic revises it; a judge from another model family
          reads every verse; a dagger (&#8224;) marks a verse the judge flagged that a person has not yet read. Read it
          beside the Sanskrit.
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          More texts, verse by verse: <Link to="/texts" className={LINK}>the published texts</Link>. Signed-in
          researchers can send corrections through <Link to="/corpus/corner" className={LINK}>the Researchers' Corner</Link>.
        </p>
      </header>

      {q.isLoading && (
        <div className="space-y-4" aria-busy="true">
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {r && !r.ok && (
        <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
          <CardContent className="pt-6 flex items-start gap-3 text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600" aria-hidden="true" />
            <div>
              <p className="font-semibold">The editions could not be loaded.</p>
              <p className="text-muted-foreground mt-1">This is a loading failure, not an empty list. Please try again shortly.</p>
              <p className="text-xs text-muted-foreground mt-2 font-mono">{r.error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {r && r.ok && r.editions.length === 0 && (
        <p className="text-muted-foreground">No edition is published yet.</p>
      )}

      {r && r.ok && r.editions.length > 0 && (
        <ul className="space-y-6">
          {r.editions.map((e) => (
            <li key={e.slug}><EditionCard e={e} /></li>
          ))}
        </ul>
      )}
    </div>
  );
}
