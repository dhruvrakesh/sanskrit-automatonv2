#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_read_in_2026_10_13.py  (2026-10-13)  READ_IN_2026_10_13

After MIRROR_CAP_2026_10_12 (e51422b), the morning of 13 Oct: the Natyasastra's repair read 245 more pages (513 of
546 now, at $0.0070 a page), and every tool still said "repair the scan": the merge leaves out blank pages (538
merged), so "merged_complete" (every page) never comes, and 22 pages vision failed on twice (left to Tesseract)
were counted as pages to read. ocr_consensus.py printed the old wipe-and-re-ingest block, which deletes every
translation of the text.
  repair_text.py: the assessment counts the pages left to Tesseract (the ledger); a scan vision has read (80% of
    its pages, 95% merged) is ready: NEXT is the in-place re-ingest of the pages read (reingest_pages.py), and the
    pages vision may still read come after (ALSO, with a cap that fits them).
  text_path.py: the same rule (a text so read goes to "use the repair"); the pages left to Tesseract are not
    priced as pages to read; a scan whose every remaining page vision failed on twice is "find a source".
  ocr_consensus.py: "To bring it up to date" gives the in-place re-ingest first; the whole text again (wipe and
    re-ingest, which deletes its translations) comes second.

Needs PATH_2026_10_12 (repair_text.py) and MIRROR_CAP_2026_10_12 (text_path.py, ocr_consensus.py). Anchored,
all-or-nothing, marker-idempotent per file; keeps line endings and encodings; each .py is compiled before it
replaces the original; backups .bak_readin_<date>.
  python scripts\\patch_read_in_2026_10_13.py --check
  python scripts\\patch_read_in_2026_10_13.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "READ_IN_2026_10_13"
NEEDS = {"scripts/repair_text.py": "PATH_2026_10_12", "scripts/text_path.py": "MIRROR_CAP_2026_10_12",
         "scripts/ocr_consensus.py": "MIRROR_CAP_2026_10_12"}
FILES = list(NEEDS)

