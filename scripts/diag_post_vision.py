import sqlite3, re, sys
# Post-vision-ingest verification. Read-only.
DOC = sys.argv[1] if len(sys.argv) > 1 else "AphorismsOfSandilya"
DEV = re.compile(r"[ऀ-ॣ॰-ॿ]"); LAT = re.compile(r"[A-Za-z]")
def dv(s):
    d, l = len(DEV.findall(s or "")), len(LAT.findall(s or "")); t = d + l
    return d / t if t else 0.0

c = sqlite3.connect("file:data/context.db?mode=ro", uri=True, timeout=30)
rows = c.execute("""SELECT p.id, p.page_no, p.idx, p.text, p.translation, p.text_type,
                           p.quality_score, p.translation_qa
                    FROM passages p JOIN docs d ON d.id=p.doc_id
                    WHERE d.code=? ORDER BY p.page_no, p.idx""", (DOC,)).fetchall()
print(f"=== {DOC}: {len(rows)} passages ===")

# 1. SOURCE QUALITY now (this is the headline: did vision OCR actually improve the corpus?)
san = [r for r in rows if dv(r[3]) >= 0.5]
eng = [r for r in rows if dv(r[3]) < 0.5 and len((r[3] or "").strip()) > 40]
print(f"\n1. Script split: {len(san)} Sanskrit-dominant, {len(eng)} Latin-dominant, "
      f"{len(rows)-len(san)-len(eng)} short/empty")
if san:
    print(f"   mean Devanagari fraction of Sanskrit rows: {sum(dv(r[3]) for r in san)/len(san):.3f}")

# 2. STALE ROWS - upsert never deletes (QUALITY_LOOP_DESIGN warns about this)
print("\n2. Stale-row check (pages whose passage count may exceed the new ingest):")
bypage = {}
for r in rows:
    bypage.setdefault(r[1], []).append(r)
suspicious = [(pg, len(v)) for pg, v in bypage.items() if len(v) > 12]
print(f"   pages with >12 passages (possible leftovers): {len(suspicious)}")
for pg, n in sorted(suspicious, key=lambda x: -x[1])[:10]:
    print(f"     page {pg}: {n} passages")

# 3. RUNAWAY pages - the model can loop and emit the same line repeatedly
print("\n3. Runaway/repetition check (very long passages):")
longs = sorted(rows, key=lambda r: -len(r[3] or ""))[:6]
for r in longs:
    t = " ".join((r[3] or "").split())
    # crude repetition signal: how much of the text is unique 40-char chunks
    chunks = [t[i:i+40] for i in range(0, len(t), 40)]
    uniq = len(set(chunks)) / max(1, len(chunks))
    flag = "  <-- REPETITION SUSPECTED" if uniq < 0.6 and len(t) > 3000 else ""
    print(f"   p{r[1]}.{r[2]}: {len(t)} chars  unique-chunks={uniq:.2f}{flag}")

# 4. TRANSLATION MISMATCH - translations made from the OLD garbled text
tr = [r for r in rows if (r[4] or "").strip()]
print(f"\n4. Existing translations: {len(tr)}")
print("   These were produced from the OLD Tesseract text. The Sanskrit beneath them has")
print("   now CHANGED, so they no longer correspond to their source and should be re-done.")
if tr:
    r = tr[0]
    print(f"\n   example p{r[1]}.{r[2]}:")
    print(f"     source now : {' '.join((r[3] or '').split())[:90]}")
    print(f"     translation: {' '.join((r[4] or '').split())[:90]}")

# 5. STALE TAGS - text_type/quality_score were computed from the OLD text
nf = sum(1 for r in rows if r[5] == 'frontmatter')
nn = sum(1 for r in rows if r[5] == 'noise')
print(f"\n5. Stale tags from the previous text: frontmatter={nf}  noise={nn}")
print("   Both classifiers must be re-run: the text they judged has been replaced.")
c.close()
