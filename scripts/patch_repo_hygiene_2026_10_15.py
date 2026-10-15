#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_repo_hygiene_2026_10_15.py  (2026-10-15)  REPO_HYGIENE_2026_10_15

The release of 15 Oct (7d292ca) committed data/raw_mbh01_ce/ (225 files: MBh01's critical-edition e-text, as
import_mbh_gretil.py wrote it) and data/heal/ (heal_etext_meta.py's log). release.ps1 stages everything
(git add -A); its safety check refuses backups, raw_vision, raw_merged and probe, and .gitignore had data/raw/ but not
these. The e-text is BORI's ("Please do not provide copies of the text to others"), and both are made again from their
sources.

This patch:
  .gitignore: data/raw_*_ce/ and data/heal/.
  scripts/release.ps1: refuses those two as it refuses the other working dirs; and a path being taken out of the repo
    (git rm --cached: a D in the status) is never refused, so the removal can be released.
The files stay on disk; taking them out of the repo is `git rm -r --cached data/raw_mbh01_ce data/heal` (by hand),
then the release. Their copy in commit 7d292ca stays in the history: if the repo is public, that is the owner's
decision (make it private, or rewrite the history).

Needs SOURCE_DESK_2026_10_11 (.gitignore) and the release script of 2026-10 (its safety check).
Anchored, all-or-nothing, marker-idempotent per file; keeps line endings; backups .bak_hygiene_<date>.
  python scripts\\patch_repo_hygiene_2026_10_15.py --check
  python scripts\\patch_repo_hygiene_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "REPO_HYGIENE_2026_10_15"
NEEDS = {".gitignore": "SOURCE_DESK_2026_10_11", "scripts/release.ps1": "[safety] checking for large or excluded paths"}
FILES = list(NEEDS)

GITIGNORE_ADD = """
# REPO_HYGIENE_2026_10_15: an e-text's import (data/raw_mbh01_ce: the BORI critical edition, "do not provide copies of
# the text to others") and the heal logs are working files, made again from their sources
data/raw_*_ce/
data/heal/
"""

E = []   # (file, number, old, new); old None: append new at the end
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit(".gitignore", 1, None, GITIGNORE_ADD)

edit("scripts/release.ps1", 1,
     r'''foreach ($line in $status) {
    $p = $line.Substring(3).Trim('"')
    if ($p -match '(^|/|\\)(backups|raw_vision|raw_merged|probe)(/|\\)') { $bad += "excluded dir: $p"; continue }
''',
     r'''foreach ($line in $status) {
    $p = $line.Substring(3).Trim('"')
    # REPO_HYGIENE_2026_10_15: a path being taken out of the repo (git rm --cached: a D) is never refused
    if ($line.Substring(0, 2) -match 'D') { continue }
    if ($p -match '(^|/|\\)(backups|raw_vision|raw_merged|probe)(/|\\)') { $bad += "excluded dir: $p"; continue }
    # REPO_HYGIENE_2026_10_15: an e-text's import (data/raw_<book>_ce) and the heal logs stay out too
    if ($p -match '(^|/|\\)data(/|\\)(raw_[A-Za-z0-9]+_ce|heal)(/|\\)') { $bad += "excluded dir: $p"; continue }
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/release.ps1").exists():
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
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            if old is None:
                out = out + ("" if out.endswith("\n") else "\n") + new
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if not bad:
            data = out.replace("\n", nl).encode("utf-8")
            if rel.endswith(".ps1") and not all(x < 128 for x in data):
                problems.append("%s would not be ASCII (PowerShell 5.1)" % rel); continue
            todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_hygiene_" + stamp))
        t = p.with_name(p.name + ".tmp_hygiene"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next, by hand (the files stay on disk; they leave the repo):")
    print("  git rm -r --cached data/raw_mbh01_ce data/heal")
    print("  .\\scripts\\release.ps1 -MessageFile COMMIT_MSG_costtruth_20261015.txt   (its dry run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
