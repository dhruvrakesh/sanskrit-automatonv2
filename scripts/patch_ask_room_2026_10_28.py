#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ask_room_2026_10_28.py  ASK_ROOM_2026_10_28

The Professor's answers were cut. gemini-2.5-flash counts its thinking inside max_output_tokens: at 3,072 the
thinking took about 2,900 tokens and the answer was cut after about 130 (28 Oct: two answers of 545 and 423
characters, 3,068 tokens each in usage_log, kind ask_prof). scripts/dashboard.py:
  - the room: _ASK_ROOM, 16,384 for the Professor, 6,144 for the verses (a ceiling, not a cost: an answer is billed
    for the tokens it uses; at most about $0.04);
  - an answer cut at the limit says so (finish reason MAX_TOKENS), and the reply carries "cut";
  - a reply with no part (the limit reached inside the thinking) gives "(The model returned no text ...)", not an
    error for the whole question (_ask_text);
  - each of the scholars' claims is cited by its own work (claims.db's claim_works), and a work not in the public
    domain is marked as private reading (the Professor runs on this PC only).
Nothing else changes. Restart the dashboard when it is idle to load it.

  python scripts\\patch_ask_room_2026_10_28.py --check
  python scripts\\patch_ask_room_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ASK_ROOM_2026_10_28'
TAG = 'askroom'
FILES = ['scripts/dashboard.py']
NEEDS = {'scripts/dashboard.py': 'ASK_HOMONYM_2026_10_24'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, '                    "successor_of", "predecessor_of", "brother_of", "descendant_of", "ancestor_of", "married",\n                    "capital_of", "fought", "defeated", "dated_to")\n\n',
     '                    "successor_of", "predecessor_of", "brother_of", "descendant_of", "ancestor_of", "married",\n                    "capital_of", "fought", "defeated", "dated_to")\n# ASK_ROOM_2026_10_28: the room the model is given, its thinking included. gemini-2.5-flash counts its thinking inside\n# max_output_tokens: at 3,072 the Professor\'s thinking took about 2,900 tokens and its answer was cut after about 130\n# (28 Oct: two answers of 545 and 423 characters, 3,068 tokens each in usage_log). The room is a ceiling, not a cost:\n# an answer is billed for the tokens it uses (at most about $0.04 at 16,384).\n_ASK_ROOM = {"professor": 16384, "verses": 6144}\n\n\ndef _ask_text(resp) -> str:\n    """ASK_ROOM_2026_10_28: the answer\'s text; "" when the reply holds no part (the SDK\'s .text raises then, as when\n    the limit is reached inside the thinking), instead of an error for the whole question."""\n    try:\n        return (resp.text or "").strip()\n    except Exception:\n        try:\n            return "".join(getattr(p, "text", "") or "" for p in resp.candidates[0].content.parts).strip()\n        except Exception:\n            return ""\n\n\ndef _ask_cut(resp) -> bool:\n    """ASK_ROOM_2026_10_28: whether the model stopped at the length limit (finish reason MAX_TOKENS, 2)."""\n    try:\n        fr = resp.candidates[0].finish_reason\n    except Exception:\n        return False\n    name = getattr(fr, "name", None)\n    if isinstance(name, str):\n        return name == "MAX_TOKENS"\n    try:\n        return int(fr) == 2\n    except (TypeError, ValueError):\n        return str(fr).upper().endswith("MAX_TOKENS")\n\n')

edit('scripts/dashboard.py', 2, '            try:\n                rels = ",".join("\'%s\'" % r for r in _PROF_CLAIM_RELS)\n                for eid, canon in ids:\n                    for cid, printed, rel, claim, stance, hedge in c2.execute(\n                            "SELECT DISTINCT c.id, c.printed, c.relation, c.claim, c.stance, c.hedge FROM claim_links l "\n                            "JOIN claims c ON c.id = l.claim_id WHERE l.entity_id = ? AND c.read_id IN (SELECT MAX(id) "\n                            "FROM claim_reads WHERE status = \'ok\' GROUP BY work, pdf_page) ORDER BY CASE WHEN "',
     '            try:\n                rels = ",".join("\'%s\'" % r for r in _PROF_CLAIM_RELS)\n                works = {}   # ASK_ROOM_2026_10_28: each claim cited by its own work\n                if c2.execute("SELECT 1 FROM sqlite_master WHERE type=\'table\' AND name=\'claim_works\'").fetchone():\n                    _wc = {r[1] for r in c2.execute("PRAGMA table_info(claim_works)")}\n                    if {"code", "author", "title", "year", "licence"} <= _wc:\n                        for _c, _a, _t, _y, _l in c2.execute("SELECT code, author, title, year, licence FROM claim_works"):\n                            works[_c] = {"author": _a, "title": _t, "year": _y, "licence": _l}\n                for eid, canon in ids:\n                    for cid, printed, rel, claim, stance, hedge, work in c2.execute(\n                            "SELECT DISTINCT c.id, c.printed, c.relation, c.claim, c.stance, c.hedge, c.work FROM claim_links l "\n                            "JOIN claims c ON c.id = l.claim_id WHERE l.entity_id = ? AND c.read_id IN (SELECT MAX(id) "\n                            "FROM claim_reads WHERE status = \'ok\' GROUP BY work, pdf_page) ORDER BY CASE WHEN "')

