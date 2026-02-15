import subprocess, json
def test_morph():
    p = subprocess.run(["python","scripts/morph_parse.py","--json"], input="कुरुक्षेत्रे".encode("utf-8"), stdout=subprocess.PIPE)
    out = json.loads(p.stdout.decode("utf-8"))
    assert "engine" in out
