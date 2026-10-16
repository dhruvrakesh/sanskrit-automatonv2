#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
gemini_thinking_probe.py  (2026-10-16)  THINKING_PROBE_2026_10_16

What gemini-2.5-flash's thinking costs, and what turning it off would change, measured on the judge (judge-v1) of a
text's scholarly English. Since COST_TRUTH_2026_10_15 counts the thinking, the ledger shows it is most of the Gemini
bill: on 15 Oct a judge call cost $0.00274 (1,053 output tokens for a one-line answer), a working-English call $0.00247
(808), an entities call $0.0128 (4,870). Gemini 2.5 Flash takes a thinking budget; 0 turns the thinking off.

For N verses of --engine's latest rows (chosen by hash, the same every time), the judge reads each twice, through the
Gemini REST API (generateContent): with its thinking as now, and with thinkingConfig.thinkingBudget = 0. It prints
the tokens and the cost of each way, and how far the scores agree. Every call is metered (usage_log, kind "probe")
and asks Google's spend cap first. It also says whether the installed google-generativeai SDK can set a thinking
budget (it decides how the change could be made). Nothing else is written; the scholarly rows are not touched.

A dry run by default (free): the plan and its price.
  python scripts\\gemini_thinking_probe.py --doc HAYASHIRSHA_PANCARATRA --n 12
  python scripts\\gemini_thinking_probe.py --doc HAYASHIRSHA_PANCARATRA --n 12 --yes
