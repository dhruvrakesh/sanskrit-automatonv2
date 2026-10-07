#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_reader_marks_2026_10_07.py  (2026-10-07)  READER_MARKS_2026_10_07

For the SRANGAM repo (run from D:\\srangam-42267, on main). W5: the OCR writes an ornamental rule
of the printed page as a line reading "<decorative line>". On /texts/markandeya_purana two
passages (p1.4 and p1.6) showed that line to readers, in the Devanagari and in the IAST. It is not
text, so the reader now draws a short rule in its place; every other character is shown as
published (the stored text is not changed).

  src/lib/corpusDisplay.ts        + splitDecoration(): drops lines that are exactly
                                    "<decorative line>" and says whether there was one
  src/pages/texts/TextReader.tsx  uses it for the Sanskrit and the IAST; a rule (aria-hidden) above
  src/__tests__/reader-marks.test.ts   new

Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_marks_<date>.
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_reader_marks_2026_10_07.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_reader_marks_2026_10_07.py"
Then: npx vitest run src/__tests__/reader-marks.test.ts src/__tests__/texts-reader.test.tsx
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "READER_MARKS_2026_10_07"

HELPER = (
    "\n/**\n"
    " * " + MARK + ": the OCR writes an ornamental rule of the printed page as a line reading\n"
    " * \"<decorative line>\". It is not text: the reader draws a short rule instead. Only lines that are\n"
    " * exactly that marker are removed; everything else is returned as published.\n"
    " */\n"
    "const DECORATIVE_LINE = /^\\s*<decorative line>\\s*$/i;\n\n"
    "export function splitDecoration(s: string | null | undefined): { text: string; rule: boolean } {\n"
    "  const lines = (s ?? '').split('\\n');\n"
    "  const kept = lines.filter((l) => !DECORATIVE_LINE.test(l));\n"
    "  return { text: kept.join('\\n').trim(), rule: kept.length !== lines.length };\n"
    "}\n"
)

EDITS = {
    "src/lib/corpusDisplay.ts": [(
        "after displayTranslation",
        "    .replace(/\\s+\\/\\/(?:\\s+|$)/g, '\\n')   // only a spaced mark; 'http://' is not one\n"
        "    .trim();\n"
        "}\n",
        "    .replace(/\\s+\\/\\/(?:\\s+|$)/g, '\\n')   // only a spaced mark; 'http://' is not one\n"
        "    .trim();\n"
        "}\n" + HELPER,
    )],
    "src/pages/texts/TextReader.tsx": [
        ("import",
         "  PASSAGES_PER_PAGE, displayTranslation, isLowQuality, pageFromQuery, passageLabel,\n"
         "} from '@/lib/corpusDisplay';\n",
         "  PASSAGES_PER_PAGE, displayTranslation, isLowQuality, pageFromQuery, passageLabel, splitDecoration,\n"
         "} from '@/lib/corpusDisplay';\n"),
        ("sanskrit",
         "                  <p lang=\"sa\" className=\"font-devanagari text-lg leading-relaxed whitespace-pre-line text-foreground\">\n"
         "                    {p.sanskrit}\n"
         "                  </p>\n"
         "                  {p.iast && (\n"
         "                    <p lang=\"sa-Latn\" className=\"mt-2 italic text-sm leading-relaxed whitespace-pre-line text-muted-foreground\">\n"
         "                      {p.iast}\n"
         "                    </p>\n"
         "                  )}\n",
         "                  {/* " + MARK + ": an ornamental rule of the page, drawn, not printed as text */}\n"
         "                  {(splitDecoration(p.sanskrit).rule || splitDecoration(p.iast).rule) && (\n"
         "                    <div aria-hidden=\"true\" className=\"mb-3 h-px w-24 bg-border\" />\n"
         "                  )}\n"
         "                  <p lang=\"sa\" className=\"font-devanagari text-lg leading-relaxed whitespace-pre-line text-foreground\">\n"
         "                    {splitDecoration(p.sanskrit).text}\n"
         "                  </p>\n"
         "                  {splitDecoration(p.iast).text && (\n"
         "                    <p lang=\"sa-Latn\" className=\"mt-2 italic text-sm leading-relaxed whitespace-pre-line text-muted-foreground\">\n"
         "                      {splitDecoration(p.iast).text}\n"
         "                    </p>\n"
         "                  )}\n"),
    ],
}

TEST_PATH = "src/__tests__/reader-marks.test.ts"
TEST = """import { describe, it, expect } from 'vitest';
import { splitDecoration } from '@/lib/corpusDisplay';

// READER_MARKS_2026_10_07 - "<decorative line>" is an ornament of the printed page, not text.
describe('splitDecoration', () => {
  it('drops the marker line and reports a rule', () => {
    const sa = '<decorative line>\\n\\u092f\\u0926\\u094d\\u092f\\u094b\\u0917\\u093f\\u092d\\u093f\\u0903';
    expect(splitDecoration(sa)).toEqual({ text: '\\u092f\\u0926\\u094d\\u092f\\u094b\\u0917\\u093f\\u092d\\u093f\\u0903', rule: true });
    expect(splitDecoration('<decorative line>\\nyadyogibhir')).toEqual({ text: 'yadyogibhir', rule: true });
    expect(splitDecoration('  <Decorative Line>  \\nx\\n<decorative line>')).toEqual({ text: 'x', rule: true });
  });

  it('leaves everything else exactly as published', () => {
    expect(splitDecoration('a\\nb [ILLEGIBLE] c')).toEqual({ text: 'a\\nb [ILLEGIBLE] c', rule: false });
    expect(splitDecoration('see the <decorative line> here')).toEqual({ text: 'see the <decorative line> here', rule: false });
    expect(splitDecoration(null)).toEqual({ text: '', rule: false });
    expect(splitDecoration(undefined)).toEqual({ text: '', rule: false });
  });

  it('a passage that is only the marker has no text left', () => {
    expect(splitDecoration('<decorative line>')).toEqual({ text: '', rule: true });
  });
});
"""


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("src/pages/texts/TextReader.tsx").exists():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel, edits in EDITS.items():
        p = Path(rel); src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    tp = Path(TEST_PATH)
    if tp.exists():
        if tp.read_text(encoding="utf-8").replace("\r\n", "\n") != TEST:
            problems.append("%s exists with other content" % TEST_PATH)
        else:
            print("skip %s (already present)" % TEST_PATH)
    else:
        todo.append((tp, TEST.encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    for p, data in todo:
        if p.exists():
            shutil.copy2(p, p.with_name(p.name + ".bak_marks_" + stamp))
        t = p.with_name(p.name + ".tmp_marks"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next: npx vitest run src/__tests__/reader-marks.test.ts src/__tests__/texts-reader.test.tsx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
