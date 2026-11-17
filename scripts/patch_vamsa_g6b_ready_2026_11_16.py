#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_g6b_ready_2026_11_16.py  (2026-11-16)  VAMSA_G6B_READY_2026_11_16   (the genealogies' reader made ready for G6b)

Asked on 16 Nov, with the trial's report (the Harivamsa 9-10: 175 statements, 151 verified, $0.18; the Mahabharata
1.90: 181 statements, 173 verified, $0.16): "what next to put claude sonnet to work ... proceed with pending work".
Before the whole reading of G6 is bought (about $8), what the trial showed is mended. This patch changes:

  scripts/vamsa_read.py   the works of G6 read with a second prompt (vamsa-read-v2: son_of the father, born_of the
                          mother, begotten_by a begetter whose child the text counts as another man's: niyoga, a god,
                          a son before the marriage); G5a's three keep the first and are not read again; a reading made
                          with another prompt is kept beside the new one (.json.vamsa-read-v1). The checks: a name by
                          each of its words, an avagraha read as its a, a pronoun's person two verses back, a statement
                          whose words are in another verse takes that verse (108 statements of the stored readings
                          become verified with --reparse, 2 unsupported become words, none goes down). The lines: a
                          mother is never a father (Rathamtari > Duhsanta). --chapters that name nothing here is
                          refused; every NEXT carries --work; no "--chapters 1-2" for a work without them.
  tests/test_vamsa_g6a_2026_11_15.py   its stubbed reading expects the second prompt; its replay knows this came after.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_vamsag6b_<date> copies.

  python scripts\\patch_vamsa_g6b_ready_2026_11_16.py --check
  python scripts\\patch_vamsa_g6b_ready_2026_11_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_G6B_READY_2026_11_16'
