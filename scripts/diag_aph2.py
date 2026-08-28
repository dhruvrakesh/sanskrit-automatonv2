import sqlite3
c = sqlite3.connect("file:data/context.db?mode=ro", uri=True, timeout=30)
q = lambda s: c.execute(s).fetchone()[0]
DOC = "AphorismsOfSandilya"

print("READER sanity:")
print("  corpus EN non-empty     :", q("SELECT COUNT(*) FROM passages WHERE TRIM(COALESCE(translation,''))<>''"))
print("  Bodhicaryavatara EN     :", q("SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code='Bodhicaryavatara' AND TRIM(COALESCE(p.translation,''))<>''"))

print(f"\nWHERE are {DOC} translations?")
print("  passages.translation != '' :", q(f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code='{DOC}' AND TRIM(COALESCE(p.translation,''))<>''"))
try:
    print("  translations_l10n rows     :", q(f"SELECT COUNT(*) FROM translations_l10n x JOIN passages p ON p.id=x.passage_id JOIN docs d ON d.id=p.doc_id WHERE d.code='{DOC}'"))
    print("  translations_l10n non-empty:", q(f"SELECT COUNT(*) FROM translations_l10n x JOIN passages p ON p.id=x.passage_id JOIN docs d ON d.id=p.doc_id WHERE d.code='{DOC}' AND TRIM(COALESCE(x.translation,''))<>''"))
    for lang, n in c.execute(f"SELECT x.lang, COUNT(*) FROM translations_l10n x JOIN passages p ON p.id=x.passage_id JOIN docs d ON d.id=p.doc_id WHERE d.code='{DOC}' GROUP BY x.lang"):
        print(f"      l10n lang '{lang}': {n}")
except Exception as e:
    print("  translations_l10n: err", e)
try:
    print("  translation_history rows   :", q(f"SELECT COUNT(*) FROM translation_history x JOIN passages p ON p.id=x.passage_id JOIN docs d ON d.id=p.doc_id WHERE d.code='{DOC}'"))
except Exception as e:
    print("  translation_history: err", e)

print(f"\nSample {DOC} page 48-50 (passages.translation and any l10n):")
for pid, rid, pg, idx, qa, tr in c.execute(f"""SELECT p.id, p.rowid, p.page_no, p.idx, p.translation_qa,
                              substr(COALESCE(NULLIF(TRIM(p.translation),''),'(blank)'),1,42)
                       FROM passages p JOIN docs d ON d.id=p.doc_id
                       WHERE d.code='{DOC}' AND p.page_no IN (48,49,50)
                       ORDER BY p.page_no, p.idx LIMIT 12"""):
    try:
        l10 = c.execute("SELECT lang, substr(COALESCE(NULLIF(TRIM(translation),''),'(blank)'),1,30) FROM translations_l10n WHERE passage_id=?", (pid,)).fetchall()
    except Exception:
        l10 = []
    print(f"  id={pid} p{pg}.{idx} en_qa={qa} en={tr!r}  l10n={l10}")
c.close()
