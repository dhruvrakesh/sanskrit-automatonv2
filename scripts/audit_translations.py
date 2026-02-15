import os, glob, re, sqlite3, json, sys

DOC = "MBh-01"
DB  = r"data/context.db"
NORM_GLOB = r"data/norm/mbh-01_*.jsonl"

# Pages we intended to have (from files)
def file_pages():
    pages = set()
    rx = re.compile(r"_(\d+)\.jsonl$")
    for p in glob.glob(NORM_GLOB):
        m = rx.search(os.path.basename(p))
        if m:
            pages.add(int(m.group(1)))
    return pages

# Pages we actually have in DB
def db_pages(con):
    cur=con.cursor()
    rows=cur.execute("""select distinct p.page_no
                        from passages p join docs d on d.id=p.doc_id
                        where d.code=?""",(DOC,)).fetchall()
    return {r[0] for r in rows}

# Per-page missing translations (simple check)
def pages_with_missing(con):
    cur=con.cursor()
    rows=cur.execute("""select p.page_no, count(*)
                        from passages p
                        join docs d on d.id=p.doc_id
                        where d.code=? and (p.translation is null or trim(p.translation)='')
                        group by p.page_no
                        order by p.page_no""",(DOC,)).fetchall()
    return rows

con = sqlite3.connect(DB)

want = file_pages()
have = db_pages(con)
missing_pages = sorted(want - have)

print("INPUT files:", len(want), "pages; DB has:", len(have), "pages")
if missing_pages:
    print("Pages missing in DB:", missing_pages[:20], ("… +%d more" % (len(missing_pages)-20) if len(missing_pages)>20 else ""))
else:
    print("All file pages present in DB ✅")

rows = pages_with_missing(con)
total_missing_rows = sum(n for _,n in rows)
print("Pages with any empty translations:", len(rows), " (empty rows:", total_missing_rows, ")")
if rows:
    print("First few page→missing-row counts:", rows[:10])
