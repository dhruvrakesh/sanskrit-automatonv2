import subprocess, json, sys, os, pathlib

def run(cmd, text):
    p = subprocess.run(cmd, input=text.encode("utf-8"), stdout=subprocess.PIPE)
    return json.loads(p.stdout.decode("utf-8"))

def test_normalize_basic():
    out = run(["python","scripts/normalize_text.py","--json"], "रामः।")
    assert "normalized" in out
    assert "transliterated" in out
