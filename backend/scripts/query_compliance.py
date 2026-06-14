import sqlite3
from collections import Counter
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "lingxi.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute(
    """
    SELECT id, question, action, matched_word, created_at
    FROM compliance_logs
    WHERE question LIKE '%茅台%' OR question LIKE '%能买%'
    ORDER BY created_at
    """
)
rows = [dict(r) for r in cur.fetchall()]
out = Path(__file__).with_name("compliance_query_result.txt")
lines = [f"total={len(rows)}"]
for r in rows:
    lines.append(f"{r['id']}|{r['created_at']}|{r['matched_word']}|{r['question']}")
lines.append("---group---")
for q, cnt in Counter(r["question"] for r in rows).most_common():
    lines.append(f"{cnt}x {q}")
out.write_text("\n".join(lines), encoding="utf-8")
print(out)
