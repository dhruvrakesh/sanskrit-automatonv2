import sqlite3, time, sys
db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)
q = lambda s, a=(): c.execute(s, a).fetchone()
print("journal_mode       =", q("PRAGMA journal_mode")[0])
print("page_size          =", q("PRAGMA page_size")[0])
print("wal_autocheckpoint =", q("PRAGMA wal_autocheckpoint")[0])
print("busy_timeout(new)  =", q("PRAGMA busy_timeout")[0], " <-- 0 == the Phase-1 gap every raw connect() has")
print()
t = time.time()
docs = q("SELECT COUNT(*) FROM docs")[0]
psg  = q("SELECT COUNT(*) FROM passages")[0]
en   = q("SELECT COUNT(*) FROM passages WHERE TRIM(COALESCE(translation,''))<>''")[0]
try:    hi = q("SELECT COUNT(*) FROM translations_l10n WHERE lang='hi' AND TRIM(COALESCE(translation,''))<>''")[0]
except Exception: hi = "n/a"
print(f"docs={docs}  passages={psg}  en={en}  hi={hi}   (counts in {time.time()-t:.2f}s)")
t = time.time()
rows = c.execute("SELECT d.code, COUNT(p.id) FROM docs d LEFT JOIN passages p ON p.doc_id=d.id GROUP BY d.code").fetchall()
print(f"per-doc coverage aggregate: {len(rows)} docs in {time.time()-t:.2f}s   <-- LOAD-TIME BASELINE")
for tbl in ("passage_embeddings","entities","entity_mentions"):
    try:    print(f"{tbl:20s}=", q(f"SELECT COUNT(*) FROM {tbl}")[0])
    except Exception: print(f"{tbl:20s}= n/a")
print("\nEN quality_score histogram:")
for lo in (0.0,0.2,0.4,0.6,0.8):
    n = q("SELECT COUNT(*) FROM passages WHERE translation<>'' AND quality_score>=? AND quality_score<?", (lo, lo+0.2))[0]
    print(f"  {lo:.1f}-{lo+0.2:.1f}: {n}")
low = q("SELECT COUNT(*) FROM passages WHERE translation<>'' AND COALESCE(quality_score,0)<0.4")[0]
print(f"  --> EN verses below 0.4 (heal candidates): {low}")
c.close()
