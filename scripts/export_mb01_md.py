# export_mb01_md.py
import sqlite3, html

DB = r"data/context.db"
DOC = "MBh-01"
OUT_MD = "MBh01_translation.md"

con = sqlite3.connect(DB)
cur = con.cursor()
rows = cur.execute("""
SELECT p.page_no, p.idx, p.text, p.translation
FROM passages p JOIN docs d ON d.id=p.doc_id
WHERE d.code=? AND (p.text IS NOT NULL OR p.translation IS NOT NULL)
ORDER BY p.page_no, p.idx
""", (DOC,))

def oneline(s: str) -> str:
    return (s or "").replace("\r","").replace("\n"," ").strip()

with open(OUT_MD, "w", encoding="utf-8-sig") as f:  # UTF-8 *with BOM* (helps old Windows viewers)
    f.write(
"""<!-- Devanagari + IAST friendly preview -->
<style>
body, .markdown-body { font-family:
  "Noto Serif", "Noto Serif Devanagari", "Mangal", "Nirmala UI",
  "Gentium Plus", "Charis SIL", "Segoe UI Historic", serif; line-height:1.6 }
[lang="sa-Deva"]{ font-family:"Noto Serif Devanagari","Mangal","Nirmala UI",serif }
[lang="sa-Latn"]{ font-family:"Gentium Plus","Charis SIL","Noto Serif",serif }
pre, code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace }
</style>

# Mahābhārata – Adi Parva (MBh-01)
*(Sanskrit in **Devanāgarī** + Roman/IAST)*

"""
    )
    for pg, idx, sa, en in rows:
        sa = oneline(sa)
        en = oneline(en)
        if not sa and not en: 
            continue
        f.write(f"### Page {pg}, Segment {idx}\n")
        if sa:
            f.write(f'<p lang="sa-Deva"><strong>Sanskrit:</strong> {sa}</p>\n')
        if en:
            f.write(f'<p lang="sa-Latn"><strong>English:</strong> {en}</p>\n')
        f.write("\n")

print(f"✅ Wrote {OUT_MD} (UTF-8 with BOM).")
