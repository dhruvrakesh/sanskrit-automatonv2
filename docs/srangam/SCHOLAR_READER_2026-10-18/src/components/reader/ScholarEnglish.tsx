/**
 * A verse's scholarly English in the corpus reader - SCHOLAR_READER_2026_10_18.
 *
 * Shown above the working (machine) English, which folds under it. Labelled for what it is: the scholarly English,
 * a sentence's range when it runs over several verses, and its standing (judged faithful, flagged by the judge, its
 * Sanskrit in doubt, read by a person). Its notes and doubts, who made it and who judged it are in a small popover.
 * A verse whose sentence is given with an earlier verse says so. A *term* is in italics; nothing is HTML.
 */
import { Info } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { displayTranslation } from '@/lib/corpusDisplay';
import { emphasisParts, engineName, scholarStatus, type ScholarReading } from '@/lib/scholarReading';

const TONE: Record<string, string> = {
  read: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
  passed: 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200',
  flagged: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  doubt: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200',
  other: 'bg-muted text-muted-foreground',
};

export function Emphasised({ text }: { text: string }) {
  return (
    <>
      {emphasisParts(text).map((x, i) => (x.em ? <em key={i}>{x.text}</em> : <span key={i}>{x.text}</span>))}
    </>
  );
}

function AboutScholar({ s }: { s: ScholarReading }) {
  const st = scholarStatus(s);
  const n = s.notes.length;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded px-0.5 normal-case tracking-normal text-burgundy hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
          aria-label="About the scholarly English"
          title="Its notes, and how it was made and checked"
        >
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
          {n > 0 ? <span>{n === 1 ? '1 note' : `${n} notes`}</span> : null}
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-96 max-w-[calc(100vw-2rem)] text-xs leading-relaxed">
        {n > 0 && (
          <ol className="mb-3 list-decimal space-y-1.5 pl-4">
            {s.notes.map((x, i) => (
              <li key={i}>
                {x.anchor ? <><span className="font-semibold"><Emphasised text={x.anchor} /></span>: </> : null}
                <Emphasised text={x.note} />
              </li>
            ))}
          </ol>
        )}
        {s.doubts && (
          <p className="mb-3"><span className="font-semibold">The translator&apos;s doubt:</span> <Emphasised text={s.doubts} /></p>
        )}
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1">
          {s.engine && (
            <>
              <dt className="text-muted-foreground">Made by</dt>
              <dd>{engineName(s.engine)}{s.madeAt ? `, ${s.madeAt.slice(0, 10)}` : ''}; read by a critic and revised</dd>
            </>
          )}
          <dt className="text-muted-foreground">Standing</dt>
          <dd>{st.title}</dd>
        </dl>
        <p className="mt-2 text-muted-foreground">
          Translated afresh from the Sanskrit in the register of an unabridged critical translation: every word
          rendered, names and terms kept and explained. The working English beside it is the faster machine translation.
        </p>
      </PopoverContent>
    </Popover>
  );
}

export default function ScholarEnglish({ s }: { s: ScholarReading }) {
  if (!s.text) {
    return (
      <p className="text-sm italic text-muted-foreground" data-scholar="with">
        {s.with ? `Its scholarly English is given with the sentence at ${s.with}.` : 'Its scholarly English is given with the verse before it.'}
      </p>
    );
  }
  const st = scholarStatus(s);
  return (
    <div data-scholar="english">
      <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span>Scholarly English</span>
        {s.range && <span className="font-mono normal-case tracking-normal text-burgundy" title="One Sanskrit sentence over these verses, translated whole">{s.range}</span>}
        <span className={`rounded px-1.5 py-0.5 normal-case tracking-normal ${TONE[st.key]}`} title={st.title}>{st.label}</span>
        <AboutScholar s={s} />
      </div>
      <p lang="en" className="whitespace-pre-line font-serif leading-relaxed text-foreground">
        <Emphasised text={displayTranslation(s.text)} />
      </p>
    </div>
  );
}