"""
from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, sys, time, types
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MARK = "THINKING_PROBE_2026_10_16"
API = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
PER_CALL = 0.0027   # a judge call with the thinking, 15 Oct


def sdk_can_budget() -> str:
    """Whether the installed google-generativeai can carry a thinking budget (no call is made)."""
    try:
        import google.generativeai as genai
    except Exception as e:
        return "google-generativeai cannot be imported (%s)" % type(e).__name__
    ver = getattr(genai, "__version__", "?")
    try:
        fields = genai.protos.GenerationConfig.meta.fields
        has = "thinking_config" in fields
    except Exception:
        has = False
    return ("google-generativeai %s: its GenerationConfig %s thinking_config" % (ver, "has" if has else "has no"))


def rest_call(model: str, system: str, prompt: str, budget, key: str, opener=None, timeout: float = 120.0):
    """One generateContent call; a response shaped as the SDK's (text, candidates, usage_metadata)."""
    import urllib.request
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2048}}
    if budget is not None:
        body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": int(budget)}
    req = urllib.request.Request(API % model, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    op = opener or urllib.request.build_opener()
    with op.open(req, timeout=timeout) as f:
        d = json.loads(f.read().decode("utf-8"))
    cand = (d.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    um = d.get("usageMetadata") or {}
    ns = types.SimpleNamespace
    return ns(text=text, candidates=[ns(finish_reason=cand.get("finishReason"))],
              usage_metadata=ns(prompt_token_count=um.get("promptTokenCount"),
                                candidates_token_count=um.get("candidatesTokenCount"),
                                thoughts_token_count=um.get("thoughtsTokenCount") or 0,
                                total_token_count=um.get("totalTokenCount")))


def sample(con, doc: str, engine: str, n: int) -> list:
    """n of engine's latest current rows of doc, chosen by the hash of the passage id: [(row, passage)]."""
    import scholar_translate as ST
    allp = ST.load_text(con, doc)
    byid = {x["id"]: x for x in allp}
    rows = [(r, byid[pid]) for pid, r in ST.latest_rows(con, doc, engine).items()
            if pid in byid and ST.current(r, byid[pid]) and (r.get("translation") or "").strip()]
    rows.sort(key=lambda t: hashlib.sha256(("probe:%s" % t[0]["passage_id"]).encode()).hexdigest())
    return rows[:max(0, n)]


def main(argv=None, opener=None) -> int:
    ap = argparse.ArgumentParser(description="What gemini-2.5-flash's thinking costs on the judge (a dry run unless --yes)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--engine", default="anthropic:claude-sonnet-5-5", help="whose scholarly rows are judged")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    try:
        from env_loader import load_env
        load_env()
    except Exception:
        pass
    if not Path(a.db).exists():
        print("REFUSE: %s not found (run from the repo root)" % a.db); print("VERDICT: nothing sent"); print("NEXT: ")
        return 2
    import judge_sample as js
    import db_utils
    con = sqlite3.connect(Path(a.db).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = sample(con, a.doc, a.engine, a.n)
    finally:
        con.close()
    print("gemini_thinking_probe.py  %s  %s   %s, judge-v1, with its thinking and with thinkingBudget 0"
          % (MARK, "RUN" if a.yes else "DRY RUN (nothing sent)", a.model))
    print("  %s: %d verse(s) of %s; %d call(s), about $%.3f (Google's bill, in the spend cap)"
          % (a.doc, len(rows), a.engine, 2 * len(rows), len(rows) * (PER_CALL + 0.0005)))
    print("  the SDK: %s" % sdk_can_budget())
    if not rows:
        print("VERDICT: no rows to judge"); print("NEXT: "); return 0
    if not a.yes:
        print("VERDICT: %d verse(s) to judge twice" % len(rows))
        print("NEXT: python scripts\\gemini_thinking_probe.py --doc %s --engine %s --n %d --yes" % (a.doc, a.engine, a.n))
        return 0
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("REFUSE: GEMINI_API_KEY is not set (.env)"); print("VERDICT: nothing sent"); print("NEXT: "); return 1
    import usage_meter
    system = js._SYS.format(lang_name="English")
    engine = "gemini:%s" % a.model
    con = db_utils.connect(a.db)
    res = {"on": [], "off": []}
    both = []   # (with, without) of each verse both answered
    try:
        for k, (r, x) in enumerate(rows, 1):
            if not usage_meter.budget_ok(con, 2 * PER_CALL):
                print("  STOPPED: the spend cap is reached (python scripts\\set_budget.py shows it)")
                break
            src, ia = (x.get("text") or "").strip(), (x.get("iast") or "")
            eng = ((r.get("group_translation") if r.get("group_ref") else None) or r.get("translation") or "").strip()
            got = {}
            for mode, budget in (("on", None), ("off", 0)):
                box = {}

                class _M:
                    def generate_content(self, prompt):
                        t0 = time.time()
                        resp = rest_call(a.model, system, prompt, budget, key, opener=opener)
                        box["resp"], box["dt"], box["prompt"] = resp, time.time() - t0, prompt
                        return resp
                try:
                    fid, flu, why = js._judge_one(_M(), "English", src, ia, eng)
                except Exception as e:
                    print("  (%d/%d) %s %s: no answer (%s)" % (k, len(rows), r.get("verse_ref"), mode, type(e).__name__))
                    continue
                resp = box["resp"]
                cost = usage_meter.meter(kind="probe", doc=a.doc, engine=engine, resp=resp,
                                         in_chars=len(system) + len(box["prompt"]), out_chars=len(resp.text or ""),
                                         units=1, duration_s=box["dt"], ok=fid is not None, con=con)
                um = resp.usage_metadata
                got[mode] = {"fid": fid, "flu": flu, "cost": cost or 0.0, "think": um.thoughts_token_count or 0,
                             "out": um.candidates_token_count or 0, "in": um.prompt_token_count or 0}
                res[mode].append(got[mode])
            on, off = got.get("on") or {}, got.get("off") or {}
            if on.get("fid") is not None and off.get("fid") is not None:
                both.append((on, off))
            print("  (%d/%d) %-12s with thinking %s/%s (%s thinking tokens, $%.5f); without %s/%s ($%.5f)"
                  % (k, len(rows), r.get("verse_ref"), on.get("fid"), on.get("flu"), on.get("think"), on.get("cost", 0),
                     off.get("fid"), off.get("flu"), off.get("cost", 0)))
    finally:
        con.close()
    pairs = both
    same = sum(1 for p, q in pairs if p["fid"] == q["fid"])
    near = sum(1 for p, q in pairs if abs(p["fid"] - q["fid"]) <= 1)
    gate = sum(1 for p, q in pairs if (p["fid"] >= 4 and p["flu"] >= 4) == (q["fid"] >= 4 and q["flu"] >= 4))
    c_on, c_off = sum(p["cost"] for p in res["on"]), sum(q["cost"] for q in res["off"])
    print("  with thinking: %d call(s), $%.4f, %.0f thinking tokens a call" % (len(res["on"]), c_on, sum(
        p["think"] for p in res["on"]) / max(1, len(res["on"]))))
    print("  without: %d call(s), $%.4f, %.0f thinking tokens a call" % (len(res["off"]), c_off, sum(
        q["think"] for q in res["off"]) / max(1, len(res["off"]))))
    print("VERDICT: without thinking the judge costs %s of what it costs with it; its fidelity is the same in %d of %d, "
          "within one in %d; pass or flag the same in %d" % (("%.0f%%" % (100.0 * c_off / c_on)) if c_on else "?", same,
                                                             len(pairs), near, gate))
    print("NEXT: a person decides (docs/TRIAGE_2026-10-16.md, section 5); nothing changes until then")
    return 0


if __name__ == "__main__":
    sys.exit(main())
