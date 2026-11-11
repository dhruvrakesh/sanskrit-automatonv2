#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_tests_hermetic_2026_11_11.py  (2026-11-11)  TESTS_HERMETIC_2026_11_11

On 11 Nov run_tests.ps1 on the PC failed in test_claude_engine_2026_10_15 (test_the_credit_stops_a_run_and_says_so:
"the API (or the key) is not answering", then WinError 32 on its temp database). The tests read this PC's .env: its
keys and its Claude credit ($200 from 9 Nov) through env_loader and the dashboard, so a test written for the credit of
15 Oct ($190, until 11 Nov) saw another one; and without .env (a copy elsewhere) ten modules failed from 11 Nov, the
default credit's last day. A test that reads the PC's keys can also call a paid API with a real one.

This patch (with tests\\__init__.py, new, beside it):
  scripts/env_loader.py, dashboard.py (_load_env, _credit_env_fresh), ingest_pdf.py, run_inbox.py, publish_api.py,
  publish_srangam.py    leave .env alone when SA_NO_DOTENV=1
  scripts/corpus_sync.py         load_config reads only the files it is given when SA_NO_DOTENV=1
  scripts/claude_engine.py       test_today(): the tests' day (SA_TEST_TODAY) for the credit; the clock otherwise
  tests/test_desk_fresh_2026_11_11.py   its credit test reads its own .env with SA_NO_DOTENV taken out
tests\\__init__.py sets SA_NO_DOTENV=1 and SA_TEST_TODAY=2026-10-20 and takes the keys and the credit's settings out of
the environment of every test (and of every process a test starts). Nothing changes outside the tests: neither is
ever set by the dashboard, the scripts or .env.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_testsherm_<date> copies.

  python scripts\\patch_tests_hermetic_2026_11_11.py --check
  python scripts\\patch_tests_hermetic_2026_11_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'TESTS_HERMETIC_2026_11_11'
TAG = 'testsherm'
FILES = ['scripts/env_loader.py', 'scripts/ingest_pdf.py', 'scripts/run_inbox.py', 'scripts/corpus_sync.py', 'scripts/publish_api.py', 'scripts/publish_srangam.py', 'scripts/dashboard.py', 'scripts/claude_engine.py', 'tests/test_desk_fresh_2026_11_11.py']
NEEDS = {'scripts/dashboard.py': 'DESK_FRESH_2026_11_11', 'scripts/claude_engine.py': 'DESK_FRESH_2026_11_11', 'tests/test_desk_fresh_2026_11_11.py': 'DESK_FRESH_2026_11_11'}
REQUIRES = {'tests/__init__.py': 'TESTS_HERMETIC_2026_11_11'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/env_loader.py', 1, "\ndef _load_dotenv():\n    # Import lazily to avoid new hard deps if you don't want them\n    try:",
     '\ndef _load_dotenv():\n    # TESTS_HERMETIC_2026_11_11: the tests (tests/__init__.py) set SA_NO_DOTENV=1: they never read this PC\'s .env (its\n    # keys, its credit), so they run alike on every machine and never call a paid API with a real key\n    if os.environ.get("SA_NO_DOTENV") == "1":\n        return\n    # Import lazily to avoid new hard deps if you don\'t want them\n    try:')

edit('scripts/ingest_pdf.py', 1, '\ndef _load_dotenv_from_repo_root():\n    if os.environ.get("OPENAI_API_KEY"):\n        return\n    env_path = Path(__file__).resolve().parents[1] / ".env"',
     '\ndef _load_dotenv_from_repo_root():\n    if os.environ.get("OPENAI_API_KEY") or os.environ.get("SA_NO_DOTENV") == "1":   # TESTS_HERMETIC_2026_11_11\n        return\n    env_path = Path(__file__).resolve().parents[1] / ".env"')

edit('scripts/run_inbox.py', 1, 'def _load_dotenv_from_repo_root():\n    if os.environ.get("OPENAI_API_KEY"):  # already set (e.g., CI or shell)\n        return\n    env_path = Path(__file__).resolve().parents[1] / ".env"',
     'def _load_dotenv_from_repo_root():\n    if os.environ.get("OPENAI_API_KEY"):  # already set (e.g., CI or shell)\n        return\n    if os.environ.get("SA_NO_DOTENV") == "1":   # TESTS_HERMETIC_2026_11_11: the tests never read this PC\'s .env\n        return\n    env_path = Path(__file__).resolve().parents[1] / ".env"')

edit('scripts/corpus_sync.py', 1, '    except Exception:\n        pass\n    local = _read_env_file(env_path or (ROOT / ".env"))\n    get = lambda k: os.environ.get(k) or local.get(k) or ""\n    site = _read_env_file(site_env_path or get("CORPUS_SITE_ENV") or DEFAULT_SITE_ENV)\n    return {\n        "secret": get("CORPUS_SYNC_SECRET"),',
     '    except Exception:\n        pass\n    quiet = os.environ.get("SA_NO_DOTENV") == "1"   # TESTS_HERMETIC_2026_11_11: the tests read only the files they name\n    local = _read_env_file(env_path or (ROOT / ".env")) if (env_path or not quiet) else {}\n    get = lambda k: os.environ.get(k) or local.get(k) or ""\n    site_path = site_env_path or get("CORPUS_SITE_ENV") or ("" if quiet else DEFAULT_SITE_ENV)\n    site = _read_env_file(site_path) if site_path else {}\n    return {\n        "secret": get("CORPUS_SYNC_SECRET"),')

