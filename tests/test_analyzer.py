"""Offline test for the Analyzer module.

Usage:
    cd D:/EricDoc/Study/Applications/phd_hunter
    python -m tests.test_analyzer

Requirements:
    - Database has at least one professor with homepage_summary (e.g., id=239)
    - Profile table has data (preferences + paper_links; CV/PS optional)
    - hound_config.json is configured with a valid API key
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phd_hunter.analyzer import analyze_professor_first_time
from phd_hunter.database import Database

DB_PATH = str(Path(__file__).parent.parent / "phd_hunter.db")


def list_professors_with_summary():
    """List professors that have homepage_summary for testing."""
    db = Database(db_path=DB_PATH)
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT id, name, university_name, homepage_summary FROM professors "
        "WHERE homepage_summary IS NOT NULL AND homepage_summary != '' "
        "LIMIT 5"
    )
    rows = cursor.fetchall()
    db.close()
    return [dict(row) for row in rows]


def check_profile():
    """Check if applicant profile exists."""
    db = Database(db_path=DB_PATH)
    profile = db.get_profile()
    db.close()
    return profile


async def main():
    print("=" * 70)
    print("Analyzer Offline Test")
    print("=" * 70)

    # Check profile
    profile = check_profile()
    if not profile:
        print("\n[ERROR] No applicant profile found.")
        print("Please fill in the Profile page (preferences, papers) first.")
        return

    print(f"\n[Profile]")
    print(f"  Preferences: {(profile.get('preferences') or '')[:100]}...")
    print(f"  Papers: {len(profile.get('paper_links', []))}")
    print(f"  CV: {'Yes' if profile.get('cv_path') else 'No'}")
    print(f"  PS: {'Yes' if profile.get('ps_path') else 'No'}")

    # Find professors with summary
    profs = list_professors_with_summary()
    if not profs:
        print("\n[ERROR] No professors with homepage_summary found.")
        print("Run the scorer daemon first to fetch professor homepages.")
        return

    print(f"\n[Professors with homepage_summary]:")
    for p in profs:
        print(f"  id={p['id']}: {p['name']} @ {p['university_name']}")
        print(f"    summary: {p['homepage_summary'][:120]}...")

    # Use the first professor for testing
    test_prof = profs[0]
    prof_id = test_prof["id"]

    print(f"\n{'=' * 70}")
    print(f"Testing analyze_professor_first_time(professor_id={prof_id})")
    print(f"Professor: {test_prof['name']} @ {test_prof['university_name']}")
    print(f"{'=' * 70}\n")

    result = await analyze_professor_first_time(
        professor_id=prof_id,
        db_path=DB_PATH,
    )

    if result:
        print("\n" + "=" * 70)
        print("SUCCESS - Assistant Response:")
        print("=" * 70)
        print(result)
        print("\n" + "=" * 70)

        # Verify messages were saved
        db = Database(db_path=DB_PATH)
        prof = db.get_professor_hound_data(prof_id)
        db.close()
        messages = prof.get("messages", [])
        print(f"\n[Verification] Messages saved: {len(messages)} entries")
        for i, m in enumerate(messages):
            print(f"  [{i}] role={m['role']}, content_len={len(m['content'])}")
    else:
        print("\n[ERROR] analyze_professor_first_time returned None.")


if __name__ == "__main__":
    asyncio.run(main())
