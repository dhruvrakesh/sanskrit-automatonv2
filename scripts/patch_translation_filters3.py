#!/usr/bin/env python3
"""patch_translation_filters3.py  (MARK FILTERS3_2026_09_27)

Third pass, from the outcome ledger on the live corpus (2026-09-27):

  text_filters.py        strip_leading_source_echo(): an answer that repeats
                         the Sanskrit line(s) first and then translates is not
                         an echo. 3 of 3 Aphorisms Hindi "echo-filter" empties
                         in data/translate_outcomes.jsonl were exactly that.
  translate_passages.py  calls it before the echo test; prints [UNQUOTE];
                         the ledger records the raw answer as "salvaged".
  dashboard.py           /api/db/open reports snapshot_age_s, and refreshes a
                         Datasette it started itself when refresh=true or the
                         snapshot is older than max_age_s (600). A Datasette
                         left by an earlier dashboard is reported stale, never
                         killed. The snapshot of 12:57 that hid every v3 row
                         was exactly that case.
  dashboard_static.html  the Database toast says how old the snapshot is.

  python scripts/patch_translation_filters3.py --root .           # check
  python scripts/patch_translation_filters3.py --root . --apply   # write

All anchors must match exactly once before anything is written; backups
<name>.bak_tf3_20260927; line endings preserved. Jobs that START after this
use it; a running job keeps its code. dashboard.py needs a restart.
"""
import argparse, os, py_compile, shutil, sys
from pathlib import Path

