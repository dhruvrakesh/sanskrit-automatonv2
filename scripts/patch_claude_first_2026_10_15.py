#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_claude_first_2026_10_15.py  (2026-10-15)  CLAUDE_FIRST_2026_10_15

The Claude credit first, Gemini after it (Dhruv, 15 Oct): the free credit ($190 of it, to 11 Nov) pays for the
translation work, and Google's prepaid balance is kept for what only Gemini does. Follows RUN_FIX_2026_10_15.

scripts/scholar_translate.py:
  - the checks of a Claude run may be another Claude model's: --judge-engine anthropic:... (judge-v1, every verse)
    and --compare-engine anthropic:... (the second judge and the audit). Each check is metered on the Claude credit
    (usage_log, kind "judge" or "scholar"). The translator's own model may not check it (refused);
  - a run with no Gemini engine at all is gated by the Claude credit only: Google's spend cap is not consulted, and
    no Gemini key is needed;
  - a Gemini run may not have Claude checks (refused); the defaults (gemini-2.5-flash, gemini-2.5-pro) are as before;
  - the dry run says whose bill each check is; the NEXT line keeps --judge-engine and --compare-engine.

scripts/infer_mt.py:
  - the engine "anthropic:<model>[@effort]" (claude_engine.py): the working English and the Hindi by Claude, with the
    same system prompt and message as Gemini's. Every call is metered on the Claude credit (usage_log, kind
    "translation"; never budget_state); the credit is asked before each passage and fails closed (the run stops:
    BudgetBlocked). An answer cut off is asked once more with twice the room, else left empty (an honest gap), as the
    Gemini ladder ends; a refusal is empty. The default (MT_ENGINE, gemini-2.5-flash) is unchanged: nothing moves
    to Claude unless a job is given the engine.

Needs RUN_FIX_2026_10_15 (scholar_translate.py) and COST_TRUTH_2026_10_15 (infer_mt.py). Anchored, all-or-nothing,
marker-idempotent; keeps line endings; ASCII added only; py_compile before the atomic replace; backups
.bak_claudefirst_<date>.
  python scripts\\patch_claude_first_2026_10_15.py --check
  python scripts\\patch_claude_first_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "CLAUDE_FIRST_2026_10_15"
NEEDS = {"scripts/scholar_translate.py": "RUN_FIX_2026_10_15", "scripts/infer_mt.py": "COST_TRUTH_2026_10_15"}
FILES = list(NEEDS)

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"
MT = "scripts/infer_mt.py"

# ----------------------------------------------------------------------------------------- scholar_translate.py
edit(ST, 1, r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15
''', r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15, CLAUDE_FIRST_2026_10_15
''')

edit(ST, 2, r'''past its ingest (translating or exporting) does not stop a run.
''', r'''past its ingest (translating or exporting) does not stop a run.

CLAUDE_FIRST_2026_10_15: the checks of a Claude run may be another Claude model's (--judge-engine, --compare-engine
anthropic:...), on the Claude credit; never the translator's own model. A run with no Gemini engine is gated by the
Claude credit only (Google's spend cap is not consulted, no Gemini key is needed).
''')

edit(ST, 3, r'''        ga = argparse.Namespace(**vars(a))
        ga.engine = getattr(a, "compare_engine", None) or COMPARE_ENGINE
        self.gem = Gemini(ga, meta, con)
''', r'''        if claude_checks(a):   # CLAUDE_FIRST_2026_10_15: a check by another Claude model, on the credit
            self.gem = Checks(a, meta, con, sdk)
        else:
            ga = argparse.Namespace(**vars(a))
            ga.engine = getattr(a, "compare_engine", None) or COMPARE_ENGINE
            self.gem = Gemini(ga, meta, con)
''')

