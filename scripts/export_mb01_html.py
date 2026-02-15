# export_mb01_html.py
import sqlite3, html
DB=r"data/context.db"; DOC="MBh-01"; OUT="MBh01_translation.html"
con=sqlite3.connect(DB); cur=con.cursor()
rows=cur.execute("""
SELECT p.page_no, p.idx, p.text, p.translation
FROM passages p JOIN docs d ON d.id=p.doc_id
WHERE d.code=? ORDER BY p.page_no,p.idx
""",(DOC,))
with open(OUT,"w",encoding="utf-8-sig") as f:
    f.write("""<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif&family=Noto+Serif+Devanagari&display=swap" rel="stylesheet">
<style>
body{margin:2rem auto; max-width:900px; padding:0 1rem;
font-family:"Noto Serif","Noto Serif Devanagari","Mangal","Nirmala UI",serif; line-height:1.7}
[lang="sa-Deva"]{ font-family:"Noto Serif Devanagari","Mangal","Nirmala UI",serif }
h1,h2,h3{ line-height:1.3 }
.card{ margin:1rem 0; padding:1rem; border:1px solid #ddd; border-radius:.5rem; background:#fff }
.label{ font-weight:600; color:#333 }
.san{ margin:.25rem 0 }
.en{ margin:.25rem 0 }
</style>
<title>Mahābhārata – Adi Parva (MBh-01)</title>
<h1>Mahābhārata – Adi Parva (MBh-01)</h1>
""")
    for pg,idx,sa,en in rows:
        sa=(sa or "").replace("\r","").strip()
        en=(en or "").replace("\r","").strip()
        if not sa and not en: continue
        f.write(f'<div class="card"><h3>Page {pg}, Segment {idx}</h3>')
        if sa: f.write(f'<div class="san" lang="sa-Deva"><span class="label">Sanskrit:</span> {html.escape(sa)}</div>')
        if en: f.write(f'<div class="en"  lang="sa-Latn"><span class="label">English:</span> {html.escape(en)}</div>')
        f.write('</div>\n')
print(f"✅ Wrote {OUT} (UTF-8 with BOM).")
