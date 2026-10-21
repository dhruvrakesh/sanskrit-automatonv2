/**
 * ETEXT_NOISE_2026_10_21 - an e-text (typed from an edition, not scanned) has no scanner: what the automaton folds as
 * noise in one is the e-text's own header or notes (GRETIL's English header on the Surya Siddhanta's page 1), and the
 * reader says so, folded as before; its "About" says what it is. A scan's noise, and noise whose reading is not
 * recorded, are "Scanner noise, not text." as before.
 */
import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { DEFAULT_PREFS } from '@/lib/readerPrefs';
import PassageBlock, { TYPE_NOTES } from '@/components/reader/PassageBlock';

const HEADER = 'Contribution: Michio Yano';
const wrap = (el: JSX.Element) => render(<ol>{el}</ol>);
const p = (extra: Record<string, unknown>) => ({
  page_no: 1, idx: 3, verse_ref: null, sanskrit: HEADER, iast: null, translation: null, quality_score: 0.95,
  text_type: 'noise', ...extra,
});

describe("an e-text's noise", () => {
  it("is called the e-text's own header or notes, folded until asked for", () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ reading: 'etext:etext' })} />);
    expect(screen.queryByText(HEADER)).toBeNull();
    const label = screen.getByText("Not the text: the e-text's own header or notes.");
    expect(label.getAttribute('title')).toBe(TYPE_NOTES.etext_noise);
    expect(TYPE_NOTES.etext_noise).toMatch(/GRETIL's English header/);
    expect(screen.queryByText('Scanner noise, not text.')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Show it' }));
    expect(screen.getByText(HEADER)).toBeTruthy();
  });

  it("a scan's noise, and noise whose reading is not recorded, are scanner noise as before", () => {
    wrap(<>
      <PassageBlock prefs={DEFAULT_PREFS} p={p({ idx: 4, reading: 'tesseract' })} />
      <PassageBlock prefs={DEFAULT_PREFS} p={p({ idx: 5 })} />
    </>);
    expect(screen.getAllByText('Scanner noise, not text.')).toHaveLength(2);
    expect(screen.queryByText("Not the text: the e-text's own header or notes.")).toBeNull();
    expect(TYPE_NOTES.noise).toBe('Scanner noise: marks on the page that are not text.');
  });
});
