import json, os, subprocess, sys, time
W = os.path.expanduser(sys.argv[1]); out = os.path.expanduser(sys.argv[2]); budget = float(sys.argv[3])
done = {}
if os.path.exists(out):
    for l in open(out):
        r = json.loads(l); done[r["m"]] = r
mods = sorted(f[:-3] for f in os.listdir(os.path.join(W, "tests")) if f.startswith("test_") and f.endswith(".py"))
t0 = time.time()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
for m in mods:
    if m in done: continue
    if time.time() - t0 > budget: break
    s = time.time()
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "tests." + m], cwd=W, capture_output=True, text=True, timeout=150, env=env)
        tail = (p.stderr or "")[-3000:]; rc = p.returncode
    except subprocess.TimeoutExpired:
        tail, rc = "TIMEOUT", -9
    line = [x for x in tail.splitlines() if x.startswith(("OK", "FAILED", "Ran "))]
    with open(out, "a") as f:
        f.write(json.dumps({"m": m, "rc": rc, "s": round(time.time() - s, 1), "sum": " ".join(line), "tail": tail if rc else ""}) + "\n")
left = [m for m in mods if m not in done and m not in [json.loads(l)["m"] for l in open(out)]] if os.path.exists(out) else mods
print("modules", len(mods), "left", len(left))
