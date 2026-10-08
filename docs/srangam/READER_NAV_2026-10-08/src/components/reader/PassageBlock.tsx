/**
 * One passage in a reader - READER_NAV_2026_10_08. Used by /texts/:docCode and /corpus/:docCode.
 *
 * The reference sits in the margin (scan page and passage, with the edition's own number under it
 * when there is one), so the text starts at the same place every time. On wide screens the
 * Sanskrit and IAST stand beside the English and Hindi (the "source + translation" layout of the
 * Booksmith editions and the HTML exports); on phones, and when the reader chooses "stacked", they
 * follow one another. Every note is a tooltip or a small popover; nothing stored is changed:
 * misread lines are shown as read, muted and labelled, and scanner noise is folded, not removed.
 */
import { useState, type ReactNode } from 'react';
import { Info } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  displayTranslation, gutterRef, isLowQuality, passageWhere, sourceLines, splitDecoration, type SourceLine,
} from '@/lib/corpusDisplay';
import type { ReaderPrefs } from '@/lib/readerPrefs';

export interface ReaderPassage {
  page_no: number;
  idx: number;
  verse_ref: string | null;
  sanskrit: string | null;
  iast: string | null;
  translation: string | null;
  hindi?: string | null;
  quality_score: number | null;
  text_type?: string | null;
  engine?: string | null;
  translated_at?: string | null;
  translation_qa?: number | null;
}

export const TYPE_NOTES: Record<string, string> = {
  mula: 'The root text.',
  tika: 'A commentary on the root text.',
  prose: 'Prose.',
  colophon: 'The closing line of a chapter or section.',
  noise: 'Scanner noise: marks on the page that are not text.',
  frontmatter: "The printed book's front matter.",
};

const pct = (x: number) => `${Math.round(x * 100)}%`;

function Lines({ lines, note }: { lines: SourceLine[]; note: string }) {
  return (
    <>
      {lines.map((l, i) =>
        l.misread ? (
          <span key={i} className="block italic text-muted-foreground/70" title={note}>
            {l.text || ' '}
            <span className="sr-only"> (misread by the scanner)</span>
          </span>
        ) : (
          <span key={i} className="block">{l.text || ' '}</span>
        ),
      )}
    </>
  );
}

function About({ p }: { p: ReaderPassage }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center rounded p-0.5 hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
          aria-label="About this passage"
          title="About this passage"
        >
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 text-xs leading-relaxed">
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1">
          <dt className="text-muted-foreground">Where</dt>
          <dd>{passageWhere(p)}</dd>
          {typeof p.quality_score === 'number' && p.quality_score > 0 && (
            <>
              <dt className="text-muted-foreground">Scan</dt>
              <dd>OCR confidence {pct(p.quality_score)}{isLowQuality(p.quality_score) ? ': the printed page was hard to read' : ''}</dd>
            </>
          )}
          {p.engine && (
            <>
              <dt className="text-muted-foreground">Translation</dt>
              <dd>{p.engine}{p.translated_at ? `, ${String(p.translated_at).slice(0, 10)}` : ''}</dd>
            </>
          )}
          {typeof p.translation_qa === 'number' && (
            <>
              <dt className="text-muted-foreground">Check</dt>
              <dd>automatic translation check {pct(p.translation_qa)}</dd>
            </>
          )}
          {p.text_type && (
            <>
              <dt className="text-muted-foreground">Kind</dt>
              <dd>{TYPE_NOTES[p.text_type] ?? p.text_type}</dd>
            </>
          )}
        </dl>
        <p className="mt-2 text-muted-foreground">Read by machine from the scan and translated by machine; not reviewed.</p>
      </PopoverContent>
    </Popover>
  );
}

