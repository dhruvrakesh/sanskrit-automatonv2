#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_kin_salvage_2026_10_25.py  (2026-10-25)  KIN_SALVAGE_2026_10_25

scripts\\kin_index.py, after the full run of 24 Oct cost $0.22 where the plan said $0.04: two of Soerensen's
longest entries (12641 and 7692) ask for more relations than one answer holds; the reply was cut short (about
20,000 characters), was not the JSON asked for, was asked again twice (cut again), and the next run asked again:
three calls of each entry, about $0.13 a run.

  - a reply cut short keeps the relations it gives whole (salvage), and is not asked again;
  - in a call of one entry every relation is that entry's, whatever number the model gave it ("entry": 150);
  - an entry whose reading failed twice is not asked again unless --retry-failed; the plan says how many;
  - --salvage (free) reads again the failed replies already stored (the reads of 23 to 25 Oct).

Needs RELATIONS_INDEX_2026_10_23 and KIN_CLOSE_2026_10_24. Anchored, all-or-nothing, marker-idempotent; line endings
kept; a .bak_kinsalvage_<date> copy; compiled before anything is written. Test: tests\\test_kin_salvage_2026_10_25.py.

  python scripts\\patch_kin_salvage_2026_10_25.py --check
  python scripts\\patch_kin_salvage_2026_10_25.py
  python scripts\\kin_index.py --salvage
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'KIN_SALVAGE_2026_10_25'
TAG = 'kinsalvage'
FILES = ['scripts/kin_index.py']
NEEDS = {'scripts/kin_index.py': 'KIN_CLOSE_2026_10_24'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/kin_index.py', 1, "  python scripts\\\\kin_index.py --check                 free: the checks and the exports again\n  python scripts\\\\kin_index.py --show Janamejaya       one name's relations with their evidence\n\nStored in data/shelf/kin.db (beside claims.db; data/shelf/ is not committed; the Cologne shelf's terms, CC BY-NC-SA",
     '  python scripts\\\\kin_index.py --check                 free: the checks and the exports again\n  python scripts\\\\kin_index.py --show Janamejaya       one name\'s relations with their evidence\n  python scripts\\\\kin_index.py --salvage              free: the relations whole in a stored reply that was cut short\n\nKIN_SALVAGE_2026_10_25: a reply cut short (Soerensen\'s longest entries ask for more relations than one answer holds:\nentries 12641 and 7692, 25 Oct) keeps the relations it gives whole, and is not asked again (asked again it was cut\nagain: three calls of one entry, about $0.13 a run); in a call of one entry every relation is that entry\'s, whatever\nnumber the model gave it ("entry": 150); an entry whose reading failed twice is not asked again unless --retry-failed\n(the plan says how many); --salvage reads again, free, the failed replies already stored.\n\nStored in data/shelf/kin.db (beside claims.db; data/shelf/ is not committed; the Cologne shelf\'s terms, CC BY-NC-SA')

edit('scripts/kin_index.py', 2, 'EST_CHAR = 0.0000001    # ... plus about 0.3/3.5 of a millionth of a dollar a character of the entries\nEST_ENTRY = 0.0002      # ... plus the relations written back\nKIN_RX = re.compile(r"\\b(sons?|daughters?|father|mother|wife|wives|husband|brothers?|sisters?|grand(?:son|daughter|father)"\n                    r"|pupil|disciple|teacher|preceptor|king|queen|contemporar\\w*|patronymic|descendant|married"',
     'EST_CHAR = 0.0000001    # ... plus about 0.3/3.5 of a millionth of a dollar a character of the entries\nEST_ENTRY = 0.0002      # ... plus the relations written back\nGIVE_UP = 2             # KIN_SALVAGE_2026_10_25: an entry whose reading failed this often is not asked again by itself\nKIN_RX = re.compile(r"\\b(sons?|daughters?|father|mother|wife|wives|husband|brothers?|sisters?|grand(?:son|daughter|father)"\n                    r"|pupil|disciple|teacher|preceptor|king|queen|contemporar\\w*|patronymic|descendant|married"')

edit('scripts/kin_index.py', 3, '\n\ndef _s(x, n: int) -> str:\n    return re.sub(r"\\s+", " ", str(x or "")).strip()[:n]',
     '\n\ndef salvage(text: str):\n    """KIN_SALVAGE_2026_10_25: the relations given whole in a reply cut short ({"relations": [{...}, {...}, {"entr),\n    or None when there are none."""\n    t = text or ""\n    i = t.find(\'"relations"\')\n    if i < 0:\n        return None\n    j = t.find("[", i)\n    if j < 0:\n        return None\n    dec = json.JSONDecoder(strict=False)\n    out, pos = [], j + 1\n    while True:\n        k = t.find("{", pos)\n        if k < 0:\n            break\n        try:\n            obj, end = dec.raw_decode(t, k)\n        except ValueError:\n            break\n        if isinstance(obj, dict):\n            out.append(obj)\n        pos = end\n    return out or None\n\n\ndef _s(x, n: int) -> str:\n    return re.sub(r"\\s+", " ", str(x or "")).strip()[:n]')

edit('scripts/kin_index.py', 4, '        k = int(d.get("entry"))\n    except (TypeError, ValueError):\n        return None\n    rel = _s(d.get("relation"), 40).lower().replace(" ", "_")',
     '        k = int(d.get("entry"))\n    except (TypeError, ValueError):\n        k = None\n    if n_entries == 1:   # KIN_SALVAGE_2026_10_25: one entry to the call: every relation is that entry\'s\n        k = 1\n    if k is None:\n        return None\n    rel = _s(d.get("relation"), 40).lower().replace(" ", "_")')

edit('scripts/kin_index.py', 5, '\n\ndef done_entries(con, engine: str) -> dict:\n    return {e: s for e, s in con.execute("SELECT entry_id, entry_sha FROM kin_done WHERE prompt_version = ? AND "',
     '\n\ndef failures(con, engine: str) -> dict:\n    """KIN_SALVAGE_2026_10_25: {entry_id: failed reads} of the entries not read since, for this prompt and engine."""\n    out = collections.Counter()\n    done = {e for (e,) in con.execute("SELECT entry_id FROM kin_done WHERE prompt_version = ? AND engine = ?",\n                                      (PROMPT_VERSION, engine))}\n    for (ids,) in con.execute("SELECT entries FROM kin_reads WHERE status = \'failed\' AND prompt_version = ? AND "\n                              "engine = ?", (PROMPT_VERSION, engine)):\n        try:\n            for e in json.loads(ids or "[]"):\n                if e not in done:\n                    out[e] += 1\n        except (TypeError, ValueError):\n            continue\n    return dict(out)\n\n\ndef keep(store, rid: int, src: str, batch: list, rels: list, engine: str) -> int:\n    """KIN_SALVAGE_2026_10_25 (from read): a read\'s relations checked and stored, its entries marked done."""\n    kept = 0\n    for d in rels:\n        c = clean_relation(d, len(batch))\n        if not c:\n            continue\n        eid, head, body = batch[c["entry"] - 1]\n        text = entry_text(head, body)\n        store.execute("INSERT INTO kin (read_id, source, entry_id, head, subject, relation, object, words, "\n                      "refs, words_check, direction, at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",\n                      (rid, src, eid, head, c["subject"], c["relation"], c["object"], c["words"],\n                       json.dumps(c["refs"], ensure_ascii=False), words_check(c["words"], text),\n                       direction_check(c["relation"], c["words"]), now()))\n        kept += 1\n    for eid, head, body in batch:\n        store.execute("INSERT OR REPLACE INTO kin_done (entry_id, source, entry_sha, read_id, prompt_version, "\n                      "engine) VALUES (?,?,?,?,?,?)", (eid, src, entry_sha(head, body), rid, PROMPT_VERSION, engine))\n    store.execute("UPDATE kin_reads SET relations = ? WHERE id = ?", (kept, rid))\n    return kept\n\n\ndef salvage_stored(store, engine: str, cands: dict) -> dict:\n    """KIN_SALVAGE_2026_10_25 (--salvage, free): each failed read whose stored reply gives relations whole, kept as\n    a read would keep them; its entries marked done. A read whose entries changed since (or left the candidates) stays\n    as it is."""\n    by_id = {r[0]: (src, r) for src, rows in cands.items() for r in rows}\n    got = {"reads": 0, "salvaged": 0, "relations": 0, "entries": 0}\n    for rid, src, ids, raw in store.execute("SELECT id, source, entries, raw FROM kin_reads WHERE status = \'failed\' AND "\n                                            "prompt_version = ? AND engine = ? ORDER BY id",\n                                            (PROMPT_VERSION, engine)).fetchall():\n        got["reads"] += 1\n        try:\n            batch = [by_id[e][1] for e in json.loads(ids or "[]")]\n        except (KeyError, TypeError, ValueError):\n            continue\n        rels = parse_reply(raw or "") or salvage(raw or "")\n        if not batch or not rels:\n            continue\n        kept = keep(store, rid, src, batch, rels, engine)\n        store.execute("UPDATE kin_reads SET status = \'salvaged\', note = trim(coalesce(note, \'\') || \' salvaged by "\n                      "--salvage: \' || ? || \' relation objects\') WHERE id = ?", (str(len(rels)), rid))\n        store.commit()\n        got["salvaged"] += 1\n        got["relations"] += kept\n        got["entries"] += len(batch)\n    return got\n\n\ndef done_entries(con, engine: str) -> dict:\n    return {e: s for e, s in con.execute("SELECT entry_id, entry_sha FROM kin_done WHERE prompt_version = ? AND "')

edit('scripts/kin_index.py', 6, '            prompt, cut = batch_prompt(titles.get(src, src), batch)\n            reply, resp, err, spent, rels = "", None, "", 0.0, None\n            for attempt in range(3):\n                t0 = time.time()',
     '            prompt, cut = batch_prompt(titles.get(src, src), batch)\n            reply, resp, err, spent, rels = "", None, "", 0.0, None\n            salvaged = 0   # KIN_SALVAGE_2026_10_25\n            for attempt in range(3):\n                t0 = time.time()')

edit('scripts/kin_index.py', 7, '                if rels is not None:\n                    break\n                if attempt < 2 and caller is None:\n                    time.sleep(2 ** (attempt + 1))\n            got["calls"] += 1\n            got["cost"] += spent\n            ids = [r[0] for r in batch]\n            status = "ok" if rels is not None else "failed"\n            cur = store.execute("INSERT INTO kin_reads (source, entries, prompt_version, engine, status, relations, "\n                                "cost_usd, raw, error, note, at, mark) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",\n                                (src, json.dumps(ids), PROMPT_VERSION, engine, status, 0, spent, reply[:200000],\n                                 err or ("" if rels is not None else "the reply is not the JSON asked for"),\n                                 ("cut: %s" % ",".join(map(str, cut))) if cut else "", now(), MARK))\n            rid = cur.lastrowid\n            if rels is None:',
     '                if rels is not None:\n                    break\n                if not err and reply.strip():   # KIN_SALVAGE_2026_10_25: a reply cut short keeps its whole relations,\n                    sal = salvage(reply)        # and is not asked again (it would be cut again)\n                    if sal:\n                        rels, salvaged = sal, len(sal)\n                        break\n                if attempt < 2 and caller is None:\n                    time.sleep(2 ** (attempt + 1))\n            got["calls"] += 1\n            got["cost"] += spent\n            ids = [r[0] for r in batch]\n            status = ("salvaged" if salvaged else "ok") if rels is not None else "failed"\n            note = " ".join(x for x in (("cut: %s" % ",".join(map(str, cut))) if cut else "",\n                                        ("salvaged: %d relation objects of a reply cut short" % salvaged)\n                                        if salvaged else "") if x)\n            cur = store.execute("INSERT INTO kin_reads (source, entries, prompt_version, engine, status, relations, "\n                                "cost_usd, raw, error, note, at, mark) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",\n                                (src, json.dumps(ids), PROMPT_VERSION, engine, status, 0, spent, reply[:200000],\n                                 err or ("" if rels is not None else "the reply is not the JSON asked for"),\n                                 note, now(), MARK))\n            rid = cur.lastrowid\n            if rels is None:')

edit('scripts/kin_index.py', 8, '                    return got\n                continue\n            kept = 0\n            for d in rels:\n                c = clean_relation(d, len(batch))\n                if not c:\n                    continue\n                eid, head, body = batch[c["entry"] - 1]\n                text = entry_text(head, body)\n                store.execute("INSERT INTO kin (read_id, source, entry_id, head, subject, relation, object, words, "\n                              "refs, words_check, direction, at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",\n                              (rid, src, eid, head, c["subject"], c["relation"], c["object"], c["words"],\n                               json.dumps(c["refs"], ensure_ascii=False), words_check(c["words"], text),\n                               direction_check(c["relation"], c["words"]), now()))\n                kept += 1\n            for eid, head, body in batch:\n                store.execute("INSERT OR REPLACE INTO kin_done (entry_id, source, entry_sha, read_id, prompt_version, "\n                              "engine) VALUES (?,?,?,?,?,?)", (eid, src, entry_sha(head, body), rid, PROMPT_VERSION,\n                                                              engine))\n            store.execute("UPDATE kin_reads SET relations = ? WHERE id = ?", (kept, rid))\n            store.commit()\n            got["entries"] += len(batch)',
     '                    return got\n                continue\n            kept = keep(store, rid, src, batch, rels, engine)   # KIN_SALVAGE_2026_10_25: as --salvage keeps them\n            store.commit()\n            got["entries"] += len(batch)')

edit('scripts/kin_index.py', 9, '    ap.add_argument("--show", default="")\n    ap.add_argument("--no-write", action="store_true")\n    a = ap.parse_args(argv)\n    for stream in (sys.stdout, sys.stderr):',
     '    ap.add_argument("--show", default="")\n    ap.add_argument("--no-write", action="store_true")\n    ap.add_argument("--salvage", action="store_true",   # KIN_SALVAGE_2026_10_25\n                    help="free: the relations given whole in the stored replies that failed (a reply cut short)")\n    ap.add_argument("--retry-failed", action="store_true",\n                    help="ask again the entries whose reading failed %d times (KIN_SALVAGE_2026_10_25)" % GIVE_UP)\n    a = ap.parse_args(argv)\n    for stream in (sys.stdout, sys.stderr):')

edit('scripts/kin_index.py', 10, '        return show(a, open_store(a.kin_db), a.show)\n    engine = "gemini:%s" % a.model\n    store = open_store(a.kin_db) if (a.yes or a.check or Path(a.kin_db).exists()) else None\n    done = done_entries(store, engine) if store else {}\n    todo, planned = {}, 0.0\n    for src in sources:\n        rows = cands[src]\n        pick = rows if a.per_source <= 0 else rows[:a.per_source]\n        left = [r for r in pick if done.get(r[0]) != entry_sha(r[1], r[2])]\n        todo[src] = left\n        planned += estimate(left)\n        print("  %-44s %6d candidate entries; this run %d (%d read already); about $%.2f" % (\n            SHORT.get(src, src)[:44], len(rows), len(left), len(pick) - len(left), estimate(left)))\n    print("%s: %d entries to read, about $%.2f in all; %s" % (MARK, sum(len(v) for v in todo.values()), planned,\n                                                               budget_left(a.db, a.immutable)))',
     '        return show(a, open_store(a.kin_db), a.show)\n    engine = "gemini:%s" % a.model\n    store = open_store(a.kin_db) if (a.yes or a.check or a.salvage or Path(a.kin_db).exists()) else None\n    if store is not None and a.salvage:   # KIN_SALVAGE_2026_10_25: free, before the plan\n        sv = salvage_stored(store, engine, cands)\n        print("salvage: %d failed read(s) stored; %d salvaged: %d entries, %d relations kept (free)" % (\n            sv["reads"], sv["salvaged"], sv["entries"], sv["relations"]))\n    done = done_entries(store, engine) if store else {}\n    fails = failures(store, engine) if store else {}   # KIN_SALVAGE_2026_10_25\n    todo, planned, given_up = {}, 0.0, 0\n    for src in sources:\n        rows = cands[src]\n        pick = rows if a.per_source <= 0 else rows[:a.per_source]\n        left = [r for r in pick if done.get(r[0]) != entry_sha(r[1], r[2])]\n        gave = [r for r in left if fails.get(r[0], 0) >= GIVE_UP and not a.retry_failed]\n        if gave:   # KIN_SALVAGE_2026_10_25: not asked again by themselves\n            left = [r for r in left if r not in gave]\n            given_up += len(gave)\n        todo[src] = left\n        planned += estimate(left)\n        print("  %-44s %6d candidate entries; this run %d (%d read already); about $%.2f%s" % (\n            SHORT.get(src, src)[:44], len(rows), len(left), len(pick) - len(left) - len(gave), estimate(left),\n            ("; %d given up after %d failed reads" % (len(gave), GIVE_UP)) if gave else ""))\n    if given_up:\n        print("  %d entr%s given up: python scripts\\\\kin_index.py --salvage (free) keeps what their replies give; "\n              "--retry-failed asks again" % (given_up, "y" if given_up == 1 else "ies"))\n    print("%s: %d entries to read, about $%.2f in all; %s" % (MARK, sum(len(v) for v in todo.values()), planned,\n                                                               budget_left(a.db, a.immutable)))')


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
