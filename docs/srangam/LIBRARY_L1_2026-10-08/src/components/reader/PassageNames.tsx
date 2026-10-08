/**
 * The names in one passage, as chips - CORPUS_LIBRARY_C6_2026_10_08. Used by /corpus/:docCode.
 *
 * Each chip opens a small card: the kind of name, the desk's note on it, how the passage spells
 * it, and a link to every passage that names it (/corpus/names/:canonical). Machine-recognised.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { nameHref, type PageName } from '@/lib/corpusLibrary';

const SHOW = 6;

const KIND_ONE: Record<string, string> = {
  person: 'Person', deity: 'Deity', place: 'Place', people: 'A people or clan', river: 'River', mountain: 'Mountain', other: 'Name',
};

const KIND_CLASS: Record<string, string> = {
  deity: 'border-amber-500/50 text-amber-900 dark:text-amber-200',
  person: 'border-sky-600/40 text-sky-900 dark:text-sky-200',
  place: 'border-emerald-600/40 text-emerald-900 dark:text-emerald-200',
  river: 'border-cyan-600/40 text-cyan-900 dark:text-cyan-200',
  mountain: 'border-stone-500/50 text-stone-800 dark:text-stone-200',
  people: 'border-violet-600/40 text-violet-900 dark:text-violet-200',
};

export default function PassageNames({ names }: { names: PageName[] }) {
  const [all, setAll] = useState(false);
  if (!names.length) return null;
  const shown = all ? names : names.slice(0, SHOW);
  return (
    <span className="inline-flex flex-wrap items-center gap-1" aria-label="Names in this passage">
      {shown.map((n) => (
        <Popover key={n.canonical}>
          <PopoverTrigger asChild>
            <button
              type="button"
              className={`rounded-full border px-2 py-0.5 text-[11px] leading-tight hover:bg-muted ${KIND_CLASS[n.kind ?? ''] ?? 'border-border text-muted-foreground'}`}
              title={`${n.canonical}${n.kind ? ` (${n.kind})` : ''}`}
            >
              {n.canonical}
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-72 text-xs leading-relaxed">
            <p className="font-serif text-sm font-semibold text-foreground">{n.canonical}</p>
            {n.kind && <p className="text-muted-foreground">{KIND_ONE[n.kind] ?? n.kind}</p>}
            {n.surface && n.surface !== n.canonical && <p className="mt-1 text-muted-foreground">Here written &ldquo;{n.surface}&rdquo;.</p>}
            {n.notes && <p className="mt-1 text-foreground/90">{n.notes}</p>}
            <Link to={nameHref(n.canonical)} className="mt-2 inline-block text-burgundy hover:underline">
              Every passage that names {n.canonical}
            </Link>
            <p className="mt-2 text-muted-foreground">Recognised by machine; not reviewed.</p>
          </PopoverContent>
        </Popover>
      ))}
      {names.length > SHOW && !all && (
        <button type="button" onClick={() => setAll(true)} className="text-[11px] text-muted-foreground underline hover:text-foreground">
          +{names.length - SHOW} more
        </button>
      )}
    </span>
  );
}
