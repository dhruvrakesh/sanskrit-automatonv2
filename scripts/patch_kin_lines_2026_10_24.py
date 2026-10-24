#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
KIN_LINES_2026_10_24: the lines of descent in exports\\kin_lineages.md joined by the index's own entries.

The fault (24 Oct, after the full run): kin_index.py joined the parent relations by OUR entity ids, and one of our ids
stands for every person of a name (among the entries with relations, 1,036 names are borne by more than one entry of
the same index: Prthu, Manu, Vasu ...).
So its longest line ran 40 steps from Narayana through Karna and Janamejaya to Asvatthaman, hopping from one person to
another of the same name. It was not a lineage.

The fix: lines() joins a step only where the person is one entry of that index: the index has one entry of the name,
or the homonym's number (II, [2], "3.") names one, or exactly one homonym names the other person in its own entry.
Otherwise the line ends there. Lines never cross from one index to another, and each says how many of its steps both
entries (the parent's and the child's) state; a line much the same as a longer one (a name spelt otherwise, a
branch) is counted under it, not listed again. lineages() is kept for the record and no longer used. After the
full run the NEXT line no longer asks for the full run again. Nothing else changes: the reads, the checks, kin_edges, the matrix,
the agreement and the cards are as before.

Run from the repo root:  python scripts\\patch_kin_lines_2026_10_24.py --check   then without --check; then
python scripts\\kin_index.py --check (free) rewrites the exports. Backup: scripts\\kin_index.py.bak_kin_lines_ and the
date. Test: tests\\test_kin_lines_2026_10_24.py.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'KIN_LINES_2026_10_24'
TAG = 'kin_lines'
FILES = ['scripts/kin_index.py']
NEEDS = {'scripts/kin_index.py': 'KIN_CLOSE_2026_10_24'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/kin_index.py', 1, '        titles = dict(con.execute("SELECT code, title FROM shelf_sources")) if has(con, "shelf_sources") else {}\n        ci = claims_index(a.claims_db)\n\n        def tie(name: str, entry_id: int, head: str):',
     '        titles = dict(con.execute("SELECT code, title FROM shelf_sources")) if has(con, "shelf_sources") else {}\n        ci = claims_index(a.claims_db)\n        heads = heads_index(con)   # KIN_LINES_2026_10_24\n\n        def tie(name: str, entry_id: int, head: str):')

edit('scripts/kin_index.py', 2, '    summary = summarize(rows, how_links, titles)\n    if write:\n        export(root, rows, summary)\n    return summary\n',
     '    summary = summarize(rows, how_links, titles)\n    if write:\n        export(root, rows, summary, heads)\n    return summary\n')

edit('scripts/kin_index.py', 3, '\ndef lineages(rows: list, min_len: int = 4, top: int = 25) -> list:\n    """The father-to-son lines the kept, tied parent relations make: (chain of entity names, the edges\' sources)."""\n    child = collections.defaultdict(set)\n    has_parent = set()',
     '\ndef lineages(rows: list, min_len: int = 4, top: int = 25) -> list:\n    """The father-to-son lines the kept, tied parent relations make: (chain of entity names, the edges\' sources).\n    KIN_LINES_2026_10_24: NOT used for the export any more. It joins the relations by OUR entity ids, and one id stands\n    for every homonym of a name (among the entries read, 1,036 names are borne by more than one entry of the same\n    index), so its lines jump\n    from one person to another of the same name (a 40-step line from Narayana through Karna to Asvatthaman, 24 Oct).\n    lines() below joins only the index\'s own entries."""\n    child = collections.defaultdict(set)\n    has_parent = set()')

