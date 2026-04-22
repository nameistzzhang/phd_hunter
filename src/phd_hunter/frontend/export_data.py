#!/usr/bin/env python3
"""Export database to JSON for frontend consumption."""

import json
import sqlite3
from pathlib import Path

DB_PATH = "phd_hunter.db"
OUTPUT_DIR = Path(__file__).parent / "static" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all professors
cursor.execute("SELECT * FROM professors ORDER BY match_score DESC")
professors = [dict(row) for row in cursor.fetchall()]

# Parse JSON fields and attach papers
for prof in professors:
    # Parse research_interests
    if isinstance(prof.get('research_interests'), str):
        try:
            prof['research_interests'] = json.loads(prof['research_interests'])
        except:
            prof['research_interests'] = []

    # Parse source_urls
    if isinstance(prof.get('source_urls'), str):
        try:
            prof['source_urls'] = json.loads(prof['source_urls'])
        except:
            prof['source_urls'] = []

    # Get papers
    cursor.execute("""
        SELECT * FROM papers
        WHERE professor_id = ?
        ORDER BY year DESC, created_at DESC
    """, (prof['id'],))
    papers = [dict(row) for row in cursor.fetchall()]
    prof['papers'] = papers

# Write to JSON
output_file = OUTPUT_DIR / "professors.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        'professors': professors,
        'count': len(professors),
        'universities': len(set(p['university_name'] for p in professors))
    }, f, indent=2, ensure_ascii=False)

print(f"[OK] Exported {len(professors)} professors to {output_file}")

# Also write stats
cursor.execute("SELECT COUNT(DISTINCT university_name) as unis FROM professors")
uni_count = cursor.fetchone()['unis']
cursor.execute("SELECT COUNT(*) as papers FROM papers")
paper_count = cursor.fetchone()['papers']
cursor.execute("SELECT AVG(match_score) as avg FROM professors")
avg_score = cursor.fetchone()['avg'] or 0

stats_file = OUTPUT_DIR / "stats.json"
with open(stats_file, 'w', encoding='utf-8') as f:
    json.dump({
        'universities': uni_count,
        'professors': len(professors),
        'papers': paper_count,
        'avg_match_score': round(avg_score, 1)
    }, f, indent=2)

print(f"[OK] Stats exported to {stats_file}")

conn.close()