TAG = 'vamsag6b'
FILES = ['scripts/vamsa_read.py', 'tests/test_vamsa_g6a_2026_11_15.py']
NEEDS = {'scripts/vamsa_read.py': 'VAMSA_G6A_2026_11_15', 'tests/test_vamsa_g6a_2026_11_15.py': 'VAMSA_G6A_2026_11_15'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_read.py', 1, '  python scripts\\\\vamsa_read.py --work hv --chapters 9 --show 12   the first 12 verses as they would be sent (free)\n  python scripts\\\\vamsa_read.py --work g6 --verses                 every chapter: its verses, the gaps in their numbers (free)\n"""\nfrom __future__ import annotations',
     '  python scripts\\\\vamsa_read.py --work hv --chapters 9 --show 12   the first 12 verses as they would be sent (free)\n  python scripts\\\\vamsa_read.py --work g6 --verses                 every chapter: its verses, the gaps in their numbers (free)\n\nVAMSA_G6B_READY_2026_11_16 (after the trial of 15 and 16 Nov: the Harivamsa 9-10, 175 statements, 151 verified, $0.18;\nthe Mahabharata 1.90, 181 statements, 173 verified, $0.16), before the whole reading (G6b) is bought:\n  - the works of G6 are read with a second prompt (vamsa-read-v2, SYSTEM_G6): son_of and daughter_of name the father,\n    born_of the mother, begotten_by a begetter whose child the text counts as another man\'s (niyoga, a god, a son born\n    before the marriage). The trial gave "Pandu son_of Dvaipayana" and "Arjuna son_of Kunti" only, so Arjuna\'s line\n    broke at Vyasa: what the verse says of the begetter and of the father it counts are now two statements. G5a\'s\n    three works keep vamsa-read-v1 and are not read again; the two trial chapters are read again (about $0.34), and\n    the first reading is kept beside the new one (09_1.json.vamsa-read-v1);\n  - a name is found in its verses by each of its words too (Manu Vaivasvata), an avagraha is read as the a it stands\n    for (\'mrtam: Amrta), and a pronoun\'s person in the two verses before (tasya ... in a later verse); a statement\n    whose words are in another verse of its part than the one it cites takes that verse (ref_cited keeps the other):\n    on the stored readings 108 statements become "verified" with --reparse (G5a 88, the trial 20) and 2 "unsupported"\n    become "words"; none goes the other way;\n  - a mother (a wife_of, daughter_of or sister_of whose words are in the verse, or a born_of) is never a father in a\n    line, even when her own statement is only "words"; nor is the parent of a son given two parents in one verse who\n    is not a son himself (the trial drew "Rathamtari > Duhsanta": now Puru\'s line runs 24 steps to Ajamidha);\n  - --chapters that name none of a work\'s chapters is refused with its chapters (it said "nothing to read: every\n    part asked for is read"); every NEXT carries --work; when all that was asked is read, NEXT is the work\'s plan, not\n    "--chapters 1-2" of a work that has no chapter 1.\n  python scripts\\\\vamsa_read.py --work all --reparse; python scripts\\\\vamsa_read.py --work g6 --reparse   (free)\n  python scripts\\\\vamsa_read.py --work mbh1 --chapters 90 --yes --max-usd 0.50                     (the trial again)\n"""\nfrom __future__ import annotations')

edit('scripts/vamsa_read.py', 2, 'import os\nimport re\nimport sys\nimport time',
     'import os\nimport re\nimport shutil\nimport sys\nimport time')

edit('scripts/vamsa_read.py', 3, 'HEAL = "VAMSA_HEAL_2026_11_11"\nG6A = "VAMSA_G6A_2026_11_15"\nPROMPT_VERSION = "vamsa-read-v1"\nROOT = Path(__file__).resolve().parents[1]',
     'HEAL = "VAMSA_HEAL_2026_11_11"\nG6A = "VAMSA_G6A_2026_11_15"\nG6B = "VAMSA_G6B_READY_2026_11_16"\nPROMPT_VERSION = "vamsa-read-v1"\nROOT = Path(__file__).resolve().parents[1]')

edit('scripts/vamsa_read.py', 4, '\n\nRELS = ("son_of", "daughter_of", "wife_of", "brother_of", "sister_of", "succeeded", "descendant_of", "line_of", "other")\nMODEL = "claude-sonnet-5-5"\nEFFORT = "medium"',
     '\n\nRELS = ("son_of", "daughter_of", "wife_of", "brother_of", "sister_of", "succeeded", "descendant_of", "line_of", "other",\n        "born_of", "begotten_by")   # VAMSA_G6B_READY_2026_11_16: the last two from vamsa-read-v2\nPROMPT_VERSION_G6 = "vamsa-read-v2"   # VAMSA_G6B_READY_2026_11_16: the works of G6\nREACH = 2   # VAMSA_G6B_READY_2026_11_16: a pronoun\'s person is looked for in this many verses before\nMODEL = "claude-sonnet-5-5"\nEFFORT = "medium"')

edit('scripts/vamsa_read.py', 5, 'Reply with JSON only, no prose: {"statements": [{"ref": "...", "a": "...", "rel": "...", "b": "...", "words": "...",\n"doubt": false}]}. If the verses give nothing, reply {"statements": []}."""\n\n',
     'Reply with JSON only, no prose: {"statements": [{"ref": "...", "a": "...", "rel": "...", "b": "...", "words": "...",\n"doubt": false}]}. If the verses give nothing, reply {"statements": []}."""\n\n\nSYSTEM_G6 = """You read Sanskrit genealogical passages (vamsanucarita) of a Purana, an epic (the Mahabharata, the Ramayana) or\nthe Harivamsa, given in IAST with each verse\'s reference.\nList every statement of kinship or succession that the text itself makes: who is whose son or daughter, of which\nmother a child was born, whose wife, whose brother or sister, who reigned after whom, who descends from whom, which\nline or clan is named after whom, and who begot a child that the text counts as another man\'s.\n\nRules:\n- Only what these verses say. No knowledge from other texts, no inference beyond the words, no persons the verses do\n  not name. A verse that only praises or narrates gives nothing.\n- One statement per relation. "a" is the rel of "b": {"a": "Vikuk\\u1e63i", "rel": "son_of", "b": "Ik\\u1e63v\\u0101ku"}.\n- rel is one of: son_of, daughter_of, born_of, begotten_by, wife_of, brother_of, sister_of, succeeded, descendant_of,\n  line_of, other.\n  son_of, daughter_of: b is the father, the man whose son or daughter the text counts a as. Never a mother.\n  born_of: b is the mother.\n  begotten_by: b begot a, but the text counts a as another man\'s child (niyoga on a widow or on the wife of a man\n  without sons, a god or a sage on a king\'s wife, a son born before his mother\'s marriage). Give both then: son_of (or\n  daughter_of) the man whose child the text counts a as, when these verses name him, and begotten_by the begetter.\n  succeeded: a reigned after b. line_of: a is a dynasty or clan (Y\\u0101davas, Haihayas) named after b.\n- Names in IAST, as the stem (Ik\\u1e63v\\u0101ku, not Ik\\u1e63v\\u0101ku\\u1e25 or Ik\\u1e63v\\u0101ko\\u1e25), with every diacritic as\n  in the text. Where the verse adds a name that tells two persons apart (Manu Vaivasvata), keep it.\n- "ref": the reference of the verse that says it, exactly as given in square brackets.\n- "words": the Sanskrit words of that verse that say it, copied exactly from the verse (a few words, not the verse).\n- "doubt": true when the text is ambiguous (two persons of one name, a pronoun whose person is unclear), else false.\n- Keep the order of the text. When a verse names several sons, give one statement for each.\n\nReply with JSON only, no prose: {"statements": [{"ref": "...", "a": "...", "rel": "...", "b": "...", "words": "...",\n"doubt": false}]}. If the verses give nothing, reply {"statements": []}."""\n\n\ndef prompt_of(work: str) -> tuple:\n    """VAMSA_G6B_READY_2026_11_16: (the prompt\'s version, its system prompt) for a work: G5a\'s three keep the first."""\n    return (PROMPT_VERSION, SYSTEM) if work in WORKS else (PROMPT_VERSION_G6, SYSTEM_G6)\n\n\ndef spans(nums) -> str:\n    """VAMSA_G6B_READY_2026_11_16: [2, 3, 9, 10, 15] -> "2-3, 9-10, 15"."""\n    out, run = [], []\n    for n in sorted(set(nums)):\n        if run and n == run[-1] + 1:\n            run.append(n)\n            continue\n        if run:\n            out.append("%d-%d" % (run[0], run[-1]) if len(run) > 1 else "%d" % run[0])\n        run = [n]\n    if run:\n        out.append("%d-%d" % (run[0], run[-1]) if len(run) > 1 else "%d" % run[0])\n    return ", ".join(out)\n\n\ndef work_arg(a) -> str:\n    """VAMSA_G6B_READY_2026_11_16: " --work hv" for a NEXT line (nothing for all, G5a\'s three)."""\n    return "" if getattr(a, "work", "all") == "all" else " --work %s" % a.work\n\n')

edit('scripts/vamsa_read.py', 6, '\n\ndef user_message(work: str, u: dict) -> str:\n    w = work_of(work)',
     '\n\ndef keep_before(out_dir, work: str, u: dict, version: str):\n    """VAMSA_G6B_READY_2026_11_16: a reading made with another prompt is kept beside the new one (09_1.json.vamsa-read-v1,\n    which records() does not read), so the two can be compared."""\n    p = out_path(out_dir, work, u)\n    try:\n        old = json.loads(p.read_text(encoding="utf-8")).get("prompt_version")\n    except (OSError, ValueError):\n        return None\n    if not old or old == version:\n        return None\n    keep = p.with_name(p.name + "." + str(old))\n    if not keep.exists():\n        shutil.copy2(p, keep)\n    return keep\n\n\ndef user_message(work: str, u: dict) -> str:\n    w = work_of(work)')

edit('scripts/vamsa_read.py', 7, '\n\ndef check(st: dict, refs: dict, order: list) -> str:\n    """verified, words, unsupported or bad (see the docstring). refs: {ref: text}; order: the refs in order."""',
     '\n\ndef name_keys(name: str, fold: bool = False) -> list:\n    """VAMSA_G6B_READY_2026_11_16: the keys a name is looked for by: the whole name\'s, and each of its words\' that\n    begins with a capital (Manu Vaivasvata: manuv, man, vaiva), so a name given with the word that tells two persons\n    apart is still found."""\n    f = folded if fold else (lambda x: x)\n    ks = [stem_key(f(name))] + [stem_key(f(t)) for t in str(name or "").split() if t[:1].isupper() and len(letters(t)) >= 3]\n    return [k for k in dict.fromkeys(ks) if k]\n\n\ndef name_span(text: str) -> str:\n    """VAMSA_G6B_READY_2026_11_16: the letters of the verses with an avagraha read as the a it stands for\n    (\'mrtam: amrtam), where a name is looked for."""\n    return letters(str(text or "").replace("\'", "a").replace(chr(0x2019), "a"))\n\n\ndef words_at(words: str, refs: dict, order: list, ref: str) -> bool:\n    """VAMSA_G6B_READY_2026_11_16: the words are in the verse ref, or in it and the next (as check() looks for them)."""\n    if ref not in refs:\n        return False\n    k = order.index(ref)\n    near = letters(refs[ref]) + "".join(letters(refs[r]) for r in order[k + 1:k + 2])\n    return words_in(words, near) or words_in(words, folded(near), fold=True)\n\n\ndef check(st: dict, refs: dict, order: list) -> str:\n    """verified, words, unsupported or bad (see the docstring). refs: {ref: text}; order: the refs in order."""')

edit('scripts/vamsa_read.py', 8, '    if not (words_in(words, near) or words_in(words, folded(near), fold=True)):\n        return "unsupported"\n    span = "".join(letters(refs[r]) for r in order[max(0, k - 1):k]) + near   # a pronoun\'s person: the verse before\n    if stem_key(a) in span and stem_key(b) in span:\n        return "verified"\n    fspan = folded(span)\n    if stem_key(folded(a)) in fspan and stem_key(folded(b)) in fspan:\n        return "verified"\n    return "words"',
     '    if not (words_in(words, near) or words_in(words, folded(near), fold=True)):\n        return "unsupported"\n    # a pronoun\'s person: the verses before (VAMSA_G6B_READY_2026_11_16: two, by its words and with the avagraha)\n    span = name_span(" ".join(refs[r] for r in order[max(0, k - REACH):k + 2]))\n    if all(any(x in span for x in name_keys(n)) for n in (a, b)):\n        return "verified"\n    fspan = folded(span)\n    if all(any(x in fspan for x in name_keys(n, fold=True)) for n in (a, b)):\n        return "verified"\n    return "words"')

edit('scripts/vamsa_read.py', 9, '            if got:\n                x["ref"], x["ref_from"] = got, "words"\n        x["doubt"] = bool(x.get("doubt"))\n        x["check"] = check(x, refs, order)',
     '            if got:\n                x["ref"], x["ref_from"] = got, "words"\n        elif x.get("words") and not words_at(str(x["words"]), refs, order, x["ref"]):\n            # VAMSA_G6B_READY_2026_11_16: the words are in another verse of the part (the trial: "Parikshit son_of\n            # Abhimanyu" cited 1.90.92, its words are in 1.90.90): the verse they are in, the one cited kept\n            got = ref_of(str(x["words"]), refs, order)\n            if got and got != x["ref"]:\n                x["ref_cited"], x["ref"], x["ref_from"] = x["ref"], got, "words"\n        x["doubt"] = bool(x.get("doubt"))\n        x["check"] = check(x, refs, order)')

edit('scripts/vamsa_read.py', 10, '    except (OSError, ValueError):\n        return False\n    return d.get("prompt_version") == PROMPT_VERSION and not d.get("error")\n\n',
     '    except (OSError, ValueError):\n        return False\n    return d.get("prompt_version") == prompt_of(work)[0] and not d.get("error")   # VAMSA_G6B_READY_2026_11_16\n\n')

edit('scripts/vamsa_read.py', 11, '    {key: {"name", "father", "up": key or None, "chapter", "ref", "words", "pos"}}"""\n    ver = [s for s in statements if s.get("check") == "verified"]\n    female = {letters(s.get("a")) for s in ver if s.get("rel") in ("wife_of", "daughter_of", "sister_of")}\n    sons = [s for s in ver if s.get("rel") == "son_of" and letters(s.get("b")) not in female\n            and letters(s.get("a")) and letters(s.get("b")) and letters(s.get("a")) != letters(s.get("b"))]',
     '    {key: {"name", "father", "up": key or None, "chapter", "ref", "words", "pos"}}"""\n    ver = [s for s in statements if s.get("check") == "verified"]\n    # VAMSA_G6B_READY_2026_11_16: a woman is known by any statement whose words are in its verse, and a born_of\'s b\n    said = [s for s in statements if s.get("check") in ("verified", "words")]\n    female = {letters(s.get("a")) for s in said if s.get("rel") in ("wife_of", "daughter_of", "sister_of")}\n    female |= {letters(s.get("b")) for s in said if s.get("rel") == "born_of"}\n    # VAMSA_G6B_READY_2026_11_16: a son given two parents in one verse (Duhsanta son_of Ilina, son_of Rathamtari): the\n    # one who is a son himself in these statements is the father, the other the mother (v1 asked for no born_of)\n    two = {}\n    for s in ver:\n        if s.get("rel") == "son_of" and letters(s.get("a")) and letters(s.get("b")):\n            two.setdefault((letters(s.get("a")), s.get("ref")), set()).add(letters(s.get("b")))\n    is_son = {letters(s.get("a")) for s in ver if s.get("rel") == "son_of"}\n    for bs in two.values():\n        dads = {b for b in bs if b in is_son}\n        if len(bs) > 1 and dads and dads != bs:\n            female |= bs - dads\n    sons = [s for s in ver if s.get("rel") == "son_of" and letters(s.get("b")) not in female\n            and letters(s.get("a")) and letters(s.get("b")) and letters(s.get("a")) != letters(s.get("b"))]')

edit('scripts/vamsa_read.py', 12, 'def plan_units(a) -> dict:\n    works = GROUPS.get(a.work) or [a.work]\n    texts, out = {}, {}\n    want = parse_chapters(a.chapters)\n    for wk in works:',
     'def plan_units(a) -> dict:\n    works = GROUPS.get(a.work) or [a.work]\n    texts, out, have = {}, {}, {}\n    want = parse_chapters(a.chapters)\n    for wk in works:')

edit('scripts/vamsa_read.py', 13, '        us = chunks(verses_of(wk, texts[m]))\n        out[wk] = [u for u in us if not want or u["chapter"] in want]\n    return out\n',
     '        us = chunks(verses_of(wk, texts[m]))\n        out[wk] = [u for u in us if not want or u["chapter"] in want]\n        have[wk] = sorted({u["chapter"] for u in us})\n    if want and not any(out.values()):   # VAMSA_G6B_READY_2026_11_16: it said "nothing to read: every part ... is read"\n        raise ValueError("chapters %s: none of them is here; the chapters: %s" % (\n            a.chapters, "; ".join("%s %s" % (wk, spans(c) or "none") for wk, c in have.items())))\n    return out\n')

edit('scripts/vamsa_read.py', 14, '            spec = "%d" % left[0] if len(left) == 1 else ("%d-%d" if left[1] == left[0] + 1 else "%d,%d") % tuple(left)\n            return "--work %s --chapters %s" % (wk, spec)\n    return "--work %s --chapters 1-2" % next(iter(units))\n\n',
     '            spec = "%d" % left[0] if len(left) == 1 else ("%d-%d" if left[1] == left[0] + 1 else "%d,%d") % tuple(left)\n            return "--work %s --chapters %s" % (wk, spec)\n    return None   # VAMSA_G6B_READY_2026_11_16: all that was asked is read (it named "--chapters 1-2", not there)\n\n')

edit('scripts/vamsa_read.py', 15, '        print("VERDICT: %d verses in %d work(s); %d chapter(s) with a gap or a number twice (free; nothing sent)"\n              % (n_all, len(units), odd))\n    print("NEXT: python scripts\\\\vamsa_read.py %s --yes   (a trial)" % trial_of(a, units))\n    return 0\n',
     '        print("VERDICT: %d verses in %d work(s); %d chapter(s) with a gap or a number twice (free; nothing sent)"\n              % (n_all, len(units), odd))\n    t = trial_of(a, units)\n    print("NEXT: python scripts\\\\vamsa_read.py %s --yes   (a trial)" % t if t else\n          "NEXT: python scripts\\\\vamsa_read.py%s   (all that was asked is read: the plan of the whole)" % work_arg(a))\n    return 0\n')

edit('scripts/vamsa_read.py', 16, '          "measures it), %s with %s" % (todo_n, todo_usd, total, "the Claude credit", a.model))\n    print("NEXT: python scripts\\\\vamsa_read.py %s --yes   (a trial)" % trial_of(a, units)\n          if todo_n else "NEXT: python scripts\\\\vamsa_read.py --report")\n    return 0\n',
     '          "measures it), %s with %s" % (todo_n, todo_usd, total, "the Claude credit", a.model))\n    print("NEXT: python scripts\\\\vamsa_read.py %s --yes   (a trial)" % trial_of(a, units)\n          if todo_n else "NEXT: python scripts\\\\vamsa_read.py%s --report" % work_arg(a))\n    return 0\n')

edit('scripts/vamsa_read.py', 17, '    need = sum(estimate(u["chars"], a.model) for _w, u in todo)\n    if not todo:\n        print("VERDICT: nothing to read: every part asked for is read"); print("NEXT: python scripts\\\\vamsa_read.py --report")\n        return 0\n    if need > a.max_usd * 1.5:',
     '    need = sum(estimate(u["chars"], a.model) for _w, u in todo)\n    if not todo:\n        print("VERDICT: nothing to read: every part asked for is read")\n        print("NEXT: python scripts\\\\vamsa_read.py%s --report" % work_arg(a))\n        return 0\n    if need > a.max_usd * 1.5:')

edit('scripts/vamsa_read.py', 18, '                break\n            t0 = time.time()\n            rec = {"mark": MARK, "work": wk, "title": work_of(wk)["title"], "chapter": u["chapter"], "part": u["part"],\n                   "refs": [r for r, _t in u["verses"]], "model": a.model, "effort": a.effort,\n                   "prompt_version": PROMPT_VERSION, "source": source_of(wk),\n                   "at": datetime.datetime.now().isoformat(timespec="seconds")}\n            try:\n                msg = client.create(SYSTEM, user_message(wk, u), MAX_TOKENS)\n            except Exception as e:\n                rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])',
     '                break\n            t0 = time.time()\n            version, system = prompt_of(wk)   # VAMSA_G6B_READY_2026_11_16\n            rec = {"mark": MARK, "work": wk, "title": work_of(wk)["title"], "chapter": u["chapter"], "part": u["part"],\n                   "refs": [r for r, _t in u["verses"]], "model": a.model, "effort": a.effort,\n                   "prompt_version": version, "source": source_of(wk),\n                   "at": datetime.datetime.now().isoformat(timespec="seconds")}\n            try:\n                msg = client.create(system, user_message(wk, u), MAX_TOKENS)\n            except Exception as e:\n                rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])')

edit('scripts/vamsa_read.py', 19, '                rec["error"] = "the reply was not read: %s%s" % (e, "; it was cut (max_tokens)" if rec["stop"] == "max_tokens"\n                                                                 else "")\n            store(a.out, wk, u, rec)\n            st = rec.get("statements") or []',
     '                rec["error"] = "the reply was not read: %s%s" % (e, "; it was cut (max_tokens)" if rec["stop"] == "max_tokens"\n                                                                 else "")\n            keep_before(a.out, wk, u, version)   # VAMSA_G6B_READY_2026_11_16\n            store(a.out, wk, u, rec)\n            st = rec.get("statements") or []')

edit('scripts/vamsa_read.py', 20, '        print("VERDICT: %d part(s) read, %d statements, %d verified (%s); $%.2f spent of the Claude credit"\n              % (n_ok, n_st, n_ver, "%d%%" % (100 * n_ver // n_st) if n_st else "-", spent))\n        print("NEXT: python scripts\\\\vamsa_read.py --report")\n        return 0\n    finally:',
     '        print("VERDICT: %d part(s) read, %d statements, %d verified (%s); $%.2f spent of the Claude credit"\n              % (n_ok, n_st, n_ver, "%d%%" % (100 * n_ver // n_st) if n_st else "-", spent))\n        print("NEXT: python scripts\\\\vamsa_read.py%s --report" % work_arg(a))\n        return 0\n    finally:')

edit('scripts/vamsa_read.py', 21, '            n += 1\n    print("VERDICT: %d stored repl(ies) parsed and checked again, %d not read (free)" % (n, bad))\n    print("NEXT: python scripts\\\\vamsa_read.py --report")\n    return 0\n',
     '            n += 1\n    print("VERDICT: %d stored repl(ies) parsed and checked again, %d not read (free)" % (n, bad))\n    print("NEXT: python scripts\\\\vamsa_read.py%s --report" % work_arg(a))\n    return 0\n')

edit('scripts/vamsa_read.py', 22, '        print("         wrote %s" % p)\n    print("VERDICT: %d statements in all; the verified ones are what G5b joins to the index\'s persons" % total)\n    print("NEXT: python scripts\\\\vamsa_read.py   (the plan: what is left to read)")\n    return 0\n',
     '        print("         wrote %s" % p)\n    print("VERDICT: %d statements in all; the verified ones are what G5b joins to the index\'s persons" % total)\n    print("NEXT: python scripts\\\\vamsa_read.py%s   (the plan: what is left to read)" % work_arg(a))\n    return 0\n')

edit('tests/test_vamsa_g6a_2026_11_15.py', 1, '        self.assertIn("Harivamsa (Vaidya\'s constituted text), chapter 9", sent)\n        self.assertIn("[HV 9.2] nari\\u1e63yantas", sent); self.assertNotIn("HV 10.1", sent)\n        self.assertEqual(sdk.requests[0]["system"], VR.SYSTEM, "the same prompt as G5a")\n        d = json.loads((Path(self.out) / "hv" / "09.json").read_text(encoding="utf-8"))\n        self.assertEqual([s["check"] for s in d["statements"]], ["verified", "words", "bad"])',
     '        self.assertIn("Harivamsa (Vaidya\'s constituted text), chapter 9", sent)\n        self.assertIn("[HV 9.2] nari\\u1e63yantas", sent); self.assertNotIn("HV 10.1", sent)\n        self.assertEqual(sdk.requests[0]["system"], getattr(VR, "SYSTEM_G6", VR.SYSTEM),\n                         "G5a\'s prompt; VAMSA_G6B_READY_2026_11_16: its second, for the works of G6")\n        d = json.loads((Path(self.out) / "hv" / "09.json").read_text(encoding="utf-8"))\n        self.assertEqual([s["check"] for s in d["statements"]], ["verified", "words", "bad"])')

edit('tests/test_vamsa_g6a_2026_11_15.py', 2, '            self.assertEqual(run().returncode, 0)\n            for rel in FILES:\n                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)\n            self.assertIn("Nothing to do", run().stdout)\n',
     '            self.assertEqual(run().returncode, 0)\n            for rel in FILES:\n                want = (REPO / rel).read_bytes()\n                later = sorted((REPO / rel).parent.glob(Path(rel).name + ".bak_vamsag6b_*"))   # VAMSA_G6B_READY came after\n                if later and b"VAMSA_G6B_READY_2026_11_16" in want:\n                    want = later[0].read_bytes()\n                self.assertEqual((t / rel).read_bytes(), want, rel)\n            self.assertIn("Nothing to do", run().stdout)\n')


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
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

