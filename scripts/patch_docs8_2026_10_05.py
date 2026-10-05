#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs8_2026_10_05.py  DOCS8_2026_10_05

Corrects the vision-cost statements made on 2026-10-04 (PLATFORM section 10 and
ENTERPRISE_PATH_2026-10-04.md) and records what COST_RATIO_2026_10_05 changed.
Appends PLATFORM section 11; replaces four rows of ENTERPRISE_PATH (anchored).
Marker-idempotent per file, backup first, all-or-nothing.

  python scripts/patch_docs8_2026_10_05.py --check
  python scripts/patch_docs8_2026_10_05.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS8_2026_10_05"

PLATFORM_APPEND = """

## 11. Vision cost, corrected again (DOCS8_2026_10_05, COST_RATIO_2026_10_05)

Section 10 said the "about $0.0054" in section 9 "was not a ledger figure". **That was wrong.** It is the figure `spend_audit.py` printed for the last 24 hours: $3.02 for 557 delivered pages = $0.00542 a page.

**Where the error came from.** The mean ($0.00313) and median ($0.00282) of section 10 counted only usage rows that delivered a page. `ocr_vision` also meters every ladder attempt (budget and temperature retries) as `units=0`, and those calls are billed. From 2026-10-03 12:00 to the 04:00 backup on 2026-10-05:
- 557 page-delivering calls cost $1.94;
- 93 zero-page calls cost $1.08, or 36% of the vision spend, almost all of it on the Rgveda.

**The rate also differs a lot by book.** Repriced, all provider-metered history:

| Text | Calls | Pages | $/page |
|---|---|---|---|
| Rgveda Vol-ii | 539 | 447 | 0.00646 |
| Shatpatha | 336 | 336 | 0.00348 |
| markandeya | 101 | 100 | 0.00132 |
| Mallapurana | 301 | 202 | 0.00115 |
| Dhanurveda, both codes (2026-10-05) | 51 | 51 | about 0.0012 |

**What changed (COST_RATIO_2026_10_05):**
- **Rate formula.** `measured_cost_per_page` is now total cost divided by pages delivered, with zero-page calls included.
- **Per-text rates.** A text with at least 20 delivered pages is priced from its own last 600 calls. Any other text is priced from the last 300 calls corpus-wide.
- **Where the rate is used.** `corpus_status` and `ocr_consensus` use each text's own rate. `ocr_vision`'s pre-flight estimate reads the ledger instead of a fixed $0.00028.
- **Noise.** The "Update COST_PER_PAGE" note no longer prints on every one-page run.

**Rgveda's remaining 618 pages:** about $4.0 at its own rate (`--max-usd` about $4.6). The 2026-10-05 `corpus_status` had proposed $1.82.
"""

EP_EDITS = [
    ("s1 vision row",
     "| Vision cost per page (repriced) | median $0.00282, mean $0.00313, p90 $0.00350; $0.00407 per delivered page over all metered history (1,278 calls for 1,086 pages) | `usage_log`, 17:58 backup |\n",
     "| Vision cost per page (repriced) | Cost / pages delivered, ladder retries included (DOCS8_2026_10_05). Last 24 h on 10-04: $0.00542. All history: $0.00407. Per text: Rgveda $0.00646, Shatpatha $0.00348, markandeya $0.00132, Mallapurana $0.00115. | `usage_log`, 2026-10-05 04:00 backup; PLATFORM s11 |\n", 1),
    ("s3 vision row",
     "| Vision $/page | 0.00028, 0.00087, 0.0015, 0.0054 | Mean $0.0031 a call; $0.0041 a delivered page including retries. PLATFORM \u00a79's \"about $0.0054\" was wrong (PLATFORM \u00a710). |\n",
     "| Vision $/page | 0.00028, 0.00087, 0.0015, 0.0054 | It depends on the book: $0.0012-0.0065 a delivered page, retries included. The 24 h figure of $0.0054 was right; PLATFORM s10's retraction of it was wrong (PLATFORM s11). Estimates now use each text's own rate. |\n", 1),
    ("1.2 Rgveda estimate",
     "| 618 pages, then about 11.5k passages | vision about $2.0; translation about $4 EN + $4 HI |\n",
     "| 618 pages, then about 11.5k passages | vision about $4.0 at Rgveda's own $0.00646 a page (DOCS8); translation about $4 EN + $4 HI |\n", 1),
    ("1.3 Dhanurveda done",
     "| `dhanur_veda_shiva_dhanur_veda` 19 pages; `dhanur_veda_vasishtha_dhanur_veda` 32 pages | about $0.20 |\n",
     "| `dhanur_veda_shiva_dhanur_veda` 19 pages; `dhanur_veda_vasishtha_dhanur_veda` 32 pages | Vision done 2026-10-05, about $0.06 for 51 pages, all clean. Next: re-ingest and translate. |\n", 1),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    plat, ep = Path("docs/PLATFORM_2026-10-04.md"), Path("docs/ENTERPRISE_PATH_2026-10-04.md")
    for p in (plat, ep):
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    out = []
    s, nl = load(plat)
    if MARK in s:
        print("skip %s (already carries %s)" % (plat, MARK))
    else:
        out.append((plat, s + PLATFORM_APPEND, nl))
    s, nl = load(ep)
    if MARK in s:
        print("skip %s (already carries %s)" % (ep, MARK))
    else:
        bad = []
        for label, old, new, n in EP_EDITS:
            c = s.count(old)
            if c != n:
                bad.append("%s: matched %d times, expected %d" % (label, c, n))
            else:
                s = s.replace(old, new)
        if bad:
            print("REFUSING TO WRITE:"); [print("  " + b) for b in bad]; return 1
        out.append((ep, s, nl))
    if a.check:
        print("CHECK OK: %d file(s) to change. Nothing written." % len(out)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    for p, text, nl in out:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs8_" + stamp))
        t = p.with_name(p.name + ".tmp_docs8"); t.write_bytes(text.replace("\n", nl).encode("utf-8")); os.replace(t, p)
        print("changed %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
