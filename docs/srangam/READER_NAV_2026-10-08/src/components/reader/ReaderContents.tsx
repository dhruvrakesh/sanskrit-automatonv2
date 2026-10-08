/**
 * Contents of one text - READER_NAV_2026_10_08. A panel from the side, opened from the reader's bar.
 *
 * Every reader page with the scan pages it covers, the chapter ends (colophons) where the data has
 * them, and a box to go straight to a scan page of the printed book. Loaded only when opened.
 * Chapters are not listed: the stored chapter field mostly holds the division word without its
 * number, so a list built on it would mislead (docs/cloud/C5b).
 */
import { FormEvent, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { scanRange, type PageStart } from '@/lib/corpusDisplay';

export interface Landmark {
  reader_page: number;
  page_no: number;
  idx: number;
  label: string;
}

export interface ContentsState {
  loading: boolean;
  /** Non-null when the contents could not be loaded. */
  error: string | null;
  pages: PageStart[];
  landmarks: Landmark[];
}

export default function ReaderContents({
  open, onOpenChange, title, state, current, lastPage, goPage, goPassage, goScan,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  state: ContentsState;
  current: number;
  lastPage: number;
  goPage: (p: number) => void;
  goPassage: (readerPage: number, pageNo: number, idx: number) => void;
  /** Resolves true when it found the page; the panel then closes. */
  goScan: (scan: number) => Promise<boolean> | boolean;
}) {
  const [scan, setScan] = useState('');
  const [miss, setMiss] = useState<string | null>(null);
  const n = Number.parseInt(scan, 10);
  const scanOk = Number.isFinite(n) && n > 0;
  const byPage = new Map<number, Landmark[]>();
  for (const l of state.landmarks) byPage.set(l.reader_page, [...(byPage.get(l.reader_page) ?? []), l]);
  const pages: PageStart[] = state.pages.length
    ? state.pages
    : Array.from({ length: lastPage }, (_, i) => ({ reader_page: i + 1, page_no: 0, idx: 0, last_page_no: null }));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!scanOk) return;
    setMiss(null);
    Promise.resolve(goScan(n)).then((found) => {
      if (found) onOpenChange(false);
      else setMiss(`Scan page ${n} could not be found in this text.`);
    });
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Contents</SheetTitle>
          <SheetDescription>{title}</SheetDescription>
        </SheetHeader>

        <form onSubmit={submit} className="mt-4 flex items-end gap-2">
          <div className="flex-1">
            <label htmlFor="reader-scan" className="text-xs text-muted-foreground">Go to a page of the printed book (scan page)</label>
            <Input id="reader-scan" inputMode="numeric" value={scan} onChange={(e) => { setScan(e.target.value.replace(/\D/g, '')); setMiss(null); }} placeholder="e.g. 18" />
          </div>
          <Button type="submit" size="sm" disabled={!scanOk}>Go</Button>
        </form>
        {miss && <p role="alert" className="mt-2 text-xs text-amber-800 dark:text-amber-200">{miss}</p>}

        <div className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1" aria-busy={state.loading}>
          {state.loading && (
            <p className="text-sm text-muted-foreground"><Loader2 className="mr-1 inline h-4 w-4 animate-spin" aria-hidden="true" />Reading the contents...</p>
          )}
          {state.error && <p role="alert" className="mb-3 text-xs text-amber-800 dark:text-amber-200">{state.error}</p>}
          <ol className="space-y-1">
            {pages.map((p) => (
              <li key={p.reader_page}>
                <button
                  type="button"
                  onClick={() => { goPage(p.reader_page); onOpenChange(false); }}
                  aria-current={p.reader_page === current ? 'page' : undefined}
                  className={`w-full rounded px-2 py-1 text-left text-sm hover:bg-muted ${p.reader_page === current ? 'bg-muted font-semibold' : ''}`}
                >
                  Page {p.reader_page}
                  {p.page_no > 0 && <span className="ml-2 text-xs text-muted-foreground">{scanRange(p)}</span>}
                </button>
                {(byPage.get(p.reader_page) ?? []).map((l) => (
                  <button
                    key={`${l.page_no}-${l.idx}`}
                    type="button"
                    onClick={() => { goPassage(l.reader_page, l.page_no, l.idx); onOpenChange(false); }}
                    className="ml-4 block w-[calc(100%-1rem)] rounded px-2 py-0.5 text-left text-xs italic text-muted-foreground hover:bg-muted hover:text-foreground"
                    title="A colophon: the closing line of a chapter or section"
                  >
                    <span className="font-mono not-italic">{l.page_no}.{l.idx}</span> {l.label}
                  </button>
                ))}
              </li>
            ))}
          </ol>
        </div>
      </SheetContent>
    </Sheet>
  );
}
