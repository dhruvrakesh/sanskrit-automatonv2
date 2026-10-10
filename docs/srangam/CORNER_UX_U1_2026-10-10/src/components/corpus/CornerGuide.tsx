/**
 * The parts of the Corner's guide - CORNER_UX_U1_2026_10_10 (the rules: src/lib/cornerGuide.ts).
 *
 *   OfferingStrip  the working corpus so far, in a line ("the offering so far"), with how many texts
 *                  still wait for their first story. Shared and quiet: no names, no ranks.
 *   TextShelf      before a text is chosen: where to begin (texts with English and no story yet),
 *                  the text chosen last time on this browser, "Surprise me".
 *   TextSummary    after: what the text has (stories, pictures, graphic novels) and where to read it.
 *   GoalPicker     what to make: a story, a picture, a graphic novel, or everything; and anthologies.
 *   ReadyList      what is ready to be asked for in this text, each with "Set it up", which only
 *                  fills the form below and goes to it: the desk is still asked by the form's button.
 * None of them asks the desk for anything.
 */
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Flame, Shuffle, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { imagesHref } from '@/lib/corpusMedia';
import { aboutUsd } from '@/lib/corner';
import {
  GOALS, loadOffering, OFFERING_KEY, offeringParts, textStateLine, untoldLine, untoldTexts,
  type Goal, type Suggestion, type TextLine, type TextState,
} from '@/lib/cornerGuide';

const LINK = 'font-medium text-burgundy underline decoration-burgundy/40 underline-offset-2 hover:decoration-burgundy';
const CHIP = 'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-burgundy/50';

/** The working corpus so far. From corner_offering() where the database has it (C13), else from the texts. */
export function OfferingStrip({ texts }: { texts: readonly TextLine[] }) {
  const q = useQuery({ queryKey: OFFERING_KEY, queryFn: loadOffering, staleTime: 5 * 60 * 1000 });
  const o = q.data?.ok ? q.data.rows[0] ?? null : null;
  if (q.isLoading) return null;
  const parts = offeringParts(o, texts);
  if (!parts.length) return null;
  const untold = untoldLine(texts);
  return (
    <section aria-label="The offering so far" className="flex items-start gap-2 text-sm text-muted-foreground">
      <Flame className="mt-0.5 h-4 w-4 shrink-0 text-burgundy" aria-hidden="true" />
      <p className="min-w-0 flex-1">
        <span lang="sa" className="font-devanagari text-foreground">यज्ञ</span>
        <span className="text-foreground"> · The offering so far: </span>
        {parts.map((t, i) => (
          // on a phone, the first three; the rest from a wider screen up
          <span key={t} className={i > 2 ? 'hidden sm:inline' : undefined}>{i > 0 ? ' · ' : ''}{t}</span>
        ))}
        .{untold && <span> {untold}.</span>}
      </p>
    </section>
  );
}

