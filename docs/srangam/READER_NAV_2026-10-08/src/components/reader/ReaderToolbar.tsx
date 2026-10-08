/**
 * The reader's bar - READER_NAV_2026_10_08. Shared by /texts/:docCode and /corpus/:docCode.
 *
 * On tablets and wider it stays under the site header while the reader scrolls (on a phone it would
 * cover a third of the screen, so there it scrolls away and the foot of the page has the pager):
 * previous and next page, any page by number, the contents, and what to show (IAST, English, Hindi,
 * side by side, scanner noise).
 * The arrow keys turn the page when no field has the focus.
 */
import { useEffect, type ReactNode } from 'react';
import { ChevronLeft, ChevronRight, ListTree } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ReaderPrefs } from '@/lib/readerPrefs';

const nf = new Intl.NumberFormat('en-IN');

export function pageStatus(page: number, lastPage: number, perPage: number, total: number): string {
  const from = (page - 1) * perPage + 1;
  const to = Math.min(page * perPage, total);
  return `Page ${page} of ${lastPage} · passages ${nf.format(from)}–${nf.format(to)} of ${nf.format(total)}`;
}

function typing(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null;
  if (!el || !el.tagName) return false;
  const tag = el.tagName.toLowerCase();
  return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable === true;
}

/** ← and → turn the page, unless a field has the focus or a modifier is held. */
export function usePageKeys(page: number, lastPage: number, go: (p: number) => void, enabled = true) {
  useEffect(() => {
    if (!enabled) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || typing(e.target)) return;
      if (e.key === 'ArrowLeft' && page > 1) { e.preventDefault(); go(page - 1); }
      if (e.key === 'ArrowRight' && page < lastPage) { e.preventDefault(); go(page + 1); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [page, lastPage, go, enabled]);
}

function Toggle({ label, aria, checked, onChange, title }: {
  label: string; aria: string; checked: boolean; onChange: (v: boolean) => void; title?: string;
}) {
  return (
    <label className="inline-flex cursor-pointer select-none items-center gap-1.5" title={title}>
      <input type="checkbox" aria-label={aria} checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

export default function ReaderToolbar({
  page, lastPage, perPage, total, go, prefs, setPrefs, hindi = false, noise = false, onContents, children,
}: {
  page: number;
  lastPage: number;
  perPage: number;
  total: number;
  go: (p: number) => void;
  prefs: ReaderPrefs;
  setPrefs: (patch: Partial<ReaderPrefs>) => void;
  /** Offer the Hindi toggle (the text has Hindi). */
  hindi?: boolean;
  /** Offer the scanner-noise toggle (the text has passages typed as noise). */
  noise?: boolean;
  onContents?: () => void;
  /** A find box, shown at the end of the bar. */
  children?: ReactNode;
}) {
  usePageKeys(page, lastPage, go);
  const many = lastPage > 1;

  return (
    <div
      className="-mx-4 mb-4 border-b border-border bg-background/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-background/80 sm:-mx-6 sm:px-6 md:sticky md:top-16 md:z-30 lg:-mx-8 lg:px-8"
      role="toolbar"
      aria-label="Reading controls"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        {many && (
          <nav className="flex items-center gap-1.5" aria-label="Pages of this text">
            <Button variant="outline" size="sm" onClick={() => go(page - 1)} disabled={page <= 1} title="Previous page (the left arrow key)">
              <ChevronLeft className="h-4 w-4" aria-hidden="true" /><span className="sr-only sm:not-sr-only sm:ml-1">Previous</span>
            </Button>
            <label className="sr-only" htmlFor="reader-page">Go to page</label>
            <select
              id="reader-page"
              value={page}
              onChange={(e) => go(Number(e.target.value))}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              title="Go to a page"
            >
              {Array.from({ length: lastPage }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>Page {n}</option>
              ))}
            </select>
            <Button variant="outline" size="sm" onClick={() => go(page + 1)} disabled={page >= lastPage} title="Next page (the right arrow key)">
              <span className="sr-only sm:not-sr-only sm:mr-1">Next</span><ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </nav>
        )}
        {onContents && (
          <Button variant="ghost" size="sm" onClick={onContents} title="Contents: every page, the chapter ends, and a scan page by number">
            <ListTree className="mr-1 h-4 w-4" aria-hidden="true" /> Contents
          </Button>
        )}
        <span className="text-xs text-muted-foreground" aria-live="polite">{pageStatus(page, lastPage, perPage, total)}</span>
        {children && <div className="w-full sm:ml-auto sm:w-auto">{children}</div>}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <Toggle label="IAST" aria="Show the IAST" checked={prefs.iast} onChange={(v) => setPrefs({ iast: v })} title="The Sanskrit in Roman letters" />
        <Toggle label="English" aria="Show the English" checked={prefs.english} onChange={(v) => setPrefs({ english: v })} />
        {hindi && <Toggle label="Hindi" aria="Show the Hindi" checked={prefs.hindi} onChange={(v) => setPrefs({ hindi: v })} />}
        <span className="hidden lg:inline-flex">
          <Toggle
            label="Side by side"
            aria="Show the translation beside the Sanskrit"
            checked={prefs.layout === 'side'}
            onChange={(v) => setPrefs({ layout: v ? 'side' : 'stacked' })}
            title="On wide screens, the Sanskrit on the left and the translation on the right"
          />
        </span>
        {noise && (
          <Toggle
            label="Scanner noise"
            aria="Show scanner noise"
            checked={prefs.noise}
            onChange={(v) => setPrefs({ noise: v })}
            title="Passages the automaton marked as marks on the page, not text"
          />
        )}
      </div>
    </div>
  );
}

/** The plain pager at the foot of the page. */
export function FootPager({ page, lastPage, perPage, total, go }: {
  page: number; lastPage: number; perPage: number; total: number; go: (p: number) => void;
}) {
  if (lastPage <= 1) return null;
  return (
    <nav className="my-8 flex items-center justify-between gap-4" aria-label="Pages of this text, at the end">
      <Button variant="outline" size="sm" onClick={() => go(page - 1)} disabled={page <= 1}>
        <ChevronLeft className="mr-1 h-4 w-4" aria-hidden="true" /> Previous
      </Button>
      <span className="text-center text-sm text-muted-foreground">{pageStatus(page, lastPage, perPage, total)}</span>
      <Button variant="outline" size="sm" onClick={() => go(page + 1)} disabled={page >= lastPage}>
        Next <ChevronRight className="ml-1 h-4 w-4" aria-hidden="true" />
      </Button>
    </nav>
  );
}