edit(ST, 4, r'''def keep_unparsed(a, meta: dict, kind: str, stop, txt, engine):
''', r'''def is_claude(engine) -> bool:
    """CLAUDE_FIRST_2026_10_15."""
    return str(engine or "").startswith("anthropic:")


def claude_checks(a) -> bool:
    """CLAUDE_FIRST_2026_10_15: a check of this run (the judge, or the second judge and the audit) is Claude's."""
    return is_claude(getattr(a, "judge_engine", None)) or is_claude(getattr(a, "compare_engine", None))


def no_gemini(a) -> bool:
    """CLAUDE_FIRST_2026_10_15: nothing in this run is Gemini's: Google's spend cap is not its gate."""
    return is_claude(a.engine) and is_claude(getattr(a, "judge_engine", None)) and is_claude(
        getattr(a, "compare_engine", None))


def own_model_check(a) -> str:
    """CLAUDE_FIRST_2026_10_15: the check engine that is the translator's own model ("" when none is). ValueError for
    an engine that cannot be read."""
    import claude_engine as ce
    mine = ce.parse_engine(a.engine)[0]
    for e in (getattr(a, "judge_engine", None), getattr(a, "compare_engine", None)):
        if is_claude(e) and ce.parse_engine(e)[0] == mine:
            return str(e)
    return ""


def bill_of(engine) -> str:
    """CLAUDE_FIRST_2026_10_15."""
    return "the Claude credit" if is_claude(engine) else "Google's bill, in the spend cap"


def checks_line(a) -> str:
    """CLAUDE_FIRST_2026_10_15: the dry run's line on the checks; as before when both are Gemini's."""
    j, c = getattr(a, "judge_engine", None) or JUDGE, getattr(a, "compare_engine", None) or COMPARE_ENGINE
    if not (is_claude(j) or is_claude(c)):
        return "the judge %s and the second judge %s: Google's bill, in the spend cap" % (j, c)
    s = "the judge %s (%s); the second judge and the audit %s (%s)" % (j, bill_of(j), c, bill_of(c))
    if no_gemini(a):
        s += "; no Gemini call: Google's spend cap is not consulted"
    return s


CLAUDE_JUDGE_MAX_TOKENS = 4000   # CLAUDE_FIRST_2026_10_15: judge-v1 answers one line; twice it when cut off


class ClaudeCheck:
    """CLAUDE_FIRST_2026_10_15: one check of a Claude run by another Claude model: ask() for the second judge and the
    audit (the critic's prompt), judge() for judge-v1 (judge_sample.py's prompt and reading). Each call is metered on
    the Claude credit (usage_log; kind "scholar" or "judge")."""

    def __init__(self, engine: str, meta: dict, con, sdk=None):
        import claude_engine as ce
        model, effort = ce.parse_engine(engine)
        self.ce, self.meta, self.engine = ce, meta, engine
        self.client = ce.Client(model, effort, sdk=sdk)
        self.a = argparse.Namespace(engine=engine)   # Claude.audit names the reader by a.engine
        self.spent, self.con, self.last, self._jcost = 0.0, con, None, 0.0

    def _once(self, system: str, msg: str, maxtok: int, kind: str):
        t0 = time.time()
        try:
            resp = self.client.create(system, msg, maxtok)
        except Exception as e:   # the SDK asked again already
            raise CallFailed("%s: %s" % (type(e).__name__, str(e)[:200]))
        txt = self.ce.text_of(resp)
        cost = self.ce.meter(self.con, kind, self.meta["doc"], self.client.model, getattr(resp, "usage", None),
                             time.time() - t0, bool(txt))
        self.spent += cost
        return txt, self.ce.stop_of(resp), cost

    def ask(self, kind: str, msg: str) -> tuple:
        system = system_for(kind, self.meta)
        txt, stop, cost = self._once(system, msg, CLAUDE_MAX_TOKENS, "scholar")
        d = parse_json(txt)
        if d is None and stop != "refusal":   # cut off, or not JSON: once more, with room
            txt, stop, more = self._once(system, msg, 2 * CLAUDE_MAX_TOKENS, "scholar")
            cost += more
            d = parse_json(txt)
        self.last = {"kind": kind, "finish": stop, "chars": len(txt or ""), "json": d is not None}
        return d, cost

    def judge(self, src: str, iast: str, english: str) -> tuple:
        """(fidelity, fluency, reason, $) by judge-v1, as Gemini.judge: None scores when it does not answer."""
        import judge_sample as js
        system, chk = js._SYS.format(lang_name="English"), self

        class _Model:
            def generate_content(self, prompt):
                txt, stop, cost = chk._once(system, prompt, CLAUDE_JUDGE_MAX_TOKENS, "judge")
                chk._jcost += cost
                if stop == "max_tokens" and not re.search(r'"fluency"\s*:\s*[1-5]', txt or ""):   # its scores not read
                    txt, stop, cost = chk._once(system, prompt, 2 * CLAUDE_JUDGE_MAX_TOKENS, "judge")
                    chk._jcost += cost
                return argparse.Namespace(text=txt, candidates=[argparse.Namespace(finish_reason=stop)])

        self._jcost = 0.0
        try:
            fid, flu, why = js._judge_one(_Model(), "English", src, iast, english)
        except Exception as e:
            return None, None, "[judge failed: %s]" % type(e).__name__, self._jcost
        return fid, flu, why, self._jcost


class Checks:
    """CLAUDE_FIRST_2026_10_15: a Claude run's checks when one of them is Claude's: the judge (--judge-engine) and the
    second judge and the audit (--compare-engine), each by Gemini or by another Claude model. As Gemini is to Claude:
    ask(), judge(), spent, con, a.engine."""

    def __init__(self, a, meta: dict, con, sdk=None):
        j = getattr(a, "judge_engine", None) or JUDGE
        c = getattr(a, "compare_engine", None) or COMPARE_ENGINE
        self.a = argparse.Namespace(engine=c, judge_engine=j)
        gem = None
        if not (is_claude(j) and is_claude(c)):
            ga = argparse.Namespace(**vars(a))
            ga.engine = COMPARE_ENGINE if is_claude(c) else c
            ga.judge_engine = JUDGE if is_claude(j) else j
            gem = Gemini(ga, meta, con)
        self.asker = ClaudeCheck(c, meta, con, sdk) if is_claude(c) else gem
        self.judger = ClaudeCheck(j, meta, con, sdk) if is_claude(j) else gem
        self._parts = [self.asker] + ([self.judger] if self.judger is not self.asker else [])
        self._con = con

    @property
    def spent(self) -> float:
        return sum(p.spent for p in self._parts)

    @property
    def con(self):
        return self._con

    @con.setter
    def con(self, v):
        self._con = v
        for p in getattr(self, "_parts", []):
            p.con = v

    @property
    def last(self):
        return getattr(self.asker, "last", None)

    def ask(self, kind: str, msg: str) -> tuple:
        return self.asker.ask(kind, msg)

    def judge(self, src: str, iast: str, english: str) -> tuple:
        return self.judger.judge(src, iast, english)


def keep_unparsed(a, meta: dict, kind: str, stop, txt, engine):
''')

