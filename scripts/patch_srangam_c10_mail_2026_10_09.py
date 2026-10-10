#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_c10_mail_2026_10_09.py  (2026-10-09)  CORNER_C10_MAIL_2026_10_09

For the SRANGAM repo (run from D:\\srangam-42267, on main, after STATE_LEARN_2026_10_09). The
Researchers' Corner level with the desk, and its email from nartiang.org:
  - the reading pages' desk bar (DeskActions) gains Edit (a story, a picture's words, a novel's page;
    never an approved one for a researcher), Check again (a story), and a novel's cast or every page
    drawn again (redo, a second click, with the estimate). The edit forms are a new, lazily loaded
    src/components/corpus/DeskEdit.tsx that starts from what the page shows and sends only what changed;
    the story, picture and novel pages pass their current values to the bar;
  - /corpus/corner: ideas for pictures and a cover, the text's ideas waiting to be drawn (Draw this idea),
    for editors its retired pictures (Restore), the ideas of a finished request in My requests, the email
    choices in Settings (everyone; the super admin: on/off, From, Reply-to, the site's address) and a Mail
    line in Sync. The new panels are a new, lazily loaded src/components/corpus/CornerPanels.tsx;
  - /admin/researchers: "Send it from nartiang.org" right after an invitation is made (the mailto stays);
  - src/lib/cornerMail.ts (the email calls; flushMail asks corner-mail to send what waits after every
    request) and src/lib/cornerC10.ts (the edit rules, the ideas); src/lib/corner.ts knows the new kinds;
  - the edge function supabase/functions/corner-mail (index.ts, lib.ts), copied unchanged from this
    repository's docs/cloud/E1_corner-mail/.
Needs, in the database, docs/cloud/C10b_corner_kinds_2026-10-09.sql and docs/cloud/C12_corner_mail_2026-10-09.sql
(this repo); before them the pages behave as before and show nothing new (a kind is offered only once
corner_kinds() lists it; no email control while corner_mail_prefs is missing).

The site's files travel in this repository, docs/srangam/C10_MAIL_2026-10-09/, under the paths they take in
Srangam (the edge function's two files are taken from docs/cloud/E1_corner-mail/, not duplicated there).
This script copies them in:
  - a NEW file is written only where nothing is, or where the same file already is (corner-mail: a
    different index.ts or lib.ts already there is refused, left alone);
  - a REPLACED file is written only over the exact version main has today (84409ca, STATE_LEARN applied):
    its md5 is recorded below, computed on the file's bytes with CRLF read as LF (the files are LF in git,
    so it is the md5 of the bytes in the repository), and a file changed since is refused;
  - docs/RELIABILITY_AUDIT.md gets Phase AC inserted after Phase AB (STATE_LEARN_2026_10_09), anchored on
    that heading, marker-idempotent; its other bytes are not touched (a checkout without that file is
    told so and left as it is);
  - every payload and source file is checked against its recorded md5 first.
All-or-nothing: everything is checked before anything is written; a failure while writing puts every
file back. Backups .bak_c10mail_<yyyymmdd>. A replaced or edited file keeps its own line endings; new
files are LF. Each file is written to a temporary name and moved into place (os.replace). Re-running
changes nothing ("Nothing to do.").

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_c10_mail_2026_10_09.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_c10_mail_2026_10_09.py"
Then: npm run typecheck ; npx vitest run ; npm run build ; the git add line it prints.
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, re, shutil, sys
from pathlib import Path

MARK = "CORNER_C10_MAIL_2026_10_09"
TAG = "c10mail"
ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "docs" / "srangam" / "C10_MAIL_2026-10-09"
FUNC_SRC = ROOT / "docs" / "cloud" / "E1_corner-mail"
FUNC_DEST = "supabase/functions/corner-mail"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces or None for a new file)
FILES = [
    ('src/__tests__/corner-mail.test.tsx', '1afb55e29d466f24b890ad1b04f5a533', None),
    ('src/__tests__/corpus-corner-c10.test.tsx', '263c834ce610ce70b5d2c738e8351435', None),
    ('src/components/corpus/CornerPanels.tsx', '7af5131feeb75da0a19ed3109ffde33a', None),
    ('src/components/corpus/DeskActions.tsx', '282d11d9404b1e79d7e85770d1b39e74', 'edbe32ca8a6c43fe6f9c1a66c7412e41'),
    ('src/components/corpus/DeskEdit.tsx', '32f8d126e0c85c66973b568396ca9a52', None),
    ('src/lib/corner.ts', 'c4bcda4f3f22b6049a0a6161a9f43bd9', '17df1668f6052cdb029b36019c0bac88'),
    ('src/lib/cornerC10.ts', '4e55d20993792fd8b7ed5502d87cd45e', None),
    ('src/lib/cornerMail.ts', '500beb7ad10df29cd2c4f60782d71677', None),
    ('src/pages/admin/Researchers.tsx', '3ca539a719ce2f8dcb3d50033f16b5af', '785bec298d1c25f82a315be87e9a7b01'),
    ('src/pages/corpus/CorpusCorner.tsx', '305cadeba95032ac0fd05e7d09b148db', '854ae8bf73c1dfb5f87f138d5ec0d137'),
    ('src/pages/corpus/CorpusImages.tsx', 'e0cae746a15567e9593c1bab3a9284dd', '2b4c7560669488804ab247ece1031cab'),
    ('src/pages/corpus/CorpusNovels.tsx', '459cd1faf55c6d3e5f0acf5cf53aa6c4', '956b1bc610d740789eecd6b3f6579d62'),
    ('src/pages/corpus/CorpusStories.tsx', '594429843afd5617fc9e9deea8fa5fbe', '792899376417e4038677de20ab92b0bf'),
]
# the edge function: (file name, md5 of docs/cloud/E1_corner-mail/<name> as released)
FUNC_FILES = [
    ('index.ts', '7aa38d65d9308108290b54bd2ad570b7'),
    ('lib.ts', 'f06e6167cea8bd72aaf3ad6825c03097'),
]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_PART = ("_append/RELIABILITY_AUDIT.phaseAC.md", "55d7e598512835038d02f74189d6a27c")
AUDIT_AFTER = re.compile(rb"(?m)^## Phase AB\b[^\r\n]*STATE_LEARN_2026_10_09[^\r\n]*")
NEXT_HEADING = re.compile(rb"(?m)^## ")

