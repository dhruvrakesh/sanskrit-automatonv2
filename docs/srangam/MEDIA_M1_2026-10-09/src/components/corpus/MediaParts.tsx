/**
 * Small parts shared by the pictures and the graphic novels - CORPUS_MEDIA_C8_2026_10_09.
 */
import { Link } from 'react-router-dom';
import { AlertTriangle, Info, ShieldAlert, Sparkles } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { CorpusRefused } from '@/components/corpus/CorpusGate';
import { atHref } from '@/lib/corpusLibrary';
import { citeParts, GENERATED_LABEL, type MediaResult } from '@/lib/corpusMedia';

export function MediaProblem({ r, what }: { r: MediaResult<unknown>; what: string }) {
  if (r.refused) return <CorpusRefused message={r.error} />;
  if (r.missing) {
    return (
      <p className="flex items-start gap-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        {what} are not available here yet.
      </p>
    );
  }
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">{what} could not be loaded.</p>
          <p className="mt-1 text-muted-foreground">This is a loading failure. Please try again shortly.</p>
          {r.error && <p className="mt-2 font-mono text-xs text-muted-foreground">{r.error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

/** Nothing for approved; a marked badge for what only editors see. */
export function MediaStatus({ status }: { status: string | null | undefined }) {
  if (status === 'approved') return null;
  return (
    <span
      className="inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
      title="Not approved yet: editors see it, readers do not"
    >
      <ShieldAlert className="h-3 w-3" aria-hidden="true" /> {status ?? 'unreviewed'}
    </span>
  );
}

export function GeneratedNote({ model, className = '' }: { model?: string | null; className?: string }) {
  return (
    <p className={`flex items-start gap-1.5 text-xs text-muted-foreground ${className}`}>
      <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>{GENERATED_LABEL}{model ? ` Drawn by ${model}.` : ''}</span>
    </p>
  );
}

/** A caption with its bracketed citations as links into the text. */
export function CitedText({ text, docCode, lang }: { text: string | null | undefined; docCode: string; lang?: string }) {
  if (!text) return null;
  return (
    <span lang={lang}>
      {citeParts(text).map((p, i) => (p.refs.length ? (
        <span key={i} className="whitespace-nowrap font-mono text-xs">
          [{p.refs.map((r, j) => (
            <span key={r + j}>
              {j > 0 && ', '}
              <Link to={atHref(docCode, r)} className="text-burgundy hover:underline" title={`Scan page ${r.split('.')[0]}, passage ${r.split('.')[1]}`}>{r}</Link>
            </span>
          ))}]
        </span>
      ) : <span key={i}>{p.text}</span>))}
    </span>
  );
}
