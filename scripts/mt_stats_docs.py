import os, sqlite3, argparse

DB = os.getenv("SA_DB_PATH", "data/context.db")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True, help="doc code, e.g. panchatantra")
    args = ap.parse_args()

    with sqlite3.connect(DB) as con:
        cur = con.cursor()

        tot = cur.execute("""
            SELECT COUNT(*)
            FROM passages p
            JOIN docs d ON d.id = p.doc_id
            WHERE d.code = ?
        """, (args.doc,)).fetchone()[0]

        miss = cur.execute("""
            SELECT COUNT(*)
            FROM passages p
            JOIN docs d ON d.id = p.doc_id
            WHERE d.code = ? AND (p.translation IS NULL OR TRIM(p.translation) = '')
        """, (args.doc,)).fetchone()[0]

        print(f"total={tot}  missing_en={miss}  covered={tot-miss}")

        # show a few missing examples (page_no + preview)
        rows = cur.execute("""
            SELECT p.page_no, substr(p.text,1,80)
            FROM passages p
            JOIN docs d ON d.id = p.doc_id
            WHERE d.code = ? AND (p.translation IS NULL OR TRIM(p.translation) = '')
            ORDER BY p.page_no, p.idx
            LIMIT 10
        """, (args.doc,)).fetchall()
        if rows:
            print("examples missing:", rows)

if __name__ == "__main__":
    main()