edit('scripts/kin_index.py', 4, '            break\n    return out\n\n',
     '            break\n    return out\n\n\n# ---- KIN_LINES_2026_10_24: the lines of descent by the index\'s own entries ---------------------------------------\nROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}\n\n\ndef _roman(t: str) -> int:\n    t, n, prev = t.lower(), 0, 0\n    for ch in reversed(t):\n        v = ROMAN.get(ch, 0)\n        n, prev = (n - v, prev) if v < prev else (n + v, v)\n    return n\n\n\ndef split_mark(name: str) -> tuple:\n    """(the folded name, the homonym\'s number or 0): "Janamejaya (II)", "Jaratkaru[2]", "3. Rsabha", "Rsabha (3)" and\n    "Sraddha(devi) (IV)" (a gloss in brackets set aside) give the number the index gives its homonyms."""\n    s, mark = (name or "").strip(), 0\n    m = re.match(r"^(\\d{1,2})\\.\\s+(.+)$", s)\n    if m:\n        mark, s = int(m.group(1)), m.group(2)\n    else:\n        m = re.search(r"\\s*(?:\\((\\d{1,2}|[ivxlc]{1,6})\\)|\\[(\\d{1,2})\\])\\s*$", s, flags=re.I)\n        if m:\n            g = m.group(1) or m.group(2)\n            mark, s = (int(g) if g.isdigit() else _roman(g)), s[:m.start()]\n    s = re.sub(r"\\([^)]*\\)|\\[[^\\]]*\\]", " ", s)\n    return fold_loose(s), mark\n\n\ndef heads_index(con, sources=SOURCES) -> dict:\n    """{source: {folded name: [(entry id, number)]}} and {(source, entry id): the head as printed}, from the shelf."""\n    by, shown = {s: collections.defaultdict(list) for s in sources}, {}\n    if not has(con, "shelf_entries"):\n        return {"by": by, "shown": shown}\n    q = "SELECT id, source, head FROM shelf_entries WHERE source IN (%s)" % ",".join("?" * len(sources))\n    for eid, src, head in con.execute(q, tuple(sources)):\n        base, mark = split_mark(head)\n        if base:\n            by[src][base].append((eid, mark))\n            shown[(src, eid)] = head\n    return {"by": by, "shown": shown}\n\n\ndef heads_from_rows(rows: list) -> dict:\n    """The same index from the rows alone (their entries\' heads), when the shelf is not at hand."""\n    by, shown = collections.defaultdict(lambda: collections.defaultdict(list)), {}\n    for r in rows:\n        k = (r["source"], r["entry_id"])\n        if k in shown:\n            continue\n        base, mark = split_mark(r["head"])\n        if base:\n            by[r["source"]][base].append((r["entry_id"], mark))\n            shown[k] = r["head"]\n    return {"by": by, "shown": shown}\n\n\ndef lines(rows: list, heads: dict, min_len: int = 4, top: int = 20) -> dict:\n    """{source: [(the heads elder first, the steps stated in both entries, the lines much the same left out)]}: the\n    parent relations the index states,\n    joined only where a person is one entry of that index. A name is that entry when the index has one entry of that\n    name, or the number names one homonym, or (homonyms, no number) exactly one of them names the other person in its\n    own relations. Else the line ends there. Lines never cross from one index to another."""\n    by, shown = heads["by"], heads["shown"]\n    par = [r for r in rows if r["kept"] and CLASS[r["relation"]][0] == "parent"]\n    names_in = collections.defaultdict(set)\n    for r in par:\n        names_in[(r["source"], r["entry_id"])].add(split_mark(r["object"])[0])\n        names_in[(r["source"], r["entry_id"])].add(split_mark(r["subject"])[0])\n\n    def resolve(src: str, name: str, other: str):\n        base, mark = split_mark(name)\n        cands = by.get(src, {}).get(base, [])\n        if mark:\n            got = [e for e, m in cands if m == mark]\n            return got[0] if len(got) == 1 else None\n        if len(cands) == 1:\n            return cands[0][0]\n        got = [e for e, _m in cands if other and other in names_in.get((src, e), ())]\n        return got[0] if len(got) == 1 else None\n\n    out = {}\n    for src in sorted({r["source"] for r in par}):\n        child, has_parent, said = collections.defaultdict(set), set(), collections.defaultdict(set)\n        for r in (x for x in par if x["source"] == src):\n            hb, hm = split_mark(r["head"])\n            sb, sm = split_mark(r["subject"])\n            s = r["entry_id"] if sb == hb and sm in (0, hm) else resolve(src, r["subject"], hb)\n            o = resolve(src, r["object"], sb)\n            if s is None or o is None or s == o:\n                continue\n            _, p, c = norm(r["relation"], s, o)\n            child[p].add(c)\n            has_parent.add(c)\n            said[(p, c)].add(r["entry_id"])\n        best, steps = [], 0\n        for root_ in sorted(p for p in child if p not in has_parent):\n            stack = [[root_]]\n            while stack and steps < 200000:\n                steps += 1\n                path = stack.pop()\n                nxt = [c for c in child.get(path[-1], ()) if c not in path]\n                if not nxt or len(path) >= 60:\n                    if len(path) >= min_len:\n                        best.append(path)\n                    continue\n                stack.extend(path + [c] for c in sorted(nxt, reverse=True))\n        best.sort(key=lambda p: (-len(p), p))\n        got, seen = [], []\n        for p in best:\n            sp = set(p)\n            near = [i for i, q in enumerate(seen) if sp <= q or len(sp & q) >= 0.75 * len(sp)]\n            if near:   # the same line again, or with one name spelt another way (Mahadrti, Mahadhrti)\n                got[near[0]][2] += 1\n                continue\n            if len(got) >= top:\n                continue\n            seen.append(sp)\n            both = sum(1 for i in range(len(p) - 1) if {p[i], p[i + 1]} <= said[(p[i], p[i + 1])])\n            got.append([[shown.get((src, e), str(e)) for e in p], both, 0])\n        out[src] = [tuple(x) for x in got]\n    return out\n\n\ndef lines_text(found: dict) -> str:\n    text = ["# Lines of descent in the indexes (KIN_LINES_2026_10_24)", "",\n            "Each line joins the parent relations one index states, elder first, and only where a person is one entry "\n            "of that index: the index has one entry of the name, or its number names one homonym, or exactly one "\n            "homonym names the other person in its own entry. A line never jumps from one person to another of the "\n            "same name, nor from one index to another. \\"Both entries\\" counts the steps stated by the parent\'s entry "\n            "and by the child\'s. Every step is in kin_edges.csv with its words and its reference.", ""]\n    for src in ("pui", "vei", "inm"):\n        if src not in found:\n            continue\n        text.append("## %s" % SHORT.get(src, src))\n        text.append("")\n        if not found[src]:\n            text.append("No line of four generations or more.")\n        for chain, both, variants in found[src]:\n            text.append("- %s  (%d generations; %d of %d steps in both entries%s)" % (\n                " > ".join(chain), len(chain), both, len(chain) - 1,\n                "; %d more line(s) much the same, a name spelt otherwise or a branch" % variants if variants else ""))\n        text.append("")\n    return "\\n".join(text) + "\\n"\n\n')

