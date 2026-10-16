/**
 * ORNAMENT_2026_10_16 - a printed ornament is not the scanner's debris. The vision OCR writes an ornamental rule of
 * the page as a line of its own reading "<decorative line>"; the reader hides it and draws a short rule
 * (READER_MARKS_2026_10_07). The provisional test (PROVISIONAL_EN_2026_10_14) read the marker's words as Latin-letter
 * debris and called such a clean verse "provisional English" (found by Lovable, 16 Oct). The marker inside a line
 * of text, and any other Latin word, is debris as before. The automaton's own test sets the ornament aside too.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { madeFromMisread } from '@/lib/corpusDisplay';
import { DEFAULT_PREFS } from '@/lib/readerPrefs';
import PassageBlock from '@/components/reader/PassageBlock';

const CLEAN = 'धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।';
const ORN = '<decorative line>';

describe('madeFromMisread and the ornament', () => {
  it('sets aside a line that is only the ornament', () => {
    expect(madeFromMisread(`${ORN}\n${CLEAN}`)).toBe(false);
    expect(madeFromMisread(`${CLEAN}\n  ${ORN.toUpperCase()} \n${CLEAN}`)).toBe(false);
    expect(madeFromMisread(ORN)).toBe(false);
  });

  it('still marks the marker inside a line, and other Latin words', () => {
    expect(madeFromMisread(`${ORN} ${CLEAN}`)).toBe(true);
    expect(madeFromMisread(`${ORN}\n${CLEAN} af bates`)).toBe(true);
  });
});

describe('the passage block', () => {
  const wrap = (el: JSX.Element) => render(<ol>{el}</ol>);
  const p = (extra: Record<string, unknown>) => ({
    page_no: 1, idx: 4, verse_ref: null, sanskrit: `${ORN}\n${CLEAN}`, iast: null, translation: 'On the field of dharma. //',
    quality_score: 0.9, text_type: 'mula', ...extra,
  });

  it('draws the rule and does not call a clean verse provisional', () => {
    const { container } = wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({})} />);
    expect(screen.queryByText('provisional English')).toBeNull();
    expect(screen.queryByText(ORN)).toBeNull();
    expect(container.querySelector('div[aria-hidden="true"]')).toBeTruthy();
    expect(screen.getByText('On the field of dharma.')).toBeTruthy();
  });

  it('still marks a verse beside an ornament that carries debris', () => {
    wrap(<PassageBlock prefs={DEFAULT_PREFS} p={p({ sanskrit: `${ORN}\n${CLEAN} af bates` })} />);
    expect(screen.getByText('provisional English')).toBeTruthy();
  });
});
