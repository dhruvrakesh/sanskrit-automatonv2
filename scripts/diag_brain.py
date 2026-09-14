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

# BRAIN_CONNECTIVITY_2026_09_14
# Integrity is "do the links point at rows that exist". Connectivity is "do
# they go ACROSS documents". A corpus can be perfectly intact and still be a
# shelf. This section answers the second question.
print("\n=== CONNECTIVITY (is this one brain, or a shelf?) ===")


def _cols(t):
    try:
        return [r[1] for r in c.execute("PRAGMA table_info(%s)" % t)]
    except Exception:
        return []


_ec, _mc = _cols("entities"), _cols("entity_mentions")
_eid = next((x for x in ("entity_id", "entity", "eid") if x in _mc), None)
_pid = next((x for x in ("passage_id", "passage", "pid") if x in _mc), None)
_lab = next((x for x in ("canonical", "name", "surface", "text", "label", "iast")
             if x in _ec), "id")
if not (_ec and _mc and _eid and _pid):
    print("  (entity tables absent or their join columns are not recognisable)")
else:
    print("  joining entity_mentions.%s -> entities.id, .%s -> passages.id"
          % (_eid, _pid))
    _base = ("SELECT m.%s AS e, COUNT(DISTINCT p.doc_id) AS nd "
             "FROM entity_mentions m JOIN passages p ON p.id = m.%s "
             "GROUP BY m.%s" % (_eid, _pid, _eid))
    _hist = c.execute("SELECT nd, COUNT(*) FROM (%s) GROUP BY nd ORDER BY nd"
                      % _base).fetchall()
    _tot = sum(n for _d, n in _hist)
    if not _tot:
        print("  no linked entities")
    else:
        _multi = sum(n for d, n in _hist if d > 1)
        _five = sum(n for d, n in _hist if d >= 5)
        print("    linked entities             %7d" % _tot)
        print("    in 2 or more documents      %7d   %5.1f%%"
              % (_multi, 100.0 * _multi / _tot))
        print("    in 5 or more documents      %7d   %5.1f%%"
              % (_five, 100.0 * _five / _tot))
        print("    documents per entity:")
        _mx = max(n for _d, n in _hist)
        for _d, _n in _hist[:10]:
            print("      %3d doc(s) %7d  %s" % (_d, _n, "#" * min(50, int(50.0 * _n / _mx))))
        if len(_hist) > 10:
            print("      ... up to %d document(s)" % _hist[-1][0])
        try:
            _top = c.execute(
                "SELECT e.%s, COUNT(DISTINCT p.doc_id) nd, COUNT(*) nm "
                "FROM entities e JOIN entity_mentions m ON m.%s = e.id "
                "JOIN passages p ON p.id = m.%s GROUP BY e.id "
                "HAVING nd > 1 ORDER BY nd DESC, nm DESC LIMIT 10"
                % (_lab, _eid, _pid)).fetchall()
            if _top:
                print("    the strongest cross-document links:")
                for _nm, _nd, _cnt in _top:
                    print("      %-36s %3d documents  %6d mentions"
                          % (str(_nm)[:36], _nd, _cnt))
        except Exception as _e:
            print("    (top entities unavailable: %s)" % _e)

_live = q("SELECT COUNT(*) FROM passages p WHERE "
          "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') "
          "AND TRIM(COALESCE(p.text,'')) <> ''")
if "passage_embeddings" in tabs and _live:
    _emb = q("SELECT COUNT(*) FROM passage_embeddings e JOIN passages p "
             "ON p.id = e.passage_id WHERE "
             "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')")
    print("\n  semantic index coverage")
    print("    live passages               %7d" % _live)
    print("    with a vector               %7d   %5.1f%%" % (_emb, 100.0 * _emb / _live))
    print("    with NO vector              %7d   %5.1f%%"
          % (_live - _emb, 100.0 * (_live - _emb) / _live))
    print("\n  VERDICT")
    _epct = 100.0 * _emb / _live
    if _ec and _mc and _eid and _pid and _tot:
        _mpct = 100.0 * _multi / _tot
        print("    %.0f%% of entities are mentioned in only one document, and %.0f%% of"
              % (100.0 - _mpct, 100.0 - _epct))
        print("    live passages are not in the semantic index. The links that exist")
        print("    are real - %d entities span two or more texts, and %d span five or"
              % (_multi, _five))
        print("    more - but most of the corpus is not yet reachable from the rest.")
    else:
        print("    %.0f%% of live passages are not in the semantic index." % (100.0 - _epct))
    print("    Both gaps close with the incremental passes the maintenance runner")
    print("    already calls - build_embeddings.py, then extract_entities.py. The")
    print("    shortfall is coverage, not design.")

print("\nWhat this means: a wipe+re-ingest gives passages NEW ids. Vectors and entity")
print("mentions keyed to the OLD ids become orphans, and the new text has no vectors or")
print("entity links until build_embeddings.py and extract_entities.py are re-run.")
c.close()
