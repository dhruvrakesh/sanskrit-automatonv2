/**
 * CLASSIFY_HINDI_2026_10_16 - a passage typed frontmatter (an edition's front matter, or its editor's translation or
 * notes in a modern language, as the Karanagama's Hindi under each verse) is folded until asked for, says what it is,
 * and is never "Not translated yet". A verse without English still says so; scanner noise is folded as before.
 */
import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { DEFAULT_PREFS } from '@/lib/readerPrefs';
import PassageBlock, { TYPE_NOTES } from '@/components/reader/PassageBlock';

const HINDI = 'मण्डप में नौ अथवा पांच अथवा एक कुण्ड का निर्माण कराएँ ॥';
const VERSE = 'शरीरपातपर्यन्तं न जहीहि व्रतान्यपि ।';
const wrap = (el: JSX.Element) => render(<ol>{el}</ol>);
const p = (extra: Record<string, unknown>) => ({
  page_no: 30, idx: 13, verse_ref: null, sanskrit: HINDI, iast: null, translation: null, quality_score: 0.9,
  text_type: 'frontmatter', ...extra,
});

describe("the edition's own matter", () => {
  it('is folded until asked for, and says what it is', () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({})} />);
    expect(screen.queryByText(HINDI)).toBeNull();
    const label = screen.getByText("The edition's own matter, not the Sanskrit.");
    expect(label.getAttribute('title')).toBe(TYPE_NOTES.frontmatter);
    expect(TYPE_NOTES.frontmatter).toMatch(/editor's translation/);
    expect(screen.queryByText('Not translated yet.')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Show it' }));
    expect(screen.getByText(HINDI)).toBeTruthy();
    expect(screen.queryByText('Not translated yet.')).toBeNull();
    expect(screen.getByText('frontmatter').getAttribute('title')).toBe(TYPE_NOTES.frontmatter);
  });

  it('a verse without English still says so; noise is folded as before', () => {
    wrap(<>
      <PassageBlock prefs={DEFAULT_PREFS} p={p({ idx: 14, sanskrit: VERSE, text_type: 'mula' })} />
      <PassageBlock prefs={DEFAULT_PREFS} p={p({ idx: 15, sanskrit: '~~ ||| ~~', text_type: 'noise' })} />
    </>);
    expect(screen.getByText(VERSE)).toBeTruthy();
    expect(screen.getByText('Not translated yet.')).toBeTruthy();
    expect(screen.getByText('Scanner noise, not text.')).toBeTruthy();
    expect(screen.queryByText("The edition's own matter, not the Sanskrit.")).toBeNull();
  });
});
