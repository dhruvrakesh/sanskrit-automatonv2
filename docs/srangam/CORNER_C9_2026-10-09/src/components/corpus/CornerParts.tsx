/**
 * Small parts shared by the Researchers' Corner and its anthologies - CORNER_C9_2026_10_09.
 */
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, Info, Lock } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { CorpusRefused } from '@/components/corpus/CorpusGate';
import { statusLabel, statusTone, TONE_CLASS, type CornerResult } from '@/lib/corner';

/** A loading problem: quiet when C9 is not applied yet, a refusal as a refusal. */
export function CornerProblem({ r, what }: { r: CornerResult<unknown>; what: string }) {
  if (r.refused) return <CorpusRefused message={r.error} />;
  if (r.missing) {
    return (
      <p className="flex items-start gap-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        {what} is not available here yet.
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

/** For readers of the corpus who are not invited researchers or editors. */
export function CornerClosed() {
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <Lock className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">The Researchers&apos; Corner is for invited researchers and editors.</p>
          <p className="mt-1 text-muted-foreground">
            You can read the published anthologies here. To ask the desk for stories and pictures yourself, ask the
            editor for an invitation link and open it while signed in with the address it was sent to.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

/** A request's status, in words. */
export function RequestBadge({ status }: { status: string | null | undefined }) {
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${TONE_CLASS[statusTone(status)]}`}>
      {statusLabel(status)}
    </span>
  );
}

/** What the server said about an action: its sentence, a link on to the requests when it took. */
export function ActionNote({ ok, text, mineLink = false }: { ok: boolean; text: string | null | undefined; mineLink?: boolean }) {
  if (!text) return null;
  if (!ok) {
    return (
      <p role="alert" className="flex items-start gap-1.5 text-sm text-red-700 dark:text-red-300">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> <span>{text}</span>
      </p>
    );
  }
  return (
    <p role="status" className="flex flex-wrap items-start gap-1.5 text-sm text-emerald-800 dark:text-emerald-300">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> <span>{text}</span>
      {mineLink && <Link to="/corpus/corner?tab=mine" className="text-burgundy hover:underline">See your requests</Link>}
    </p>
  );
}
