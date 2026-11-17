#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_claude_key_fresh_2026_11_16.py  (2026-11-16)  CLAUDE_KEY_FRESH_2026_11_16   (the Claude key as .env holds it now)

Found on 16 Nov in data\\jobs.jsonl and usage_log: the 18 Sonnet jobs started from the dashboard on 15 Nov (16 small
smritis, shikshas and dhanur vedas, the Siddhanta Siromani's 640 passages, 40 of the Akasa Bhairava Kalpa) each
ended "Done. N/N translated | N quality-skipped" and "empty after a paid call" for every passage: each call was refused
("401 invalid x-api-key"). The dashboard was started on 13 Nov with the key that was later replaced, its jobs inherit
its environment, and python-dotenv does not replace a key already there. No call was billed (usage_log has no row for
them); 952 passages were left untranslated (13 of the 18 logs show the 401; the other 5 end before it). This patch changes:

  scripts/claude_engine.py   each Client reads ANTHROPIC_API_KEY from .env again and uses it when it differs from the
                             environment's (one line says so; the key is never printed; the tests read no .env); a
                             refused key is said once in the run's output, with the probe to run

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_keyfresh_<date> copies.

  python scripts\\patch_claude_key_fresh_2026_11_16.py --check
  python scripts\\patch_claude_key_fresh_2026_11_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'CLAUDE_KEY_FRESH_2026_11_16'
TAG = 'keyfresh'
FILES = ['scripts/claude_engine.py']
NEEDS = {'scripts/claude_engine.py': 'CLAUDE_ENGINE_2026_10_15'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/claude_engine.py', 1, '  - max_tokens counts the thinking too; the answer is streamed (no time limit on a long one).\nThe key: ANTHROPIC_API_KEY in .env, read by the SDK from the environment; it is never printed.\n\n  python scripts\\\\claude_engine.py --credit                         the credit: spent, left (free, read-only)',
     '  - max_tokens counts the thinking too; the answer is streamed (no time limit on a long one).\nThe key: ANTHROPIC_API_KEY in .env, read by the SDK from the environment; it is never printed.\nCLAUDE_KEY_FRESH_2026_11_16: and read from .env again by each Client, which uses it when it differs from the\nenvironment\'s. A run started by the dashboard carries the dashboard\'s environment, and python-dotenv does not replace\na key already there (override=False): from 14 to 16 Nov the dashboard, started on 13 Nov, gave its jobs the key that\nwas refused ("401 invalid x-api-key"), while a run from PowerShell had the new one. The 18 Sonnet jobs of 15 Nov\n(16 small texts, the Siddhanta Siromani\'s 640 passages, 40 of the Akasa Bhairava Kalpa: 952 passages) translated\nnothing for that reason; nothing was billed.\nA refused key is said once in the run\'s output ("[claude] the key was refused (401)"), with the probe to run.\n\n  python scripts\\\\claude_engine.py --credit                         the credit: spent, left (free, read-only)')

edit('scripts/claude_engine.py', 2, '\n# --------------------------------------------------------------------------------------------- the calls\nclass Client:\n    """One model, one effort. Built first: without the key or the SDK it raises, and nothing is called."""\n\n    def __init__(self, model: str, effort=None, timeout: float = TIMEOUT_S, sdk=None):\n        if not os.environ.get("ANTHROPIC_API_KEY"):\n            raise RuntimeError("ANTHROPIC_API_KEY is not set (.env)")\n        if sdk is None:',
     '\n# --------------------------------------------------------------------------------------------- the calls\ndef env_key(path=None):\n    """CLAUDE_KEY_FRESH_2026_11_16: ANTHROPIC_API_KEY as .env holds it now, or None (no .env, no python-dotenv, no\n    key there, or the tests: SA_NO_DOTENV=1). Never printed."""\n    if os.environ.get("SA_NO_DOTENV") == "1" and path is None:\n        return None\n    try:\n        from dotenv import dotenv_values\n    except Exception:\n        return None\n    try:\n        v = dotenv_values(str(path or Path(__file__).resolve().parents[1] / ".env")).get("ANTHROPIC_API_KEY")\n    except Exception:\n        return None\n    return (v or "").strip() or None\n\n\n_SAID_KEY = []\n_SAID_REFUSED = []\n\n\nclass Client:\n    """One model, one effort. Built first: without the key or the SDK it raises, and nothing is called."""\n\n    def __init__(self, model: str, effort=None, timeout: float = TIMEOUT_S, sdk=None):\n        key = env_key()   # CLAUDE_KEY_FRESH_2026_11_16\n        if not (key or os.environ.get("ANTHROPIC_API_KEY")):\n            raise RuntimeError("ANTHROPIC_API_KEY is not set (.env)")\n        if sdk is None:')

edit('scripts/claude_engine.py', 3, '            raise RuntimeError("effort %r is not one of %s" % (effort, ", ".join(EFFORTS)))\n        self.sdk, self.model, self.effort = sdk, model, effort\n        self.client = sdk.Anthropic(max_retries=MAX_RETRIES, timeout=timeout)   # the key from the environment\n\n    def request(self, system: str, user: str, max_tokens: int) -> dict:',
     '            raise RuntimeError("effort %r is not one of %s" % (effort, ", ".join(EFFORTS)))\n        self.sdk, self.model, self.effort = sdk, model, effort\n        kw = {"max_retries": MAX_RETRIES, "timeout": timeout}   # the key from the environment\n        if key and key != os.environ.get("ANTHROPIC_API_KEY"):   # CLAUDE_KEY_FRESH_2026_11_16: .env\'s, as it is now\n            kw["api_key"] = key\n            if not _SAID_KEY:\n                _SAID_KEY.append(1)\n                print("[claude] the key in .env is not the one this process was started with (the dashboard keeps the "\n                      "key it started with): .env\'s is used", flush=True)\n        self.client = sdk.Anthropic(**kw)\n\n    def request(self, system: str, user: str, max_tokens: int) -> dict:')

edit('scripts/claude_engine.py', 4, '    def create(self, system: str, user: str, max_tokens: int):\n        """The final message, streamed. Raises what the SDK raises once its own retries are spent."""\n        with self.client.messages.stream(**self.request(system, user, max_tokens)) as s:\n            return s.get_final_message()\n\n',
     '    def create(self, system: str, user: str, max_tokens: int):\n        """The final message, streamed. Raises what the SDK raises once its own retries are spent."""\n        try:\n            with self.client.messages.stream(**self.request(system, user, max_tokens)) as s:\n                return s.get_final_message()\n        except Exception as e:   # CLAUDE_KEY_FRESH_2026_11_16: a refused key said once, plainly\n            if refused(e) and not _SAID_REFUSED:\n                _SAID_REFUSED.append(1)\n                print("[claude] the key was refused (401 invalid x-api-key): nothing is billed for it; put the key in "\n                      ".env and check it with: python scripts\\\\claude_engine.py --probe", flush=True)\n            raise\n\n\ndef refused(e) -> bool:\n    """CLAUDE_KEY_FRESH_2026_11_16: the API refused the key (401, authentication_error, invalid x-api-key)."""\n    low = str(e).lower()\n    return any(k in low for k in ("invalid x-api-key", "authentication_error", "error code: 401"))\n\n')


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

