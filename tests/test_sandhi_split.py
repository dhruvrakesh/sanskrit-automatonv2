import subprocess, json
def test_sandhi():
    p = subprocess.run(["python","scripts/sandhi_split.py","--json"], input="धर्मक्षेत्रे".encode("utf-8"), stdout=subprocess.PIPE)
    out = json.loads(p.stdout.decode("utf-8"))
    assert "splits" in out