edit('scripts/publish_api.py', 1, '# load .env after APP_DIR is defined\ntry:\n    from dotenv import load_dotenv\n    load_dotenv(str(APP_DIR / ".env"))\nexcept Exception:\n    pass',
     '# load .env after APP_DIR is defined\ntry:\n    if os.environ.get("SA_NO_DOTENV") != "1":   # TESTS_HERMETIC_2026_11_11: the tests never read this PC\'s .env\n        from dotenv import load_dotenv\n        load_dotenv(str(APP_DIR / ".env"))\nexcept Exception:\n    pass')

edit('scripts/publish_srangam.py', 1, 'except Exception:\n    try:\n        from dotenv import load_dotenv\n        load_dotenv()\n    except Exception:\n        pass',
     'except Exception:\n    try:\n        if os.environ.get("SA_NO_DOTENV") != "1":   # TESTS_HERMETIC_2026_11_11: the tests never read this PC\'s .env\n            from dotenv import load_dotenv\n            load_dotenv()\n    except Exception:\n        pass')

edit('scripts/dashboard.py', 1, 'def _load_env():\n    env_path = ROOT / ".env"\n    if not env_path.exists():\n        return\n    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():',
     'def _load_env():\n    env_path = ROOT / ".env"\n    if not env_path.exists() or os.environ.get("SA_NO_DOTENV") == "1":   # TESTS_HERMETIC_2026_11_11: not under the tests\n        return\n    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():')

edit('scripts/dashboard.py', 2, '    """DESK_FRESH_2026_11_11: the credit\'s settings as .env has them now (claude_engine.dotenv_credit: those three keys\n    only), when .env changed since last read; never raises."""\n    try:\n        p = ROOT / ".env"',
     '    """DESK_FRESH_2026_11_11: the credit\'s settings as .env has them now (claude_engine.dotenv_credit: those three keys\n    only), when .env changed since last read; never raises."""\n    if os.environ.get("SA_NO_DOTENV") == "1":   # TESTS_HERMETIC_2026_11_11: the tests never read this PC\'s .env\n        return\n    try:\n        p = ROOT / ".env"')

edit('scripts/claude_engine.py', 1, '\n\ndef dotenv_credit(path) -> dict:\n    """DESK_FRESH_2026_11_11: the credit\'s three settings as the .env file at path has them now ({} when it has none);',
     '\n\ndef test_today():\n    """TESTS_HERMETIC_2026_11_11: the tests\' own day (SA_TEST_TODAY, set by tests/__init__.py only), so that a test\n    written in the credit\'s month still runs after it; None otherwise (the clock). Never put it in .env."""\n    v = (os.environ.get("SA_TEST_TODAY") or "").strip()\n    try:\n        return datetime.date.fromisoformat(v) if v else None\n    except ValueError:\n        return None\n\n\ndef dotenv_credit(path) -> dict:\n    """DESK_FRESH_2026_11_11: the credit\'s three settings as the .env file at path has them now ({} when it has none);')

edit('scripts/claude_engine.py', 2, '    except sqlite3.Error as e:\n        raise RuntimeError("the credit cannot be read (%s)" % e)\n    day = (today or datetime.date.today()).isoformat()\n    return dict(s, spent=float(spent or 0.0), calls=int(calls or 0), left=s["cap"] - float(spent or 0.0),\n                expired=day >= s["expires"])',
     '    except sqlite3.Error as e:\n        raise RuntimeError("the credit cannot be read (%s)" % e)\n    day = (today or test_today() or datetime.date.today()).isoformat()\n    return dict(s, spent=float(spent or 0.0), calls=int(calls or 0), left=s["cap"] - float(spent or 0.0),\n                expired=day >= s["expires"])')

edit('tests/test_desk_fresh_2026_11_11.py', 1, '    def test_the_credit_as_env_has_it_now(self):\n        d = self.d\n        saved_env = {k: os.environ.get(k) for k in KEYS}\n        saved = (d.ROOT, set(d._CREDIT_SHELL), dict(d._CREDIT_ENV_SEEN))\n        try:\n            root = self.td / "root"\n            root.mkdir()',
     '    def test_the_credit_as_env_has_it_now(self):\n        d = self.d\n        saved_env = {k: os.environ.get(k) for k in KEYS + ("SA_NO_DOTENV",)}   # TESTS_HERMETIC_2026_11_11\n        saved = (d.ROOT, set(d._CREDIT_SHELL), dict(d._CREDIT_ENV_SEEN))\n        try:\n            os.environ.pop("SA_NO_DOTENV", None)   # this test reads its own .env (in a temp folder)\n            root = self.td / "root"\n            root.mkdir()')


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

