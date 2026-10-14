/**
 * PROVISIONAL_EN_2026_10_14 - English made from a misread reading is marked "provisional English".
 * The test is the automaton's own (scripts/redeem.py, repair_text.JUNK): eight or more Devanagari signs and a
 * Latin word among them. A clean verse, a verse without English, the book's own English (no Devanagari) and a
 * single stray letter are not marked. Nothing stored is changed: the Sanskrit and the English are shown as read.
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { madeFromMisread, PROVISIONAL_NOTE } from '@/lib/corpusDisplay';
import { DEFAULT_PREFS } from '@/lib/readerPrefs';
import PassageBlock from '@/components/reader/PassageBlock';

const CLEAN = 'धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।';
const DIRTY = 'धर्मक्षेत्रे af bates कुरुक्षेत्रे ।';

describe('madeFromMisread', () => {
  it('is the automaton test: eight Devanagari signs and a Latin word', () => {
    expect(madeFromMisread(DIRTY)).toBe(true);
    expect(madeFromMisread('धर्मक्षेत्रे कुरुक्षेत्रे I\' ।')).toBe(true);   // a letter and a stray quote
    expect(madeFromMisread('ay Trae: ।\nअथ प्रथमोऽध्यायः ।')).toBe(true);    // a whole misread line
  });

  it('leaves the rest alone', () => {
    expect(madeFromMisread(CLEAN)).toBe(false);
    expect(madeFromMisread('धर्मक्षेत्रे कुरुक्षेत्रे a ।')).toBe(false);     // one stray letter
    expect(madeFromMisread('अथ ab')).toBe(false);                              // too little Devanagari
    expect(madeFromMisread('ADVERTISEMENT. The present edition')).toBe(false); // the book's own English
    expect(madeFromMisread(null)).toBe(false);
    expect(madeFromMisread('')).toBe(false);
  });
});

describe('the passage block', () => {
  const wrap = (el: JSX.Element) => render(<ol>{el}</ol>);
  const p = (extra: Record<string, unknown>) => ({
    page_no: 4, idx: 2, verse_ref: null, sanskrit: DIRTY, iast: null, translation: 'On the field of dharma. //',
    quality_score: 0.8, text_type: 'mula', ...extra,
  });

  it('marks English made from a misread reading, and says why', () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({})} />);
    const chip = screen.getByText('provisional English');
    expect(chip.getAttribute('title')).toBe(PROVISIONAL_NOTE);
    expect(screen.getByText('On the field of dharma.')).toBeTruthy();   // shown as published
    expect(screen.getByText(DIRTY)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'About this passage' }));
    expect(screen.getByText(`provisional: ${PROVISIONAL_NOTE}`)).toBeTruthy();
  });

  it('does not mark a clean verse, a verse without English, or English the reader has hidden', () => {
    const { unmount } = wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ sanskrit: CLEAN })} />);
    expect(screen.queryByText('provisional English')).toBeNull();
    unmount();
    const second = wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ translation: null })} />);
    expect(screen.queryByText('provisional English')).toBeNull();
    expect(screen.getByText('Not translated yet.')).toBeTruthy();
    second.unmount();
    wrap(<PassageBlock prefs={{ ...DEFAULT_PREFS, english: false }} p={p({})} />);
    expect(screen.queryByText('provisional English')).toBeNull();
  });
});