/** Before a text is chosen. */
export function TextShelf({ texts, last, onChoose }: {
  texts: readonly TextLine[]; last: TextLine | null; onChoose: (code: string) => void;
}) {
  const begin = untoldTexts(texts, 6).filter((t) => t.doc_code !== last?.doc_code);
  if (!begin.length && !last) return null;
  return (
    <section aria-labelledby="shelf-head" className="space-y-3 rounded-md border border-dashed border-border px-4 py-3">
      <h2 id="shelf-head" className="flex items-center gap-2 font-serif text-lg font-semibold text-foreground">
        <Sparkles className="h-4 w-4 text-burgundy" aria-hidden="true" /> Where to begin
      </h2>
      {last && (
        <p className="text-sm">
          <Button type="button" size="sm" variant="outline" className="h-8" onClick={() => onChoose(last.doc_code)}>
            Continue with {last.label}
          </Button>
        </p>
      )}
      {begin.length > 0 && (
        <>
          <p className="text-sm text-muted-foreground">
            These texts have English to work from and no story yet. Choose one, or any text in the list above.
          </p>
          <ul className="flex flex-wrap gap-2">
            {begin.map((t) => (
              <li key={t.doc_code}>
                <button type="button" className={`${CHIP} border-border hover:border-burgundy/60`} onClick={() => onChoose(t.doc_code)}>
                  <span className="text-foreground">{t.label}</span>
                  <span className="text-xs text-muted-foreground">{t.english.toLocaleString('en-IN')} in English</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

/** "Surprise me": another text, preferably one waiting for its first story. */
export function SurpriseButton({ onSurprise, disabled }: { onSurprise: () => void; disabled?: boolean }) {
  return (
    <Button type="button" size="sm" variant="ghost" className="h-8 gap-1.5 text-burgundy" onClick={onSurprise} disabled={disabled}>
      <Shuffle className="h-3.5 w-3.5" aria-hidden="true" /> Surprise me
    </Button>
  );
}

/** After a text is chosen: what it has, and where to read it. */
export function TextSummary({ text, state, ready }: { text: TextLine; state: TextState | null; ready: boolean }) {
  return (
    <div className="space-y-1 text-sm">
      <p className="text-muted-foreground">
        {text.hindi > 0 ? `${text.hindi.toLocaleString('en-IN')} in Hindi. ` : ''}
        {ready && state && <span className="text-foreground">{textStateLine(state)}.</span>}
      </p>
      <p className="flex flex-wrap gap-x-4 gap-y-1">
        <Link to={`/corpus/${encodeURIComponent(text.doc_code)}`} className={`inline-flex items-center gap-1 ${LINK}`}>
          <BookOpen className="h-3.5 w-3.5" aria-hidden="true" /> Read it
        </Link>
        <Link to={`/corpus/stories?doc=${encodeURIComponent(text.doc_code)}`} className={LINK}>Its stories</Link>
        <Link to={imagesHref(text.doc_code)} className={LINK}>Its pictures</Link>
      </p>
    </div>
  );
}

/** What to make. */
export function GoalPicker({ goal, counts, onGoal }: {
  goal: Goal; counts: Record<Exclude<Goal, 'all'>, number>; onGoal: (g: Goal) => void;
}) {
  return (
    <section aria-labelledby="goal-head" className="space-y-2">
      <h2 id="goal-head" className="font-serif text-lg font-semibold text-foreground">What would you like to make?</h2>
      <div role="group" aria-label="What to make" className="flex flex-wrap items-center gap-2">
        {GOALS.map((g) => {
          const on = goal === g.key;
          const n = g.key === 'all' ? 0 : counts[g.key];
          return (
            <button key={g.key} type="button" aria-pressed={on} title={g.what} onClick={() => onGoal(g.key)}
              className={`${CHIP} ${on ? 'border-burgundy bg-burgundy text-white' : 'border-border text-foreground hover:border-burgundy/60'}`}>
              {g.label}
              {n > 0 && <span className={`rounded-full px-1.5 text-xs ${on ? 'bg-white/20' : 'bg-muted text-muted-foreground'}`}>{n} ready</span>}
            </button>
          );
        })}
        <Link to="/corpus/corner?tab=anthologies" className={`${CHIP} border-transparent text-burgundy hover:underline`}>
          An anthology
        </Link>
      </div>
    </section>
  );
}

/** What is ready to be asked for in this text. */
export function ReadyList({ items, estimate, onSetUp, doc }: {
  items: readonly Suggestion[]; estimate: (s: Suggestion) => number; onSetUp: (s: Suggestion) => void; doc: string;
}) {
  if (!items.length) return null;
  return (
    <section aria-labelledby="ready-head" className="space-y-2">
      <h2 id="ready-head" className="font-serif text-lg font-semibold text-foreground">Ready in this text</h2>
      <ul className="grid gap-2 lg:grid-cols-2">
        {items.map((s) => {
          const est = estimate(s);
          return (
            <li key={s.key} className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-border px-3 py-2 text-sm">
              <div className="min-w-0 flex-1 space-y-0.5">
                <p className="font-medium text-foreground">{s.title}</p>
                <p className="text-xs text-muted-foreground">{s.why}</p>
                {s.fill.story_id && (
                  <Link to={`/corpus/stories/${encodeURIComponent(doc)}/${s.fill.story_id}`} className={`text-xs ${LINK}`}>See the story</Link>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {est > 0 && <span className="text-xs text-muted-foreground">{aboutUsd(est)}</span>}
                <Button type="button" size="sm" variant="outline" className="h-7 px-2.5 text-xs" onClick={() => onSetUp(s)}
                  aria-label={`Set it up: ${s.title}`}>
                  Set it up
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-muted-foreground">
        &ldquo;Set it up&rdquo; fills in the form below; nothing is asked until you press Ask the desk there.
      </p>
    </section>
  );
}

