# -*- coding: ascii -*-
"""TESTS_HERMETIC_2026_11_11: the tests run alike on every machine. `python -m unittest tests.<module>` (and
scripts\\run_tests.ps1) imports this first:

  SA_NO_DOTENV=1     no script reads this PC's .env during a test (env_loader, the dashboard, ingest_pdf, run_inbox,
                     corpus_sync's default files, publish_api, publish_srangam): not its keys, not its credit. Every
                     process a test starts inherits it.
  the API keys and the mirror's secret are taken out of the environment: a test that wants a key sets a fake one, so
                     no test can call a paid API with a real key.
  the Claude credit's settings are taken out, and SA_TEST_TODAY=2026-10-20 is the tests' day (claude_engine.credit):
                     the tests were written for the credit of 15 Oct to 11 Nov ($190), and on the PC with .env's
                     credit, or after its last day, a dozen of them failed (11 Nov: test_the_credit_stops_a_run_and_says_so,
                     the benchmarks' arms, the duel's tally).
"""
import os

os.environ["SA_NO_DOTENV"] = "1"
os.environ["SA_TEST_TODAY"] = "2026-10-20"
for _k in ("SA_CLAUDE_CREDIT_USD", "SA_CLAUDE_CREDIT_SINCE", "SA_CLAUDE_CREDIT_EXPIRES",
           "ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY2", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY",
           "CORPUS_SYNC_SECRET", "RESEND_API_KEY"):
    os.environ.pop(_k, None)
