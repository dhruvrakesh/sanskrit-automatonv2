#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_booksmith_plates.py  (2026-10-04)  BOOKSMITH_PLATES_2026_10_04

Adds an OPT-IN switch to scripts/booksmith_build.py:

    --plates none       (default) nothing changes: book.yaml is not touched
    --plates approved   the doc's APPROVED *generated* images from the image
                        library become Booksmith colour plates

What Booksmith can and cannot do (read from its source, 2026-10-04):
  * book.yaml `plate_paths` lists image files inside the project; the renderer
    places min(len(plate_paths), policy.illustrations_per_volume) of them,
    SPACED EVENLY through the book (renderer.py 305-310). There is no anchor:
    a plate does not sit next to its verse. Use export_html --images approved
    + export_pdf.py when placement at the verse matters.
  * Every plate is captioned by Booksmith itself: "Symbolic editorial artwork;
    not a textual witness or evidence-bearing diagram." That is right for a
    generated image and wrong for a scan of the source edition, so only
    kind='generated' images are sent. Our own captions are not shown there.
  * Plates are part of the frozen manifest (assets_sha256, config_sha256).
    Changing them makes an existing manifest stale.

So, with --plates approved:
  1. copy each approved generated image to <project>/assets/plates/imglib_<id>_v<ver>.<ext>
     (only when missing or different);
  2. compute the new plate list = the project's own plates (anything not named
     imglib_*) + ours, in anchor order, at most 12 in all (Booksmith's cap);
  3. if the list is unchanged: nothing is written (idempotent);
  4. if it changed and work/decisions.jsonl holds human review decisions:
     REFUSE - re-freezing would silently invalidate them; decide in Booksmith;
  5. otherwise back up book.yaml to work/book.yaml.bak_plates_<stamp>, clear
     the derived files (manifest, PDFs, reports) exactly as a changed witness
     does, and save plate_paths + illustrations_per_volume THROUGH Booksmith's
     own BookConfig model (validated, as set_audit_policy does).

  python scripts/patch_booksmith_plates.py --check
  python scripts/patch_booksmith_plates.py
Test: python -m unittest tests.test_booksmith_plates -v   (fails before, passes after)
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "BOOKSMITH_PLATES_2026_10_04"
TARGET = Path("scripts/booksmith_build.py")

HELPERS = r'''# BOOKSMITH_PLATES_2026_10_04 -------------------------------------------------
PLATE_PREFIX = "assets/plates/imglib_"
PLATE_CAP = 12        # Booksmith: illustrations_per_volume le=12


def approved_generated_images(db: str, doc: str) -> list[dict]:
    """APPROVED generated images of the doc, in anchor order. Read-only."""
    import sqlite3
    uri = Path(db).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        con.execute("PRAGMA query_only=1")
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='doc_images'").fetchone():
            return []
        rows = con.execute(
            """SELECT i.id, i.version, i.path, i.anchor_page, i.anchor_idx FROM doc_images i
               JOIN docs d ON d.id = i.doc_id
               WHERE d.code = ? AND i.status = 'approved' AND i.kind = 'generated' AND i.path IS NOT NULL
               ORDER BY i.anchor_page, i.anchor_idx, i.id""", (doc,)).fetchall()
    finally:
        con.close()
    out = []
    for iid, ver, path, pg, ix in rows:
        src = Path(path) if os.path.isabs(path) else ROOT / path
        out.append({"id": iid, "version": ver, "src": src, "page": pg, "idx": ix})
    return out


def plan_plates(current: list[str], images: list[dict], cap: int = PLATE_CAP) -> tuple[list[str], list[tuple]]:
    """(new plate_paths, [(src Path, relative dst)]). The project's own plates
    (anything not imglib_*) are kept first and never removed."""
    own = [p for p in current if not str(p).replace("\\", "/").startswith(PLATE_PREFIX)]
    room = max(0, cap - len(own))
    ours, copies = [], []
    for im in images[:room]:
        ext = (im["src"].suffix or ".jpg").lower()
        rel = "%s%d_v%d%s" % (PLATE_PREFIX, im["id"], im["version"] or 1, ext)
        ours.append(rel)
        copies.append((im["src"], rel))
    return own + ours, copies


def _booksmith_config_io(bs: Path, project: Path, new_paths=None, ipv=None) -> dict:
    """Read (and with new_paths, write) plate_paths and illustrations_per_volume
    through Booksmith's own model."""
    py = project_python(bs)
    script = (
        "import sys, json\n"
        "from pathlib import Path\n"
        "from nartiang_booksmith.config import load_yaml, save_yaml, project_paths\n"
        "from nartiang_booksmith.domain import BookConfig\n"
        "paths = project_paths(Path(sys.argv[1]))\n"
        "c = load_yaml(paths['config'], BookConfig)\n"
        "if len(sys.argv) > 2:\n"
        "    d = c.model_dump(mode='json')\n"
        "    d['plate_paths'] = json.loads(sys.argv[2])\n"
        "    d['policy']['illustrations_per_volume'] = int(sys.argv[3])\n"
        "    c = BookConfig.model_validate(d)\n"
        "    save_yaml(paths['config'], c)\n"
        "print('PLATES_JSON=' + json.dumps({'plate_paths': list(c.plate_paths),"
        " 'ipv': c.policy.illustrations_per_volume}))\n"
    )
    argv = [py, "-c", script, str(project)]
    if new_paths is not None:
        argv += [json.dumps(list(new_paths)), str(int(ipv))]
    p = run(argv)
    for line in (p.stdout or "").splitlines():
        if line.startswith("PLATES_JSON="):
            return json.loads(line[len("PLATES_JSON="):])
    raise RuntimeError("could not read plate_paths from %s" % project)


def sync_plates(bs: Path, project: Path, db: str, doc: str, config_io=None) -> dict:
    """Make the project's library plates match the approved generated images.
    Returns a small report for the sidecar. Raises RuntimeError on refusal."""
    io = config_io or (lambda new=None, ipv=None: _booksmith_config_io(bs, project, new, ipv))
    cur = io()
    images = approved_generated_images(db, doc)
    missing = [str(im["src"]) for im in images if not im["src"].exists()]
    images = [im for im in images if im["src"].exists()]
    new, copies = plan_plates(list(cur["plate_paths"]), images)
    pending = [(src, rel) for src, rel in copies
               if not (project / rel).exists() or sha256_of(project / rel) != sha256_of(src)]
    ipv = min(PLATE_CAP, len(new)) if new else cur["ipv"]
    rep = {"approved_generated": len(images) + len(missing), "missing_files": missing,
           "plates": new, "copied": len(pending), "dropped_over_cap": len(images) - len(copies)}
    if new == list(cur["plate_paths"]) and ipv == cur["ipv"] and not pending:
        rep["action"] = "unchanged"
        return rep
    decisions = project / "work" / "decisions.jsonl"
    if (project / "work" / "manifest.json").exists() and decisions.exists() and decisions.stat().st_size > 0:
        # Checked BEFORE any file is copied: a refused run leaves the project exactly as it was.
        raise RuntimeError("plates changed, but work/decisions.jsonl holds human review decisions frozen "
                           "against the current manifest; re-freezing would invalidate them silently. "
                           "Open the project in Booksmith and decide there, or run without --plates.")
    for src, rel in pending:
        (project / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, project / rel)
    cfg = project / "book.yaml"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (project / "work").mkdir(parents=True, exist_ok=True)
    shutil.copy2(cfg, project / "work" / ("book.yaml.bak_plates_" + stamp))
    cleared = []
    for p in [project / "work" / "manifest.json", project / "build" / "book.pdf",
              project / "build" / "layout-proof.pdf", project / "build" / "build-report.json",
              project / "build" / "qa-report.json"]:
        if p.exists():
            p.unlink(); cleared.append(p.name)
    io(new, ipv)
    rep.update(action="updated", cleared=cleared, ipv=ipv, backup="work/book.yaml.bak_plates_" + stamp)
    return rep


'''

EDITS = [
    ("helpers", "def project_python(bs: Path) -> Path:\n",
     HELPERS + "def project_python(bs: Path) -> Path:\n", 1),
    ("arg", '    ap.add_argument("--selftest", action="store_true")\n',
     '    ap.add_argument("--plates", default="none", choices=["none", "approved"],\n'
     '                    help="BOOKSMITH_PLATES_2026_10_04: approved = approved generated images from the "\n'
     '                         "image library become colour plates (evenly spaced; edits book.yaml).")\n'
     '    ap.add_argument("--selftest", action="store_true")\n', 1),
    ("sync", '        log("[3/6] ingest")\n',
     '        if args.plates == "approved":   # BOOKSMITH_PLATES_2026_10_04\n'
     '            log("[2b/6] plates from the image library")\n'
     '            state["plates"] = sync_plates(exe, project, args.db, doc)\n'
     '            log("      plates: %s (%d in book.yaml, %d copied)"\n'
     '                % (state["plates"]["action"], len(state["plates"]["plates"]), state["plates"]["copied"]))\n'
     '            save()\n'
     '        log("[3/6] ingest")\n', 1),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def apply(src: str):
    problems = []
    for need in ("import json", "import os", "import time", "ROOT = HERE.parent"):
        if need not in src:
            problems.append("needs %r in booksmith_build.py" % need)
    for label, old, new, n in EDITS:
        c = src.count(old)
        if c != n:
            problems.append("%s: matched %d times, expected %d" % (label, c, n))
        else:
            src = src.replace(old, new)
    if "import shutil" not in src:
        src = src.replace("import subprocess\n", "import shutil\nimport subprocess\n", 1)
    return src, problems


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    src, nl = load(TARGET)
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    new, problems = apply(src)
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits. Nothing written." % len(EDITS)); return 0
    tmp = TARGET.with_name(TARGET.name + ".tmp_plates")
    tmp.write_bytes(new.replace("\n", nl).encode("utf-8"))
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        tmp.unlink(missing_ok=True); print("REFUSING TO WRITE: would not compile:\n%s" % e); return 1
    bak = TARGET.with_name(TARGET.name + ".bak_plates_" + datetime.date.today().strftime("%Y%m%d"))
    shutil.copy2(TARGET, bak)
    os.replace(tmp, TARGET)
    print("PATCHED %s (backup %s). Default unchanged; use --plates approved." % (TARGET, bak.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
