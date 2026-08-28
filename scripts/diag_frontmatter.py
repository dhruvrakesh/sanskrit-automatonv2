import sqlite3
c=sqlite3.connect("file:data/context.db?mode=ro",uri=True)
for code in ["LalitaVistara","AphorismsOfSandilya","HAYASHIRSHA_PANCARATRA","tantric_texts_series_edited_by_arthur_av","Bodhicaryavatara"]:
    print("\n== "+code+" ==")
    for (t,) in c.execute("""SELECT substr(TRIM(p.text),1,95) FROM passages p JOIN docs d ON d.id=p.doc_id
                             WHERE d.code=? AND p.text_type='frontmatter' ORDER BY p.page_no,p.idx LIMIT 5""",(code,)):
        print("  - "+t)
c.close()
