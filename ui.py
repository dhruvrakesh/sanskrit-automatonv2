import os, subprocess, sqlite3, time, tempfile, glob, sys
import streamlit as st
import pandas as pd

PY = sys.executable  # use current Python


DB_PATH = "data/context.db"

st.title("Sanskrit Automaton")

proj = st.text_input("Project prefix (e.g., NEWBOOK)", value="NEWBOOK")
uploaded = st.file_uploader("Drop PDFs", type=["pdf"], accept_multiple_files=True)

if uploaded:
    inbox = "inbox"
    os.makedirs(inbox, exist_ok=True)
    saved = []
    for f in uploaded:
        path = os.path.join(inbox, f.name)
        with open(path, "wb") as out: out.write(f.getbuffer())
        saved.append(path)
    st.success(f"Saved {len(saved)} PDFs to {inbox}")

if st.button("Ingest PDFs in inbox"):
    run = f"ingest-{proj}-{time.strftime('%Y%m%d-%H%M%S')}"
    for pdf in glob.glob("inbox/*.pdf"):
        code = f"{proj}-{os.path.splitext(os.path.basename(pdf))[0]}"
        # ingest PDFs
        subprocess.run([PY, "scripts\\ingest_pdf.py",
                        "--pdf", pdf, "--doc", code, "--run-id", run],
                       check=False)

        st.success("Ingest complete")

if st.button("Translate missing (this project only)"):
    # translate missing: run once per doc under this prefix
    with sqlite3.connect(DB_PATH) as con:
        docs = [r[0] for r in con.execute(
            "SELECT code FROM docs WHERE code LIKE ? ORDER BY code", (f"{proj}-%",)
        )]
    for d in docs:
        subprocess.run([PY, "scripts\\translate_passages.py",
                        "--doc", d, "--sleep", "1.0"], check=False)

    st.success("Translate kick-off issued")

# progress table
# progress table prettier
con = sqlite3.connect(DB_PATH)
rows = con.execute("""
  SELECT d.code AS doc, COUNT(*) AS total,
         SUM(CASE WHEN IFNULL(TRIM(p.translation),'')='' THEN 1 ELSE 0 END) AS missing
  FROM passages p JOIN docs d ON d.id=p.doc_id
  WHERE d.code LIKE ? GROUP BY d.code ORDER BY d.code
""",(f"{proj}-%",)).fetchall()
con.close()
df = pd.DataFrame(rows, columns=["doc","total","missing"])
st.dataframe(df, use_container_width=True)
