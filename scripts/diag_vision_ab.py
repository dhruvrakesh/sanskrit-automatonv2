import json, re, os, sqlite3
DEV=re.compile(r"[ऀ-ॣ॰-ॿ]"); LAT=re.compile(r"[A-Za-z]")
def dv(s):
    d,l=len(DEV.findall(s or "")),len(LAT.findall(s or "")); t=d+l
    return d/t if t else 0.0
T=os.environ["TEMP"]
vis=json.loads(open(os.path.join(T,"aph50_vision.jsonl"),encoding="utf-8").readline())["text"]
c=sqlite3.connect("file:data/context.db?mode=ro",uri=True)
old=" ".join(r[0] or "" for r in c.execute("""SELECT p.text FROM passages p JOIN docs d ON d.id=p.doc_id
     WHERE d.code='AphorismsOfSandilya' AND p.page_no=50 ORDER BY p.idx"""))
c.close()
print("=== TESSERACT (stored) ===");    print(" ".join(old.split())[:400])
print("\n=== GEMINI VISION ===");        print(" ".join(vis.split())[:400])
print(f"\ndev: tesseract={dv(old):.2f}  vision={dv(vis):.2f}   len: {len(old)} vs {len(vis)}")
print("\nREAD BOTH ABOVE: is the vision text actually coherent Sanskrit?")
