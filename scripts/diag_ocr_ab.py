import json, re, sys, sqlite3, os
DEV=re.compile(r"[ऀ-ॣ॰-ॿ]"); LAT=re.compile(r"[A-Za-z]")
def dv(s):
    d,l=len(DEV.findall(s or "")),len(LAT.findall(s or "")); t=d+l
    return d/t if t else 0.0
new=json.loads(open(os.path.join(os.environ["TEMP"],"aph50_new.jsonl"),encoding="utf-8").readline())
nt=new.get("text","")
c=sqlite3.connect("file:data/context.db?mode=ro",uri=True)
old=" ".join(r[0] or "" for r in c.execute("""SELECT p.text FROM passages p JOIN docs d ON d.id=p.doc_id
     WHERE d.code='AphorismsOfSandilya' AND p.page_no=50 ORDER BY p.idx"""))
c.close()
print(f"OLD  dev={dv(old):.2f}  len={len(old)}\n     {' '.join(old.split())[:110]}")
print(f"NEW  dev={dv(nt):.2f}  len={len(nt)}\n     {' '.join(nt.split())[:110]}")
print("\nVERDICT:", "BETTER - worth re-OCRing this doc" if dv(nt) > dv(old)+0.05 else "no material gain - do NOT re-OCR")
