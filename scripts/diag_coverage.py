import sqlite3
c=sqlite3.connect("file:data/context.db?mode=ro",uri=True)
print(f"{"doc":42s} {"all":>6} {"verses":>7} {"front":>6} {"EN":>6} {"real %":>7}")
for code in ["AphorismsOfSandilya","LalitaVistara","HAYASHIRSHA_PANCARATRA","tantric_texts_series_edited_by_arthur_av","Bodhicaryavatara"]:
    a,v,f,en = c.execute("""SELECT COUNT(*),
      SUM(CASE WHEN COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') THEN 1 ELSE 0 END),
      SUM(CASE WHEN p.text_type='frontmatter' THEN 1 ELSE 0 END),
      SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') THEN 1 ELSE 0 END)
      FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=?""",(code,)).fetchone()
    print(f"{code[:42]:42s} {a:>6} {v:>7} {f:>6} {en:>6} {(100*en/v if v else 0):>6.1f}%")
c.close()