edit('scripts/kin_index.py', 5, '\n\ndef export(root: Path, rows: list, summary: dict):\n    out = root / "exports"\n    out.mkdir(parents=True, exist_ok=True)',
     '\n\ndef export(root: Path, rows: list, summary: dict, heads: dict = None):\n    out = root / "exports"\n    out.mkdir(parents=True, exist_ok=True)')

edit('scripts/kin_index.py', 6, '        for r in ag:\n            w.writerow(r)\n    lin = lineages(rows)\n    text = ["# Father-to-son lines in the indexes (%s)" % MARK, "",\n            "Each line joins the parent relations the indexes state (kept and tied to our names), elder first; the "\n            "sources of each step are in brackets (pui the Purana Index, vei the Vedic Index, inm Soerensen).", ""]\n    for chain, srcs in lin:\n        text.append("- " + " > ".join("%s [%s]" % (chain[i], srcs[i]) for i in range(len(srcs))) + " > " + chain[-1])\n    (out / "kin_lineages.md").write_text("\\n".join(text) + "\\n", encoding="utf-8")\n    (out / "kin_cards.md").write_text(cards(rows), encoding="utf-8")\n    summary = dict(summary, agreement=collections.Counter(r["state"] for r in ag), lineages=len(lin))',
     '        for r in ag:\n            w.writerow(r)\n    found = lines(rows, heads if heads and heads.get("shown") else heads_from_rows(rows))   # KIN_LINES_2026_10_24\n    lin = [x for v in found.values() for x in v]\n    (out / "kin_lineages.md").write_text(lines_text(found), encoding="utf-8")\n    (out / "kin_cards.md").write_text(cards(rows), encoding="utf-8")\n    summary = dict(summary, agreement=collections.Counter(r["state"] for r in ag), lineages=len(lin))')

edit('scripts/kin_index.py', 7, '    tied = sum(c.get("tied", 0) for c in s["by_source"].values())\n    left = sum(len(v) for v in todo.values()) if not a.yes else 0\n    say("%d relations read, %d kept after the checks, %d tied to our names; our verses checked by %s" % (\n        s["relations"], kept, tied, s["links"]),\n        "read exports\\\\kin_cards.md and kin_agreement.csv; then the full run: python scripts\\\\kin_index.py --yes "\n        "--per-source 0 --max-usd 4.50 (the plan prices it first: about $4)" if a.per_source else\n        "python scripts\\\\kin_index.py --show Janamejaya",\n        ["%d entries of the trial are not read yet: python scripts\\\\kin_index.py --yes" % left] if left else [])\n    return 0',
     '    tied = sum(c.get("tied", 0) for c in s["by_source"].values())\n    left = sum(len(v) for v in todo.values()) if not a.yes else 0\n    unread = sum(1 for src in sources for r in cands[src] if done.get(r[0]) != entry_sha(r[1], r[2])) \\\n        if not a.yes else -1   # KIN_LINES_2026_10_24: the full run\'s NEXT only while entries are unread\n    say("%d relations read, %d kept after the checks, %d tied to our names; our verses checked by %s" % (\n        s["relations"], kept, tied, s["links"]),\n        "read exports\\\\kin_cards.md and kin_agreement.csv; then the full run: python scripts\\\\kin_index.py --yes "\n        "--per-source 0 --max-usd 4.50 (the plan prices it first: about $4)" if a.per_source and unread != 0 else\n        "read exports\\\\kin_lineages.md and kin_cards.md; one name: python scripts\\\\kin_index.py --show Janamejaya",\n        ["%d entries of the trial are not read yet: python scripts\\\\kin_index.py --yes" % left] if left else [])\n    return 0')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
