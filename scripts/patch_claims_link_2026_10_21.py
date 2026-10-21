#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_claims_link_2026_10_21.py  (2026-10-21)  CLAIMS_LINK_2026_10_21

The brain's first wire between a scholar and our texts (BRAIN_PATH_2026-10-21.md, phase B1). Part I of Raychaudhuri
(1923) is read: 2,010 claims on 99 pages, each with its page, its quotation checked and its cites read. Their names
(3,917 on the current claims, as the subject or the object) were matched to our entities only when --show was asked,
by a key loose enough to tie Arittha to Artha, and nothing was stored: the site could not be given what a name's page
needs ("what the scholars say of this name").

scripts/scholar_claims.py (needs CLAIMS_FIX_2026_10_21):
  - --link (free; data/context.db only read): each name of the current claims tied to our entities, in tiers, the first
    that ties winning: exact (the shelf's own key: scholar_shelf.key_of); a variant our texts record (entity_variants);
    loose (only a vowel's length differs: scholar_shelf.loose_of); a 1923 spelling (Rigveda, Kurukshetra, Asvapati,
    Chhandogya: only for a name without diacritics, the vowel r read as ri on both sides); then the same for a numbered
    namesake (Parikshit I and II: our texts name one Parikshit; the tie says "numbered") and an English plural (the
    Mallas, the Vaidehas; "plural": not by a variant, nor where its last letter is not the entity's: the Gandharis are
    not Gandhari). A common English word (king, god, goddess, raja: our variants hold such glosses) is never tied, and a
    variant, a spelling, a namesake or a plural only for a name with a capital. A spelling keeps doubled letters (Vajji
    is not Vaji, Kachchha not Kaca). Only an exact tie is certain; the rest say how they were made. A name that could be more
    than one of ours keeps each, with how many it could be (cands); where they share one key they are our own doubles
    (the Satapatha Brahmana twice), listed for the entity mender, not merged here.
  - claim_links (claims.db): claim, role, name, its key, entity id, canonical, kind, how, cands, linker (link-v1), when;
    claim_link_runs: each run's counts and the database it read. A run replaces the work's ties in one transaction.
  - --show: the ties stored, with how they were made, on how many claims, the other names tied to the same entity
    (Parikshit I), and a warning where our entity has changed since; before --link has run, as before.
  - --report: the ties (how, the most claimed of ours, the untied most named, claims read since the ties).
  - --csv: a column our_names.
tests/test_claims_fix_2026_10_21.py: its replay compares with the copy CLAIMS_LINK_2026_10_21 backed up, when there
  is one (the replay chain).
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_claimslink_<date>. No database change by the patch; nothing is called.

  python scripts\\patch_claims_link_2026_10_21.py --check
  python scripts\\patch_claims_link_2026_10_21.py
  python scripts\\scholar_claims.py --link
  python scripts\\scholar_claims.py --report
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'CLAIMS_LINK_2026_10_21'
NEEDS = {'scripts/scholar_claims.py': 'CLAIMS_FIX_2026_10_21', 'tests/test_claims_fix_2026_10_21.py': 'CLAIMS_FIX_2026_10_21'}
FILES = list(NEEDS)
TAG = 'claimslink'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


F = 'scripts/scholar_claims.py'

edit(F, 1, r'''The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""''', r'''CLAIMS_LINK_2026_10_21: --link (free) ties the names of the claims to our entities (data/context.db, only read): by the
shelf's key, a variant our texts record, a vowel's length, a 1923 spelling (Rigveda, Kurukshetra: only for a name
without diacritics), a numbered namesake (Parikshit I: our texts name one Parikshit) and an English plural (the
Mallas); a common English word (king, god) is never tied. The ties are kept in claim_links (claims.db), each with how
it was made and how many of our entities it could be; --show, --report and --csv use them.

  python scripts\\scholar_claims.py --link                           (free: the names tied to our entities)

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""''')

edit(F, 2, r'''CREATE INDEX IF NOT EXISTS ix_claim_names_pkey ON claim_names(pkey);
"""''', r'''CREATE INDEX IF NOT EXISTS ix_claim_names_pkey ON claim_names(pkey);
-- CLAIMS_LINK_2026_10_21: the names of the claims tied to our entities (--link); a run replaces the work's ties
CREATE TABLE IF NOT EXISTS claim_links(claim_id INTEGER NOT NULL, role TEXT, name TEXT, pkey TEXT, entity_id INTEGER NOT NULL,
  canonical TEXT, kind TEXT, how TEXT, cands INTEGER, linker TEXT, at TEXT);
CREATE INDEX IF NOT EXISTS ix_claim_links_claim ON claim_links(claim_id);
CREATE INDEX IF NOT EXISTS ix_claim_links_entity ON claim_links(entity_id);
CREATE INDEX IF NOT EXISTS ix_claim_links_pkey ON claim_links(pkey);
CREATE TABLE IF NOT EXISTS claim_link_runs(id INTEGER PRIMARY KEY AUTOINCREMENT, work TEXT NOT NULL, db TEXT,
  entities INTEGER, variants INTEGER, names INTEGER, tied INTEGER, many INTEGER, max_claim INTEGER, linker TEXT, at TEXT,
  mark TEXT);
"""''')

edit(F, 3, r'''

def show_name(a, con, code: str, work: dict) -> int:
''', r'''

# ---- CLAIMS_LINK_2026_10_21: the names of the claims tied to our entities -------------------------------------------
LINK_MARK = "CLAIMS_LINK_2026_10_21"
LINKER = "link-v1"
TIERS = ("exact", "variant", "loose", "spelling")
COMMON = frozenset((   # English words a claim may give as its subject: never a name of ours (our variants hold glosses)
    "king", "kings", "queen", "queens", "prince", "princes", "princess", "god", "gods", "goddess", "goddesses", "lord",
    "sage", "sages", "seer", "seers", "priest", "priests", "teacher", "teachers", "father", "mother", "son", "sons",
    "daughter", "brother", "wife", "people", "peoples", "tribe", "tribes", "country", "kingdom", "city", "river",
    "mountain", "hero", "heroes", "raja", "rajas", "the"))
NUMBERED = re.compile(r"\s+(?:[IVX]{1,4}|the (?:First|Second|Third|Elder|Younger|Great))$")


def skey(name: str) -> str:
    """A 1923 spelling's key (Rigveda, Kurukshetra, Asvapati, Chhandogya): the vowel r read as ri on both sides (so that
    Arittha is not Artha, as pkey would have it), diacritics, case, ch and chh, ksh and sh aside; doubled letters kept
    (Vajji is not Vaji, Kachchha not Kaca, Bhagga not Bhaga)."""
    s = unicodedata.normalize("NFC", name or "")
    s = re.sub("[\u1e5a-\u1e5d]", "ri", s)
    s = re.sub("[\u1e36-\u1e39]", "li", s)
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())
    for x, y in (("chh", "c"), ("ch", "c"), ("ksh", "ks"), ("sh", "s"), ("w", "v"), ("ee", "i"), ("oo", "u")):
        s = s.replace(x, y)
    return s


def entity_index(db: str, immutable: bool) -> tuple:
    """({tier: {key: {entity id}}, "final": {entity id: its last letter}}, {entity id: (canonical, kind)}, the number of
    variants): our entities, only read."""
    from scholar_shelf import key_of, loose_of
    c2 = connect_ro(db, immutable)
    try:
        ents = c2.execute("SELECT id, canonical, kind FROM entities").fetchall()
        try:
            var = c2.execute("SELECT entity_id, variant FROM entity_variants").fetchall()
        except sqlite3.Error:
            var = []
    finally:
        c2.close()
    idx = {t: {} for t in TIERS}
    idx["final"] = {}
    for eid, canon, _kind in ents:
        k = key_of(canon)
        if not k:
            continue
        idx["final"][eid] = unicodedata.normalize("NFC", canon).strip()[-1:].lower()
        idx["exact"].setdefault(k, set()).add(eid)
        idx["loose"].setdefault(loose_of(k), set()).add(eid)
        idx["spelling"].setdefault(skey(canon), set()).add(eid)
    for eid, v in var:
        k = key_of(v)
        if k:
            idx["variant"].setdefault(k, set()).add(eid)
    return idx, {e: (c, k) for e, c, k in ents}, len(var)


def tie(name: str, idx: dict) -> tuple:
    """(how, [entity ids]) for a claim's name, or ("", []): the first tier that ties (TIERS), then the same for a
    numbered namesake (Parikshit I) and an English plural (the Mallas). A variant, a spelling, a namesake and a plural
    only for a name with a capital; a spelling only for a name without diacritics; a common English word never. A
    plural is not tied by a variant, nor where its last letter is not the entity's (the Gandharis are not Gandhari)."""
    from scholar_shelf import key_of, loose_of
    name = unicodedata.normalize("NFC", re.sub(r"\s+", " ", name or "").strip())

    def base(n: str, proper: bool, plural: bool = False) -> tuple:
        k = key_of(n)
        if len(k) < 3 or k in COMMON:
            return "", []
        for t in TIERS:
            if t in ("variant", "spelling") and not proper or t == "variant" and plural:
                continue
            if t == "spelling" and not n.isascii():
                continue
            got = idx[t].get(k if t in ("exact", "variant") else loose_of(k) if t == "loose" else skey(n))
            if got and plural and t in ("loose", "spelling"):
                got = {e for e in got if idx["final"].get(e) == n[-1:].lower()}
            if got:
                return t, sorted(got)
        return "", []
    proper = name[:1].isupper()
    how, ids = base(name, proper)
    if ids or not proper:
        return how, ids
    m = NUMBERED.search(name)
    if m:
        how, ids = base(name[:m.start()], True)
        if ids:
            return "numbered " + how, ids
    if " " not in name and len(name) >= 5 and name.endswith("s") and not name.endswith("ss"):
        how, ids = base(name[:-1], True, plural=True)
        if ids:
            return "plural " + how, ids
    return "", []


def link(a, con, code: str, work: dict) -> int:
    """The names of the current claims tied to our entities (free; --db only read). The ties of this work's claims are
    replaced in one transaction, with the run's counts (claim_link_runs)."""
    from scholar_shelf import key_of
    print("scholar_claims %s: %s; its names tied to our entities (%s)" % (LINK_MARK, work["short"], LINKER))
    if not Path(a.db).exists():
        say("%s not found: our entities live there" % a.db, "")
        return 1
    try:
        idx, ents, nvar = entity_index(a.db, a.immutable)
    except sqlite3.Error as e:
        say("our entities were not read from %s (%s): nothing tied" % (a.db, e), "")
        return 1
    if not ents:
        say("no entities in %s: nothing tied" % a.db, "")
        return 1
    names = con.execute("SELECT n.claim_id, n.role, n.name, n.pkey FROM claim_names n JOIN claims c ON c.id = n.claim_id "
                        "WHERE c.work = ? AND c.read_id IN (%s) ORDER BY n.claim_id, n.rowid" % CURRENT,
                        (code, code)).fetchall()
    at, rows, hows, many, untied, doubles = now(), [], {}, 0, {}, {}
    for cid, role, name, pk in names:
        how, ids = tie(name, idx)
        if not ids:
            untied[name] = untied.get(name, 0) + 1
            continue
        hows[how] = hows.get(how, 0) + 1
        if len(ids) > 1:
            many += 1
            if len({key_of(ents[e][0]) for e in ids}) == 1:
                doubles[tuple(ids)] = doubles.get(tuple(ids), 0) + 1
        for eid in ids:
            rows.append((cid, role, name, pk, eid, ents[eid][0], ents[eid][1], how, len(ids), LINKER, at))
    tied = sum(hows.values())
    top_id = max((n[0] for n in names), default=0)   # a claim read after the run has a larger id (the clock may differ)
    with con:
        con.execute("DELETE FROM claim_links WHERE claim_id IN (SELECT id FROM claims WHERE work = ?)", (code,))
        con.executemany("INSERT INTO claim_links(claim_id, role, name, pkey, entity_id, canonical, kind, how, cands, "
                        "linker, at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.execute("INSERT INTO claim_link_runs(work, db, entities, variants, names, tied, many, max_claim, linker, at, "
                    "mark) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (code, str(a.db), len(ents), nvar, len(names), tied, many, top_id, LINKER, at, LINK_MARK))
    print("  our entities: %d (and %d variants of their names), read from %s" % (len(ents), nvar, a.db))
    print("  names on the current claims: %d; tied %d (%.0f%%); %d tie row(s) stored"
          % (len(names), tied, 100.0 * tied / len(names) if names else 0.0, len(rows)))
    print("  how: " + (", ".join("%s %d" % h for h in sorted(hows.items(), key=lambda x: (-x[1], x[0]))) or "none"))
    print("  tied to more than one of ours: %d (each kept, with how many it could be)" % many)
    if doubles:
        print("  our own doubles among them (one key, more than one entity: for the entity mender, not merged here):")
        for ids, n in sorted(doubles.items(), key=lambda x: -x[1])[:10]:
            print("    %s (%d name(s))" % (" / ".join("%s [%d]" % (ents[e][0], e) for e in ids), n))
    print("  untied, most named: " + (", ".join("%s %d" % u for u in sorted(untied.items(),
                                                                          key=lambda x: (-x[1], x[0]))[:15]) or "none"))
    say("%d of %d name(s) on the claims of %s tied to our entities (%d tie row(s)), free; %d untied"
        % (tied, len(names), work["short"], len(rows), len(names) - tied), "python scripts\\scholar_claims.py --report",
        ["python scripts\\scholar_claims.py --show Parikshit"])
    return 0


def links_of_key(a, con, code: str, key: str):
    """[(entity id, canonical, kind, mentions, note)] of the ties --link stored for a name's key, or None before --link
    has run for the work. The note: how, on how many claims, the other names tied to the entity, and a warning where our
    entity has changed since."""
    if not con.execute("SELECT 1 FROM claim_link_runs WHERE work = ? LIMIT 1", (code,)).fetchone():
        return None
    rows = con.execute("SELECT l.entity_id, l.canonical, l.kind, GROUP_CONCAT(DISTINCT l.how), COUNT(DISTINCT l.claim_id), "
                       "MAX(l.cands) FROM claim_links l JOIN claims c ON c.id = l.claim_id WHERE c.work = ? AND c.read_id "
                       "IN (%s) AND l.pkey = ? GROUP BY l.entity_id ORDER BY 5 DESC, 1" % CURRENT, (code, code, key)).fetchall()
    now_of, n_of = {}, {}
    if rows and Path(a.db).exists():
        try:
            c2 = connect_ro(a.db, a.immutable)
            try:
                for r in rows:
                    x = c2.execute("SELECT canonical FROM entities WHERE id = ?", (r[0],)).fetchone()
                    now_of[r[0]] = x[0] if x else None
                    n_of[r[0]] = c2.execute("SELECT COUNT(*) FROM entity_mentions WHERE entity_id = ?", (r[0],)).fetchone()[0]
            finally:
                c2.close()
        except sqlite3.Error:
            pass
    out = []
    for eid, canon, kind, hows, nc, cands in rows:
        also = con.execute("SELECT l.name, COUNT(DISTINCT l.claim_id) FROM claim_links l JOIN claims c ON c.id = l.claim_id "
                           "WHERE c.work = ? AND c.read_id IN (%s) AND l.entity_id = ? AND l.pkey != ? GROUP BY l.name "
                           "ORDER BY 2 DESC, 1 LIMIT 6" % CURRENT, (code, code, eid, key)).fetchall()
        note = "; tied (%s) on %d claim(s)%s" % (hows, nc, (", one of %d" % cands) if (cands or 1) > 1 else "")
        if also:
            note += "; also tied: " + ", ".join("%s %d" % x for x in also)
        if eid in now_of and now_of[eid] != canon:
            note += "; NOW %s in our entities: --link again" % (now_of[eid] or "not there")
        out.append((eid, canon, kind, n_of.get(eid, 0), note))
    return out


def link_report(a, con, code: str):
    """The report's lines on the ties (--link)."""
    run = con.execute("SELECT entities, names, tied, many, linker, at, db, max_claim FROM claim_link_runs WHERE work = ? "
                      "ORDER BY id DESC LIMIT 1", (code,)).fetchone()
    if not run:
        print("  our names: not tied yet (python scripts\\scholar_claims.py --link: free)")
        return
    ne, nn, nt, nm, linker, at, db, top_id = run
    print("  our names (%s, %s; %d of our entities, from %s): %d of %d name(s) tied; %d to more than one"
          % (linker, at, ne, db, nt, nn, nm))
    hows = con.execute("SELECT how, COUNT(*) FROM (SELECT DISTINCT l.claim_id, l.role, l.name, l.how FROM claim_links l "
                       "JOIN claims c ON c.id = l.claim_id WHERE c.work = ? AND c.read_id IN (%s)) GROUP BY how ORDER BY 2 "
                       "DESC, 1" % CURRENT, (code, code)).fetchall()
    print("    how: " + (", ".join("%s %d" % h for h in hows) or "none"))
    top = con.execute("SELECT l.entity_id, l.canonical, l.kind, COUNT(DISTINCT l.claim_id) FROM claim_links l JOIN claims c "
                      "ON c.id = l.claim_id WHERE c.work = ? AND c.read_id IN (%s) AND l.cands = 1 GROUP BY l.entity_id "
                      "ORDER BY 4 DESC, 2 LIMIT 12" % CURRENT, (code, code)).fetchall()
    print("    the most claimed of ours: " + (", ".join("%s (%s) %d" % t[1:] for t in top) or "none"))
    left = con.execute("SELECT n.name, COUNT(*) FROM claim_names n JOIN claims c ON c.id = n.claim_id WHERE c.work = ? AND "
                       "c.read_id IN (%s) AND NOT EXISTS (SELECT 1 FROM claim_links l WHERE l.claim_id = n.claim_id AND "
                       "l.role = n.role AND l.name = n.name) GROUP BY n.name ORDER BY 2 DESC, 1 LIMIT 12" % CURRENT,
                       (code, code)).fetchall()
    print("    untied, most named: " + (", ".join("%s %d" % u for u in left) or "none"))
    newer = con.execute("SELECT COUNT(*) FROM claims c WHERE c.work = ? AND c.read_id IN (%s) AND c.id > ?" % CURRENT,
                        (code, code, top_id or 0)).fetchone()[0]
    if newer:
        print("    %d claim(s) read since the ties were made: python scripts\\scholar_claims.py --link" % newer)


def names_of(con, cid: int) -> str:
    """The claim's names tied to ours, for the csv: canonical (entity id; how)."""
    return "; ".join("%s (%d; %s)" % (c, e, h) for e, c, h in con.execute(
        "SELECT DISTINCT entity_id, canonical, how FROM claim_links WHERE claim_id = ? ORDER BY entity_id", (cid,)))


def show_name(a, con, code: str, work: dict) -> int:
''')

edit(F, 4, r'''    shelf, ours = shelf_and_ours(a.db, a.immutable, k)
''', r'''    shelf, ours = shelf_and_ours(a.db, a.immutable, k)
    tied = links_of_key(a, con, code, k)   # CLAIMS_LINK_2026_10_21: the ties --link stored, once it has run
    if tied:
        ours = tied
''')

edit(F, 5, r'''    for eid, canon, kind, nm in ours:
        print("  ours: entity %d %s (%s), named %d time(s) in our texts" % (eid, canon, kind, nm))
''', r'''    for o in ours:
        eid, canon, kind, nm = o[:4]
        print("  ours: entity %d %s (%s), named %d time(s) in our texts%s" % (eid, canon, kind, nm,
                                                                              o[4] if len(o) > 4 else ""))
''')

edit(F, 6, r'''    bad = [r for r in rows if r[8] == "none"]
''', r'''    link_report(a, con, code)   # CLAIMS_LINK_2026_10_21
    bad = [r for r in rows if r[8] == "none"]
''')

edit(F, 7, r'''                    "quote_score", "stance", "hedge", "who", "cites", "ours"])
''', r'''                    "quote_score", "stance", "hedge", "who", "cites", "ours", "our_names"])   # CLAIMS_LINK_2026_10_21
''')

edit(F, 8, r'''                        "; ".join(c[0] for c in cs), "; ".join(sorted({c[3] for c in cs if c[3]}))])
''', r'''                        "; ".join(c[0] for c in cs), "; ".join(sorted({c[3] for c in cs if c[3]})), names_of(con, r[0])])
''')

edit(F, 9, r'''    ap.add_argument("--recite", action="store_true", help="free: the cites read again (cites-v2)")
''', r'''    ap.add_argument("--recite", action="store_true", help="free: the cites read again (cites-v2)")
    ap.add_argument("--link", action="store_true", help="free: the names tied to our entities (--db only read)")
''')

edit(F, 10, r'''        if a.recite:
            return recite(a, con, code, work)
''', r'''        if a.recite:
            return recite(a, con, code, work)
        if a.link:   # CLAIMS_LINK_2026_10_21
            return link(a, con, code, work)
''')

T = 'tests/test_claims_fix_2026_10_21.py'

edit(T, 11, r'''            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
''', r'''            for f in self.FILES:   # CLAIMS_LINK_2026_10_21 came after: its backup is what this patch made
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_claimslink_*"))
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


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
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("DONE: %s; backups .bak_%s_%s" % (MARK, TAG, stamp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