E = []   # (file, number, old, new): hunks with their context, applied in order
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/repair_text.py', 1,
     r'''    except Exception:
        return COST_PER_PAGE


''',
     r'''    except Exception:
        return COST_PER_PAGE


def vision_gave_up(work: Path, doc: str) -> int:
    """READ_IN_2026_10_13: the pages vision failed on in two runs or more, left to Tesseract (PATH_2026_10_12's
    ledger, data/ocr_consensus/<doc>_vision_failed.json); 0 when there is none."""
    try:
        import ocr_consensus as _oc
        return sum(1 for v in _oc.read_failed(Path(work), doc).values()
                   if int((v or {}).get("fails") or 0) >= _oc.VISION_GIVE_UP)
    except Exception:
        return 0


''')
edit('scripts/repair_text.py', 2,
     r'''        "aside": state, "state": state,
        "cost_per_page": measured_cost_per_page(a.db, a.doc),   # REINGEST_2026_10_12
    })
    res["held"] = res["guard"] and not (state and state.get("status") == "translate_as_is")
''',
     r'''        "aside": state, "state": state,
        "cost_per_page": measured_cost_per_page(a.db, a.doc),   # REINGEST_2026_10_12
        "vision_gave_up": vision_gave_up(work, a.doc),   # READ_IN_2026_10_13
    })
    res["held"] = res["guard"] and not (state and state.get("status") == "translate_as_is")
''')
edit('scripts/repair_text.py', 3,
     r'''        left = max(0, pages - r["vision_pages"]) if r["vision_pages"] else pages
        cpp = r.get("cost_per_page") or COST_PER_PAGE   # REINGEST_2026_10_12: measured on this text where it can be
        cap = max(1.0, math.ceil(left * cpp * 1.25 * 10) / 10.0)   # PATH_2026_10_12: a cap the estimate fits under
        return (why + "; the scan can be repaired: vision OCR on about %d page(s), about $%.2f ($%.4f a page)"
                % (left, left * cpp, cpp),
''',
     r'''        left = max(0, pages - r["vision_pages"]) if r["vision_pages"] else pages
        cpp = r.get("cost_per_page") or COST_PER_PAGE   # REINGEST_2026_10_12: measured on this text where it can be
        gave = int(r.get("vision_gave_up") or 0)   # READ_IN_2026_10_13
        left = max(0, left - gave)
        cap = max(1.0, math.ceil(left * cpp * 1.25 * 10) / 10.0)   # PATH_2026_10_12: a cap the estimate fits under
        if (r["vision_pages"] >= 0.8 * max(1, r["pdfs"]) and
                (r.get("merged_pages") or 0) >= 0.95 * max(1, r.get("raw_pages") or r["pdfs"])):
            # READ_IN_2026_10_13: the scan is read (the Natyasastra: 513 of 546 pages, 538 merged; the merge leaves
            # out blank pages, so it is never "complete"): the pages read go in now, in place
            more = ([q + " --repair --max-usd %.2f   (the %d page(s) vision has not read yet; after)" % (cap, left)]
                    if left else [])
            return (why + "; vision has read %d of its %d pages%s and %d are merged: they can go in now; the others keep "
                    "Tesseract's reading" % (r["vision_pages"], r["pdfs"],
                                             (" (%d left to Tesseract: vision failed on them twice)" % gave) if gave else "",
                                             r.get("merged_pages") or 0),
                    REINGEST % doc, more + also)
        return (why + "; the scan can be repaired: vision OCR on about %d page(s), about $%.2f ($%.4f a page)"
                % (left, left * cpp, cpp),
''')
edit('scripts/text_path.py', 4,
     r'''    mg = "python scripts\\merge_ocr_sources.py --doc %s" % doc
    o = {"path": "", "why": "", "next": [], "also": [], "cost": 0.0, "then": 0.0}
    merged_ok = bool(f.get("merged_complete")) and vpages >= 0.8 * max(1, raw)
    chg = f.get("changed", -1)
    if merged_ok and chg == 0:
''',
     r'''    mg = "python scripts\\merge_ocr_sources.py --doc %s" % doc
    o = {"path": "", "why": "", "next": [], "also": [], "cost": 0.0, "then": 0.0}
    # READ_IN_2026_10_13: a merge without its blank pages is a merge (the Natyasastra: 538 of 546 merged, 513 read by
    # vision; "merged_complete" asks for every page, so it was charted "repair the scan" for ever)
    merged_ok = (bool(f.get("merged_complete")) or (f.get("merged_pages") or 0) >= 0.95 * max(1, raw)) and \
        vpages >= 0.8 * max(1, raw)
    gave = int(f.get("vision_gave_up") or 0)   # pages vision failed on twice: left to Tesseract (the ledger)
    tryable = max(0, pdfs - vpages - gave)
    chg = f.get("changed", -1)
    if merged_ok and chg == 0:
''')
edit('scripts/text_path.py', 5,
     r'''            o["also"].append("its %d English were made from Tesseract's text; the changed passages are translated again"
                             % en)
        return o
    if tesseract:
        scan_here = pdfs and pdfs >= 0.9 * max(1, raw)
        damaged = level in ("moderate", "material")
        if scan_here and (damaged or en < 0.95 * n):
            todo = max(0, pdfs - vpages)
            est = todo * cpp
            cap = max(1.0, math.ceil(est * 1.25 * 10) / 10.0)
''',
     r'''            o["also"].append("its %d English were made from Tesseract's text; the changed passages are translated again"
                             % en)
        if tryable:   # READ_IN_2026_10_13: the pages vision may still read, after
            cap2 = max(1.0, math.ceil(tryable * cpp * 1.25 * 10) / 10.0)
            o["also"].append("%d page(s) vision has not read yet%s: %s --repair --max-usd %.2f   (after; their pages go in "
                             "the same way)" % (tryable, (" (%d more left to Tesseract)" % gave) if gave else "", q0, cap2))
        elif gave:
            o["also"].append("%d page(s) keep Tesseract's reading: vision failed on them twice (--retry-refused tries them "
                             "again)" % gave)
        return o
    if tesseract:
        scan_here = pdfs and pdfs >= 0.9 * max(1, raw)
        damaged = level in ("moderate", "material")
        if scan_here and (damaged or en < 0.95 * n) and gave and not tryable:   # READ_IN_2026_10_13
            o.update(path="source", why=("Tesseract's text: %s; vision read %d of its %d pages and failed twice on the "
                                         "other %d: the scan resists repair" % (lvl, vpages, pdfs, gave)),
                     next=[q0 + " --find-source   (free: archive.org, the wisdomlib archive, GRETIL, the DSBC; "
                           "--ai about $0.002)"],
                     also=["the pages vision read can go in now: %s   (the plan, free)" % rp] if f.get("changed", 0) > 0 else [])
            return o
        if scan_here and (damaged or en < 0.95 * n):
            todo = max(0, pdfs - vpages - gave)   # READ_IN_2026_10_13: not the pages left to Tesseract
            est = todo * cpp
            cap = max(1.0, math.ceil(est * 1.25 * 10) / 10.0)
''')
edit('scripts/text_path.py', 6,
     r'''    f = {k: r.get(k) for k in ("passages", "english", "hindi", "vectors", "pictures", "stories", "debris_pct",
                                "vision_pct", "below_quality", "pdfs", "raw_pages", "vision_pages", "merged_pages",
                                "merged_complete", "cost_per_page")}
    f.update(doc=code, level=j.get("level") if r.get("debris_pct") else "-",
             misread_letters_pct=j.get("misread_letters_pct"), state=st.get("status"), reason=st.get("reason"),
''',
     r'''    f = {k: r.get(k) for k in ("passages", "english", "hindi", "vectors", "pictures", "stories", "debris_pct",
                                "vision_pct", "below_quality", "pdfs", "raw_pages", "vision_pages", "merged_pages",
                                "merged_complete", "cost_per_page", "vision_gave_up")}
    f.update(doc=code, level=j.get("level") if r.get("debris_pct") else "-",
             misread_letters_pct=j.get("misread_letters_pct"), state=st.get("status"), reason=st.get("reason"),
''')
edit('scripts/ocr_consensus.py', 7,
     r'''    stamp = "$(Get-Date -Format yyyyMMdd_HHmmss)"
    return "\n".join([
        '# --- only when the dashboard header reads "idle" (RUNBOOK 1). Backup first. ---',
        'python scripts\\db_backup.py "data\\context.db" "D:\\backups\\context_pre_consensus_%s_%s.db"' % (doc, stamp),
''',
     r'''    stamp = "$(Get-Date -Format yyyyMMdd_HHmmss)"
    return "\n".join([
        # READ_IN_2026_10_13: the changed pages only, in place (REINGEST_2026_10_12) come first; the whole text again
        # (below) deletes every translation, vector and review of the text
        "# --- the changed pages only: the unchanged passages keep their translations, vectors and reviews ---",
        "python scripts\\reingest_pages.py --doc %s                  # the plan, free" % doc,
        "python scripts\\reingest_pages.py --doc %s --apply          # a backup first; it asks for --replace N "
        "if it removes English" % doc,
        "python scripts\\ocr_consensus.py --doc %s --drift-only     # expect: 0 stale" % doc,
        "# --- or the whole text again: its translations, vectors and reviews are deleted ---",
        '# --- only when the dashboard header reads "idle" (RUNBOOK 1). Backup first. ---',
        'python scripts\\db_backup.py "data\\context.db" "D:\\backups\\context_pre_consensus_%s_%s.db"' % (doc, stamp),
''')


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if not bad:
            todo.append((p, out.replace("\n", nl).encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
        Path(tmp).write_bytes(data)
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_readin_" + stamp))
        t = p.with_name(p.name + ".tmp_readin"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed. The Natyasastra's assessment, free:")
    print("  python scripts\\repair_text.py --doc 2015_368408_Natyasastra-With")
    print("The dashboard needs no restart: its Assess and Chart the path again run these scripts as they are on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
