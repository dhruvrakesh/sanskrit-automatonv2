import sqlite3, sys
# "Sanskritic brain" integrity: are the embeddings, entity links and FTS index still
# pointing at passages that EXIST, and were they built from the CURRENT text?
# Critical after a wipe_doc + re-ingest, which deletes rows and creates new ids.
db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
q = lambda s: c.execute(s).fetchone()[0]
_EN_SQL = "SELECT COUNT(*) FROM passages WHERE TRIM(COALESCE(translation,'')) <> ''"

print("=== CORPUS ===")
print(f"  docs              : {q('SELECT COUNT(*) FROM docs')}")
print(f"  passages          : {q('SELECT COUNT(*) FROM passages')}")
print(f"  EN translated     : {q(_EN_SQL)}")

print("\n=== SEMANTIC INDEX (embeddings) ===")
if "passage_embeddings" in tabs:
    tot = q("SELECT COUNT(*) FROM passage_embeddings")
    orph = q("""SELECT COUNT(*) FROM passage_embeddings e
                LEFT JOIN passages p ON p.id = e.passage_id WHERE p.id IS NULL""")
    missing = q("""SELECT COUNT(*) FROM passages p
                   LEFT JOIN passage_embeddings e ON e.passage_id = p.id
                   WHERE e.passage_id IS NULL AND TRIM(COALESCE(p.text,''))<>''""")
    print(f"  vectors           : {tot}")
    print(f"  ORPHANED (point at deleted passages) : {orph}")
    print(f"  passages with NO vector              : {missing}")
    for code, n in c.execute("""SELECT d.code, COUNT(*) FROM passages p
            JOIN docs d ON d.id=p.doc_id
            LEFT JOIN passage_embeddings e ON e.passage_id=p.id
            WHERE e.passage_id IS NULL AND TRIM(COALESCE(p.text,''))<>''
            GROUP BY d.code ORDER BY COUNT(*) DESC LIMIT 8"""):
        print(f"      un-embedded: {code}: {n}")
else:
    print("  (no passage_embeddings table)")

print("\n=== ENTITY LAYER (cross-connections) ===")
if "entity_mentions" in tabs:
    tot = q("SELECT COUNT(*) FROM entity_mentions")
    orph = q("""SELECT COUNT(*) FROM entity_mentions m
                LEFT JOIN passages p ON p.id = m.passage_id WHERE p.id IS NULL""")
    print(f"  entities          : {q('SELECT COUNT(*) FROM entities')}")
    print(f"  mentions          : {tot}")
    print(f"  ORPHANED mentions (deleted passages)  : {orph}")
    for code, n in c.execute("""SELECT d.code, COUNT(*) FROM passages p
            JOIN docs d ON d.id=p.doc_id
            LEFT JOIN entity_mentions m ON m.passage_id=p.id
            WHERE m.passage_id IS NULL AND TRIM(COALESCE(p.translation,''))<>''
            GROUP BY d.code ORDER BY COUNT(*) DESC LIMIT 8"""):
        print(f"      un-linked (translated but no entities): {code}: {n}")
else:
    print("  (no entity_mentions table)")

print("\n=== FULL-TEXT SEARCH ===")
if "passages_fts" in tabs:
    try:
        fts = q("SELECT COUNT(*) FROM passages_fts")
        print(f"  fts rows          : {fts}   (passages: {q('SELECT COUNT(*) FROM passages')})")
        print("  -> if these differ materially, rebuild: db_utils.rebuild_fts")
    except Exception as e:
        print(f"  fts read error: {e}")
else:
    print("  (no passages_fts table)")

print("\nWhat this means: a wipe+re-ingest gives passages NEW ids. Vectors and entity")
print("mentions keyed to the OLD ids become orphans, and the new text has no vectors or")
print("entity links until build_embeddings.py and extract_entities.py are re-run.")
c.close()
