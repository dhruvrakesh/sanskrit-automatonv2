/**
 * How a reader likes the texts laid out - READER_NAV_2026_10_08.
 *
 * Shared by /texts/:docCode and /corpus/:docCode, remembered in this browser only (localStorage,
 * every access guarded: a private window or blocked storage simply gets the defaults).
 */
import { useCallback, useState } from 'react';

export interface ReaderPrefs {
  /** 'side': Sanskrit and IAST beside the translations on wide screens. 'stacked': one column. */
  layout: 'side' | 'stacked';
  iast: boolean;
  english: boolean;
  hindi: boolean;
  /** Show passages the automaton typed as scanner noise (folded away by default). */
  noise: boolean;
  /** CORPUS_LIBRARY_C6_2026_10_08: the names recognised in each passage, as chips (corpus reader). */
  names: boolean;
}

export const DEFAULT_PREFS: ReaderPrefs = { layout: 'side', iast: true, english: true, hindi: true, noise: false, names: true };

const KEY = 'srangam.reader.v1';

export function parsePrefs(raw: string | null): ReaderPrefs {
  if (!raw) return { ...DEFAULT_PREFS };
  try {
    const o = JSON.parse(raw) as Partial<ReaderPrefs>;
    return {
      layout: o.layout === 'stacked' ? 'stacked' : 'side',
      iast: typeof o.iast === 'boolean' ? o.iast : DEFAULT_PREFS.iast,
      english: typeof o.english === 'boolean' ? o.english : DEFAULT_PREFS.english,
      hindi: typeof o.hindi === 'boolean' ? o.hindi : DEFAULT_PREFS.hindi,
      noise: typeof o.noise === 'boolean' ? o.noise : DEFAULT_PREFS.noise,
      names: typeof o.names === 'boolean' ? o.names : DEFAULT_PREFS.names,
    };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function loadPrefs(): ReaderPrefs {
  try {
    return parsePrefs(window.localStorage.getItem(KEY));
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function savePrefs(p: ReaderPrefs): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    /* storage blocked: the choice lasts for this visit only */
  }
}

export function useReaderPrefs(): [ReaderPrefs, (patch: Partial<ReaderPrefs>) => void] {
  const [prefs, setPrefs] = useState<ReaderPrefs>(loadPrefs);
  const update = useCallback((patch: Partial<ReaderPrefs>) => {
    setPrefs((cur) => {
      const next = { ...cur, ...patch };
      savePrefs(next);
      return next;
    });
  }, []);
  return [prefs, update];
}