export default function PassageBlock({
  p, prefs, highlighted = false, extra,
}: {
  p: ReaderPassage;
  prefs: ReaderPrefs;
  highlighted?: boolean;
  /** More controls for the passage's foot (the corpus reader's "similar passages"). */
  extra?: ReactNode;
}) {
  const [unfolded, setUnfolded] = useState(false);
  const id = `p${p.page_no}-${p.idx}`;
  const where = passageWhere(p);
  const mark = highlighted ? ' rounded-md bg-amber-50/70 dark:bg-amber-950/30' : '';

  if (p.text_type === 'noise' && !prefs.noise && !unfolded) {
    return (
      <li id={id} data-page={p.page_no} className={`scroll-mt-40 flex items-center gap-3 border-b border-border py-2 text-xs text-muted-foreground${mark}`}>
        <a href={`#${id}`} className="w-11 shrink-0 text-right font-mono sm:w-[3.25rem]" title={where}>{gutterRef(p)}</a>
        <span title={TYPE_NOTES.noise}>Scanner noise, not text.</span>
        <button type="button" onClick={() => setUnfolded(true)} className="underline hover:text-foreground">Show it</button>
      </li>
    );
  }

  const side = prefs.layout === 'side';
  const sa = splitDecoration(p.sanskrit);
  const ia = splitDecoration(p.iast);
  const lines = sourceLines(sa.text, ia.text);
  const en = displayTranslation(p.translation);
  const hi = p.hindi && p.hindi.trim() ? displayTranslation(p.hindi) : '';
  const typeChip = p.text_type && !['mula', 'noise', 'colophon'].includes(p.text_type) ? p.text_type : null;

  return (
    <li
      id={id}
      data-page={p.page_no}
      className={`scroll-mt-40 border-b border-border py-4 last:border-b-0 target:rounded-md target:bg-amber-50/70 dark:target:bg-amber-950/30${mark}`}
    >
      <div className="grid grid-cols-[2.75rem_minmax(0,1fr)] gap-x-3 sm:grid-cols-[3.25rem_minmax(0,1fr)] sm:gap-x-4">
        <div className="pt-1 text-right">
          <a href={`#${id}`} className="font-mono text-xs text-muted-foreground hover:text-foreground" title={`${where}. A link to this passage.`}>
            {gutterRef(p)}
          </a>
          {p.verse_ref && (
            <div className="mt-0.5 break-words font-mono text-[11px] text-burgundy" title="The edition's own number for this passage">
              {p.verse_ref}
            </div>
          )}
        </div>

        <div className="min-w-0">
          {p.text_type === 'colophon' && (
            <p className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground" title={TYPE_NOTES.colophon}>Colophon</p>
          )}
          {/* READER_MARKS_2026_10_07: an ornamental rule of the page, drawn, not printed as text */}
          {(sa.rule || ia.rule) && <div aria-hidden="true" className="mb-3 h-px w-24 bg-border" />}

          <div className={side ? 'lg:grid lg:grid-cols-2 lg:gap-x-8' : ''}>
            <div className="min-w-0">
              <p lang="sa" className="font-devanagari text-lg leading-relaxed text-foreground">
                <Lines lines={lines.sa} note="The scanner misread this line. It is shown as it was read." />
              </p>
              {prefs.iast && lines.ia.length > 0 && (
                <p lang="sa-Latn" className="mt-1.5 text-sm italic leading-relaxed text-muted-foreground">
                  <Lines lines={lines.ia} note="The transliteration of a line the scanner misread." />
                </p>
              )}
            </div>
            <div className={`min-w-0 ${side ? 'mt-3 lg:mt-0 lg:border-l lg:border-border lg:pl-8' : 'mt-3'}`}>
              {prefs.english && en && (
                <p lang="en" className="whitespace-pre-line font-serif leading-relaxed text-foreground">{en}</p>
              )}
              {prefs.english && !en && <p className="text-sm italic text-muted-foreground">Not translated yet.</p>}
              {prefs.hindi && hi && (
                <p lang="hi" className="mt-2 whitespace-pre-line font-devanagari leading-relaxed text-foreground/90">{hi}</p>
              )}
            </div>
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {isLowQuality(p.quality_score) && (
              <span
                className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                title={`OCR confidence ${pct(p.quality_score as number)}: the printed page was hard to read, so the Sanskrit may hold misreadings.`}
              >
                hard-to-read scan
              </span>
            )}
            {typeChip && <span className="rounded bg-muted px-1.5 py-0.5" title={TYPE_NOTES[typeChip] ?? typeChip}>{typeChip}</span>}
            <About p={p} />
            {extra}
          </div>
        </div>
      </div>
    </li>
  );
}