edit(ST, 5, r'''        if str(a.compare_engine).startswith("anthropic:") or str(a.judge_engine).startswith("anthropic:"):
            print("REFUSE: the judges of a Claude English are Gemini's (--judge-engine, --compare-engine): it is not judged "
                  "by Claude"); print("VERDICT: nothing sent"); print("NEXT: "); return 1
''', r'''        try:   # CLAUDE_FIRST_2026_10_15: another Claude model may check it; its own may not
            own = own_model_check(a)
        except ValueError as e:
            print("REFUSE: --judge-engine / --compare-engine: %s" % e); print("VERDICT: nothing sent"); print("NEXT: ")
            return 1
        if own:
            print("REFUSE: %s is the translator's own model: a Claude English is checked by another model "
                  "(--judge-engine, --compare-engine)" % own); print("VERDICT: nothing sent"); print("NEXT: "); return 1
    elif claude_checks(a):   # CLAUDE_FIRST_2026_10_15
        print("REFUSE: Claude checks (--judge-engine, --compare-engine anthropic:...) are for a Claude run")
        print("VERDICT: nothing sent"); print("NEXT: "); return 1
''')

edit(ST, 6, r'''        print("  the judge %s and the second judge %s: Google's bill, in the spend cap" % (a.judge_engine, a.compare_engine))
''', r'''        print("  " + checks_line(a))   # CLAUDE_FIRST_2026_10_15
''')