edit('scripts/dashboard.py', 3, '                            continue\n                        seen.add(("c", cid))\n                        items.append({"kind": "claim", "about": canon,\n                                      "source": "Raychaudhuri, Political History of Ancient India (1923)",\n                                      "where": "p. %s" % (printed or "?"), "text": claim or "",\n                                      "note": ", ".join(x for x in (stance, hedge) if x)})\n                out["read"]["claims"] = True\n            finally:',
     '                            continue\n                        seen.add(("c", cid))\n                        # ASK_ROOM_2026_10_28: the claim\'s own work (claims.db\'s claim_works); a work not in the\n                        # public domain is marked as private reading (the Professor runs on this PC only, and\n                        # index_sync.py sends only the public-domain works to the site)\n                        _w = works.get(work) or {}\n                        _wn = ("Raychaudhuri, Political History of Ancient India (1923)" if work == "phai1923" else\n                               "%s, %s (%s)" % (_w.get("author") or "?", _w.get("title") or work, _w.get("year") or "?")\n                               if _w else str(work or "a scholar\'s work"))\n                        _wp = ("" if str(_w.get("licence") or "public domain").lower().startswith("public domain") else\n                               "in copyright: private reading on this PC, never on the site")\n                        items.append({"kind": "claim", "about": canon,\n                                      "source": _wn,\n                                      "where": "p. %s" % (printed or "?"), "text": claim or "",\n                                      "note": ", ".join(x for x in (stance, hedge, _wp) if x)})\n                out["read"]["claims"] = True\n            finally:')

edit('scripts/dashboard.py', 4, '        pass\n    # 2. LLM answer \u2014 self-contained Gemini config so the translation engine is untouched\n    try:\n        import google.generativeai as genai',
     '        pass\n    # 2. LLM answer \u2014 self-contained Gemini config so the translation engine is untouched\n    _cut = False   # ASK_ROOM_2026_10_28\n    try:\n        import google.generativeai as genai')

edit('scripts/dashboard.py', 5, '        kwargs = dict(model_name=model,\n                      generation_config=genai.GenerationConfig(temperature=0.2,\n                                                               max_output_tokens=(3072 if ask_mode == "professor"\n                                                                                  else 2048)),\n                      system_instruction=_sys)\n        if _ASK_SAFETY is not None:',
     '        kwargs = dict(model_name=model,\n                      generation_config=genai.GenerationConfig(temperature=0.2,\n                                                               max_output_tokens=_ASK_ROOM[ask_mode]),   # ASK_ROOM_2026_10_28\n                      system_instruction=_sys)\n        if _ASK_SAFETY is not None:')

edit('scripts/dashboard.py', 6, '            from usage_meter import meter as _meter\n            try:\n                _out = len(getattr(resp, "text", "") or "")\n            except Exception:\n                _out = 0',
     '            from usage_meter import meter as _meter\n            try:\n                _out = len(_ask_text(resp))   # ASK_ROOM_2026_10_28\n            except Exception:\n                _out = 0')

edit('scripts/dashboard.py', 7, '        except Exception:\n            pass\n        answer = (getattr(resp, "text", "") or "").strip() or \\\n                 "(The model returned no text \u2014 try rephrasing or a smaller k.)"\n    except Exception as e:\n        return jsonify({"error": f"LLM error: {e}", "sources": sources}), 500\n    return jsonify({"answer": answer, "sources": sources, "engine": engine,\n                    "k": k, "mode": mode, "editorial": len(extra),   # BRAIN_ITEMS_2026_10_07\n                    "ask_mode": ask_mode, "scholarly": scholarly})   # ASK_PROF_2026_10_23',
     '        except Exception:\n            pass\n        answer = _ask_text(resp) or \\\n                 "(The model returned no text \u2014 try rephrasing or a smaller k.)"   # ASK_ROOM_2026_10_28\n        _cut = _ask_cut(resp)\n        if _cut:\n            answer += ("\\n\\n[The answer was cut at the length limit (%d tokens, the model\'s thinking included). "\n                       "Ask a narrower question, or with fewer passages (k).]" % _ASK_ROOM[ask_mode])\n    except Exception as e:\n        return jsonify({"error": f"LLM error: {e}", "sources": sources}), 500\n    return jsonify({"answer": answer, "sources": sources, "engine": engine, "cut": _cut,   # ASK_ROOM_2026_10_28\n                    "k": k, "mode": mode, "editorial": len(extra),   # BRAIN_ITEMS_2026_10_07\n                    "ask_mode": ask_mode, "scholarly": scholarly})   # ASK_PROF_2026_10_23')


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

