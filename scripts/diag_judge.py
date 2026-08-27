import sqlite3, sys
# Read-only: inspect Q4 judge verdicts and where the LLM-judge disagrees with the
# heuristic translation_qa (the early-warning signal QUALITY_LOOP_DESIGN wanted).
db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
lang = sys.argv[2] if len(sys.argv) > 2 else "en"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

print(f"=== Q4 verdict summary (lang={lang}) ===")
row = c.execute("""SELECT COUNT(*), ROUND(AVG(score_fidelity),2), ROUND(AVG(score_fluency),2),
                          SUM(CASE WHEN score_fidelity IS NULL THEN 1 ELSE 0 END)
                   FROM mt_reviews WHERE lang=?""", [lang]).fetchone()
print(f"  reviews={row[0]}  avg_fidelity={row[1]}  avg_fluency={row[2]}  unparsed(NULL)={row[3]}")

print("\n=== lowest-fidelity verdicts (the real semantic concerns) ===")
for code, f, u, cm in c.execute("""
    SELECT d.code, r.score_fidelity, r.score_fluency, r.comment
    FROM mt_reviews r JOIN passages p ON p.id=r.passage_id JOIN docs d ON d.id=p.doc_id
    WHERE r.lang=? AND r.score_fidelity IS NOT NULL
    ORDER BY r.score_fidelity, r.score_fluency LIMIT 12""", [lang]):
    print(f"  fid={f} flu={u}  {code[:28]:28s} {cm[:60]}")

print("\n=== judge-vs-heuristic DISAGREEMENT (judge fid<=2 but translation_qa>=0.8) ===")
dis = c.execute("""
    SELECT d.code, r.score_fidelity, ROUND(p.translation_qa,2), r.comment
    FROM mt_reviews r JOIN passages p ON p.id=r.passage_id JOIN docs d ON d.id=p.doc_id
    WHERE r.lang=? AND r.score_fidelity<=2 AND p.translation_qa>=0.8 LIMIT 15""", [lang]).fetchall()
if not dis:
    print("  none — heuristic QA and the judge agree on the sampled verses.")
for code, f, qa, cm in dis:
    print(f"  {code[:28]:28s} judge_fid={f} qa={qa}  {cm[:55]}")
c.close()
