import sqlite3

DB="data/context.db"
DOC="panchatantra"

with sqlite3.connect(DB) as con:
    cur = con.cursor()
    # figure out which column is the page number
    page_cols = [r[1] for r in cur.execute("PRAGMA table_info(pages)")]
    page_col = next((c for c in ["page","number","pageno","index"] if c in page_cols), None)

    tot = cur.execute("""
        SELECT COUNT(*)
        FROM passages pa
        JOIN pages p ON p.id = pa.page_id
        WHERE p.doc = ?
    """, (DOC,)).fetchone()[0]

    miss = cur.execute("""
        SELECT COUNT(*)
        FROM passages pa
        JOIN pages p ON p.id = pa.page_id
        WHERE p.doc = ? AND (pa.en IS NULL OR TRIM(pa.en) = '')
    """, (DOC,)).fetchone()[0]

    print(f"total={tot}  missing_en={miss}  covered={tot-miss}")
    if page_col:
        # show a couple of examples that are missing
        rows = cur.execute(f"""
            SELECT p.{page_col} AS pg, SUBSTR(pa.san,1,60)
            FROM passages pa
            JOIN pages p ON p.id = pa.page_id
            WHERE p.doc = ? AND (pa.en IS NULL OR TRIM(pa.en) = '')
            LIMIT 10
        """, (DOC,)).fetchall()
        if rows:
            print("examples missing:", rows)