# STATE_LEARN_2026_10_09 (scripts/patch_srangam_state_learn_2026_10_09.py) wrote its marker into
# src/App.tsx and its file src/lib/cornerState.ts (which carries CORNER_STATE_S1_2026_10_09).
PREREQS = [
    ("src/App.tsx", b"STATE_LEARN_2026_10_09"),
    ("src/lib/cornerState.ts", b"CORNER_STATE_S1_2026_10_09"),
]


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def md5_lf(b: bytes) -> str:
    return md5(b.replace(b"\r\n", b"\n"))


def nl_of(raw: bytes) -> bytes:
    return b"\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else b"\n"


def backup_name(dest: Path, stamp: str) -> Path:
    bak = dest.with_name("%s.bak_%s_%s" % (dest.name, TAG, stamp))
    n = 2
    while bak.exists():
        bak = dest.with_name("%s.bak_%s_%s_%d" % (dest.name, TAG, stamp, n))
        n += 1
    return bak


def main() -> int:
    ap = argparse.ArgumentParser(description="CORNER_C10_MAIL_2026_10_09 for the Srangam repo")
    ap.add_argument("--check", action="store_true", help="check everything, write nothing")
    a = ap.parse_args()
    if not Path("src/App.tsx").exists() or not Path("supabase").is_dir():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    if not PAYLOAD.is_dir():
        print("FAIL: the payload folder is missing: %s" % PAYLOAD); return 2
    for rel, needle in PREREQS:
        p = Path(rel)
        if not p.exists() or needle not in p.read_bytes():
            print("REFUSE: STATE_LEARN_2026_10_09 must be applied first (%s has no %s)."
                  % (rel, needle.decode("ascii"))); return 1
    problems, todo, skip, notes = [], [], [], []
    owned = []   # what this patch puts in the tree: the git add list

    # 1. the site's files
    for rel, want, old in FILES:
        owned.append(rel)
        src = PAYLOAD / rel
        if not src.exists():
            problems.append("payload file missing: %s" % rel); continue
        data = src.read_bytes()
        if md5(data) != want:
            problems.append("payload file differs from the one released: %s" % rel); continue
        dest = Path(rel)
        if dest.is_dir():
            problems.append("%s is a folder" % rel); continue
        if dest.exists():
            raw = dest.read_bytes()
            have = md5_lf(raw)
            if have == want:
                skip.append(rel); continue
            if old is None:
                problems.append("%s already exists and is not this file (left alone)" % rel); continue
            if have != old:
                problems.append("%s has changed since this patch was made (md5 %s, expected %s)" % (rel, have, old)); continue
            if nl_of(raw) == b"\r\n":
                data = data.replace(b"\n", b"\r\n")
            todo.append((dest, data, True))
        else:
            if old is not None:
                problems.append("%s not found (it should exist and be replaced)" % rel); continue
            todo.append((dest, data, False))

    # 2. the edge function corner-mail, from docs/cloud/E1_corner-mail
    fdir = Path(FUNC_DEST)
    if fdir.exists() and not fdir.is_dir():
        problems.append("%s exists and is not a folder" % FUNC_DEST)
    else:
        for name, want in FUNC_FILES:
            rel = "%s/%s" % (FUNC_DEST, name)
            owned.append(rel)
            src = FUNC_SRC / name
            if not src.exists():
                problems.append("edge function source missing: %s" % src); continue
            data = src.read_bytes()
            if md5(data) != want:
                problems.append("edge function source differs from the one released: docs/cloud/E1_corner-mail/%s" % name); continue
            dest = Path(rel)
            if dest.exists():
                if md5_lf(dest.read_bytes()) == want:
                    skip.append(rel); continue
                problems.append("a different corner-mail already exists: %s is not this file (left alone)" % rel); continue
            todo.append((dest, data, False))

    # 3. docs/RELIABILITY_AUDIT.md: Phase AC after Phase AB
    part = PAYLOAD / AUDIT_PART[0]
    audit = Path(AUDIT)
    if not part.exists() or md5(part.read_bytes()) != AUDIT_PART[1]:
        problems.append("payload file missing or changed: %s" % AUDIT_PART[0])
    elif not audit.exists():
        notes.append("%s is not in this checkout: Phase AC not added (append %s by hand where it is)" % (AUDIT, AUDIT_PART[0]))
    else:
        owned.append(AUDIT)
        raw = audit.read_bytes()
        if MARK.encode() in raw:
            skip.append(AUDIT)
        else:
            m = AUDIT_AFTER.search(raw)
            if not m:
                problems.append("%s has no Phase AB heading (STATE_LEARN_2026_10_09); apply STATE_LEARN first" % AUDIT)
            else:
                anl = nl_of(raw)
                lines = part.read_bytes().replace(b"\r\n", b"\n").strip(b"\n").split(b"\n")
                block = anl.join(lines)
                nxt = NEXT_HEADING.search(raw, m.end())
                if nxt:
                    out = raw[:nxt.start()] + block + anl + anl + raw[nxt.start():]
                else:
                    out = raw + (anl if raw.endswith(b"\n") else anl + anl) + block + anl
                todo.append((audit, out, True))

    for rel in skip:
        print("skip %s (already this version)" % rel)
    for x in notes:
        print("NOTE: " + x)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        for dest, _, replaced in todo:
            print("would %s %s" % ("replace" if replaced else "add", dest.as_posix()))
        print("CHECK OK: %d file(s) to write (%d replaced or edited, %d new). Nothing written."
              % (len(todo), sum(1 for t in todo if t[2]), sum(1 for t in todo if not t[2])))
        return 0
    present = [r for r in owned if Path(r).exists() or any(d.as_posix() == r for d, _, _ in todo)]
    if not todo:
        print("Nothing to do.")
        print("git add -- " + " ".join(present))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    done = []
    made_dirs = []
    try:
        for dest, data, replaced in todo:
            if not dest.parent.exists():
                for p in reversed([dest.parent] + list(dest.parent.parents)):
                    if not p.exists():
                        p.mkdir()
                        made_dirs.append(p)
            bak = None
            if replaced:
                bak = backup_name(dest, stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, dest)
            done.append((dest, bak))
            print("%s %s" % ("replaced" if replaced else "added", dest.as_posix()))
    except Exception as e:
        print("FAIL while writing: %s: %s. Putting everything back." % (type(e).__name__, e))
        for dest, bak in reversed(done):
            if bak is not None:
                shutil.copy2(bak, dest)
            elif dest.exists():
                dest.unlink()
            print("restored %s" % dest.as_posix())
        for p in reversed(made_dirs):
            try:
                p.rmdir()
            except OSError:
                pass
        return 2
    print("Backups: *.bak_%s_%s (not for git)." % (TAG, stamp))
    print("Next: npm run typecheck ; npx vitest run ; npm run build")
    print("Then ask Lovable to deploy the edge function corner-mail, and add RESEND_API_KEY in Lovable Secrets.")
    print("git add -- " + " ".join(present))
    return 0


if __name__ == "__main__":
    sys.exit(main())