edit(ST, 7, r'''                 + ((' --title "%s"' % a.title) if getattr(a, "title", None) else ""), cap))   # CLAUDE_ENGINE_2026_10_15
''', r'''                 + ((' --title "%s"' % a.title) if getattr(a, "title", None) else "")
                 + ((" --judge-engine %s" % a.judge_engine) if a.judge_engine != JUDGE else "")   # CLAUDE_FIRST_2026_10_15
                 + ((" --compare-engine %s" % a.compare_engine) if a.compare_engine != COMPARE_ENGINE else ""), cap))
''')

edit(ST, 8, r'''            budget_ok = CreditGate(asker.ce, budget_ok)
''', r'''            budget_ok = CreditGate(asker.ce, None if no_gemini(a) else budget_ok)   # CLAUDE_FIRST_2026_10_15
''')

# ----------------------------------------------------------------------------------------------- infer_mt.py
edit(MT, 1, r'''  echo                passthrough for testing
''', r'''  anthropic:<model>[@effort]  e.g. anthropic:claude-haiku-5-5 (CLAUDE_FIRST_2026_10_15: on the Claude credit)
  echo                passthrough for testing
''')

edit(MT, 2, r'''DEFAULT_ENGINE = os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
''', r'''DEFAULT_ENGINE = os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
# CLAUDE_FIRST_2026_10_15: "anthropic:<model>[@effort]" translates by Claude (scripts/claude_engine.py) on the Claude
# credit; the default stays Gemini's. A cut-off answer gets twice the room once.
ANTHROPIC_MAX_TOKENS = int(os.environ.get("MT_ANTHROPIC_MAX_TOKENS") or 8192)
ANTHROPIC_TIMEOUT = float(os.environ.get("MT_ANTHROPIC_TIMEOUT") or 300)
''')

edit(MT, 3, r'''        if _cost_tracker_ok:
            # Estimate cost of this batch before proceeding
''', r'''        if _cost_tracker_ok and not engine.startswith("anthropic:"):   # CLAUDE_FIRST_2026_10_15: the credit gates it
            # Estimate cost of this batch before proceeding
''')

edit(MT, 4, r'''        elif engine.startswith("echo"):
            generated = _echo_translate(missing_texts)
''', r'''        elif engine.startswith("anthropic:"):   # CLAUDE_FIRST_2026_10_15
            generated = _anthropic_translate(missing_texts, engine=engine, system_prompt=system_prompt,
                                             user_messages=missing_msgs, con=con, doc=doc_code)
        elif engine.startswith("echo"):
            generated = _echo_translate(missing_texts)
''')

edit(MT, 5, r'''        if _cost_tracker_ok and not engine.startswith("echo"):
''', r'''        if _cost_tracker_ok and not engine.startswith(("echo", "anthropic:")):   # CLAUDE_FIRST_2026_10_15: metered a call
''')

