import glob, json, os

def tot_chars(p):
    c = 0
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            try:
                c += len(json.loads(line).get("text",""))
            except Exception:
                pass
    return c

pairs=[]
for p in sorted(glob.glob(r"data/raw/panchatantra_*.jsonl")):
    pairs.append((tot_chars(p), os.path.basename(p)))

pairs.sort()
for c,name in pairs:
    if c < 300:
        print(f"LOW {c:>5} {name}")