MARK = 'FILTERS3_2026_09_27'
EDITS = [
  ('scripts/text_filters.py', [
    ('strip_leading_source_echo',
     'def is_source_echo(src: str, out: str, lang: str = "en") -> bool:',
     '# -- A leading copy of the source is not an echo (FILTERS3_2026_09_27) --------\n# Measured in data/translate_outcomes.jsonl on 2026-09-27: three Aphorisms\n# Hindi answers were full, faithful translations that the model PREFIXED with\n# the Sanskrit it was given ("tat-samkhya-amrtatva-upadesat || / usaki (bhakti\n# ki) samkhya ..."). is_source_echo() sees the whole source inside the output\n# and empties the verse. This drops only LEADING lines that are the source\n# again - Devanagari lines whose words are >= 80% words of the source and\n# carry no Hindi function word - and keeps the rest when anything is left.\n_DEV_WORD_RE = re.compile(r"[\u0900-\u097f]+")\n\n\ndef strip_leading_source_echo(src: str, out: str, lang: str = "en") -> str:\n    """Return out without leading lines that merely repeat the source."""\n    if not src or not out:\n        return out\n    stoks = set(_DEV_WORD_RE.findall(src))\n    if not stoks:\n        return out\n    lines = out.split("\\n")\n    k = 0\n    while k < len(lines):\n        ln = lines[k].strip()\n        if not ln or ln in ("/", "//"):\n            k += 1\n            continue\n        toks = _DEV_WORD_RE.findall(ln)\n        if not toks or frac_devanagari(ln) <= 0.5:\n            break\n        inside = sum(1 for t in toks if t in stoks) / len(toks)\n        words = set(ln.replace("(", " ").replace(")", " ").split())\n        if inside >= 0.8 and not (lang == "hi" and words & set(_HI_FUNC_WORDS)):\n            k += 1\n            continue\n        break\n    if k == 0:\n        return out\n    rest = "\\n".join(lines[k:]).strip()\n    return rest if len(rest) >= 8 else out\n\n\ndef is_source_echo(src: str, out: str, lang: str = "en") -> bool:'),
  ]),
  ('scripts/translate_passages.py', [
    ('import',
     '                          is_source_echo, salvage_translation)\n',
     '                          is_source_echo, salvage_translation,\n                          strip_leading_source_echo)   # FILTERS3_2026_09_27\n'),
    ('unquote before the echo test',
     '                if translation and is_source_echo(cleaned, translation, TGT):\n',
     '                if translation:   # FILTERS3_2026_09_27: a repeated source line is not an echo\n                    _unq = strip_leading_source_echo(cleaned, translation, TGT)\n                    if _unq != translation:\n                        print(f"  [UNQUOTE] p{page_no}.{idx}: dropped the repeated source line(s)")\n                        translation = _unq\n                if translation and is_source_echo(cleaned, translation, TGT):\n'),
  ]),
  ('scripts/dashboard.py', [
    ('snapshot age and refresh',
     '    if _port_serving("127.0.0.1", port):\n        return jsonify({"url": url, "status": "already-running"})\n',
     '    # FILTERS3_2026_09_27: say how old the snapshot is, and refresh it when\n    # asked or when it is older than max_age_s (default 600) - but only a\n    # Datasette THIS dashboard started; one left by an earlier dashboard\n    # process is reported, never killed from here.\n    _snap = ROOT / "query_snapshot.db"\n    _age = (time.time() - _snap.stat().st_mtime) if _snap.exists() else None\n    if _port_serving("127.0.0.1", port):\n        _p = _DATASETTE.get("proc")\n        _owned = _p is not None and _p.poll() is None\n        try:\n            _max = float(data.get("max_age_s", 600))\n        except (TypeError, ValueError):\n            _max = 600.0\n        _want = bool(data.get("refresh")) or (_age is not None and _age > _max)\n        if not (_want and _owned):\n            return jsonify({"url": url, "status": "already-running",\n                            "snapshot_age_s": int(_age) if _age is not None else None,\n                            "owned": _owned, "stale": bool(_want and not _owned)})\n        _p.terminate()\n        try:\n            _p.wait(timeout=10)\n        except Exception:\n            _p.kill()\n        for _i in range(20):\n            if not _port_serving("127.0.0.1", port):\n                break\n            time.sleep(0.5)\n'),
  ]),
  ('scripts/dashboard_static.html', [
    ('toast names the snapshot age',
     "      toast(running ? 'Opening database\u2026' : 'Snapshotting + starting Datasette (a few seconds)\u2026');\n",
     "      // FILTERS3_2026_09_27: say how old the snapshot is\n      var age = (d.snapshot_age_s != null) ? (' (snapshot ' + Math.round(d.snapshot_age_s / 60) + ' min old' + (d.stale ? ' - stale: close Datasette to refresh' : '') + ')') : '';\n      toast(running ? ('Opening database' + age + '\u2026') : 'Snapshotting + starting Datasette (a few seconds)\u2026');\n"),
  ]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    plan, bad = [], 0
    for rel, eds in EDITS:
        p = root / rel
        if not p.exists():
            print("  MISSING  %s" % rel); bad += 1; continue
        raw = p.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
        if MARK in text:
            print("  already  %s (marker present) - skipped" % rel); continue
        new = text
        for name, old, rep in eds:
            n = new.count(old)
            if n != 1:
                print("  ANCHOR   %s :: %s matched %d time(s), need exactly 1" % (rel, name, n))
                bad += 1; continue
            new = new.replace(old, rep, 1)
            print("  ok       %s :: %s" % (rel, name))
        if MARK not in new:
            print("  ANCHOR   %s :: marker not present after edits" % rel); bad += 1
        plan.append((p, crlf, new))
    if bad:
        print("REFUSED: %d problem(s); nothing written." % bad); return 2
    if not plan:
        print("nothing to do - every file already patched."); return 0
    if not a.apply:
        print("CHECK PASSED for %d file(s). Re-run with --apply to write." % len(plan)); return 0
    for p, crlf, new in plan:
        bak = p.with_name(p.name + ".bak_tf3_20260927")
        if not bak.exists():
            shutil.copy2(p, bak)
        tmp = p.with_name(p.name + ".tmp_patch")
        tmp.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
        os.replace(str(tmp), str(p))   # atomic: a job starting now reads old or new, never half
        if p.suffix == ".py":
            py_compile.compile(str(p), doraise=True)
        print("  WROTE    %s  (backup %s)" % (p.name, bak.name))
    print("APPLIED. To undo: copy each .bak_tf3_20260927 back over its file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