edit(MT, 6, r'''def _echo_translate(texts: List[str]) -> List[str]:
''', r'''class ClaudeUnavailable(QuotaExhausted):
    """CLAUDE_FIRST_2026_10_15: no key, no SDK, an engine that cannot be read, or the provider's own refusal to bill:
    the run stops at once with the reason."""
    pass


_ANTHROPIC = {}


def _anthropic_client(engine: str):
    """CLAUDE_FIRST_2026_10_15: (claude_engine, one Client per model and effort); ClaudeUnavailable without the key or
    the SDK."""
    try:
        import claude_engine as ce
        model, effort = ce.parse_engine(engine)
        if (model, effort) not in _ANTHROPIC:
            _ANTHROPIC[(model, effort)] = ce.Client(model, effort, timeout=ANTHROPIC_TIMEOUT)
        return ce, _ANTHROPIC[(model, effort)]
    except (ImportError, RuntimeError, ValueError) as e:
        raise ClaudeUnavailable("%s: %s" % (engine, e))


def _anthropic_once(ce, client, system: str, msg: str, maxtok: int, con, doc: str):
    t0 = time.time()
    resp = client.create(system, msg, maxtok)
    text = ce.text_of(resp)
    cost = ce.meter(con, "translation", doc, client.model, getattr(resp, "usage", None), time.time() - t0, bool(text), 1)
    return text, ce.stop_of(resp), cost


def _anthropic_translate(texts: List[str], *, engine: str, system_prompt: str, user_messages: List[str] = None,
                         con=None, doc: str = "") -> List[str]:
    """CLAUDE_FIRST_2026_10_15: each passage by Claude, as _gemini_translate does it: the system prompt and the
    passage's message; the answer's text is the translation. Every call is metered on the Claude credit (usage_log,
    kind "translation"; not budget_state). The credit is asked before each passage and fails closed: BudgetBlocked
    stops the run (translate with Gemini again). Cut off: asked once more with twice the room, else empty (an honest
    gap, as the Gemini ladder ends); a refusal: empty."""
    ce, client = _anthropic_client(engine)
    outs: List[str] = []
    msgs_to_use = user_messages or texts
    t_all, spent = time.time(), 0.0
    for i, t in enumerate(texts):
        if con is not None and not ce.budget_ok(con, 0.01):
            raise BudgetBlocked("the Claude credit is spent or expired (python scripts\\claude_engine.py --credit): "
                                "translate with a gemini: engine again")
        out = ""
        for attempt in range(RETRIES):
            try:
                text, stop, cost = _anthropic_once(ce, client, system_prompt, msgs_to_use[i].strip(),
                                                   ANTHROPIC_MAX_TOKENS, con, doc)
                spent += cost
                if stop == "max_tokens":
                    print(f"[claude] MAX_TOKENS p{i} ({len(text)} chars): asked again with twice the room")
                    text, stop, cost = _anthropic_once(ce, client, system_prompt, msgs_to_use[i].strip(),
                                                       2 * ANTHROPIC_MAX_TOKENS, con, doc)
                    spent += cost
                if stop == "max_tokens":
                    print(f"[claude] p{i} still cut off: left untranslated (an honest gap)")
                    text = ""
                elif stop == "refusal":
                    print(f"[claude] p{i}: a refusal: left untranslated")
                    text = ""
                elif not text:
                    print(f"[claude] No text (stop={stop}) p{i}: returning empty.")
                out = text
                break
            except Exception as exc:
                low = str(exc).lower()
                if "credit balance" in low or "billing" in low:
                    raise ClaudeUnavailable("the Anthropic account refuses to bill: %s" % str(exc)[:300])
                if attempt + 1 >= RETRIES:
                    if any(k in low for k in ("429", "rate limit", "rate_limit", "overloaded", "529")):
                        raise QuotaExhausted(f"Claude rate limit or overload persists after {RETRIES} attempts: {exc}")
                    print(f"[claude] FAILED after {RETRIES} attempts: {exc}")
                    break
                time.sleep(SLEEP * (2 ** attempt))
        outs.append(out)
        time.sleep(SLEEP)
    print(f"[COST] {len(texts)} passages | {time.time() - t_all:.1f}s | ${spent:.5f} | the Claude credit | "
          f"engine={engine}")
    return outs


def _echo_translate(texts: List[str]) -> List[str]:
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
    if not Path("scripts/scholar_translate.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, n, old, new in E:
        if not all(ord(c) < 128 for c in new):
            print("FAIL: edit %s %d is not ASCII" % (f, n)); return 2
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
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_claudefirst_" + stamp))
    for p, data in todo:
        t = p.with_name(p.name + ".tmp_claudefirst"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_claude_first_2026_10_15")
    return 0


if __name__ == "__main__":
    sys.exit(main())
