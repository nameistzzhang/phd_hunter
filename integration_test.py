#!/usr/bin/env python3
"""Quick integration test for arXiv crawler + database."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from phd_hunter.crawlers.arxiv_crawler import ArxivCrawler
from phd_hunter.database import Database
from phd_hunter.models import Professor
import tempfile
import os

def main():
    print("=" * 60)
    print("Integration Test: ArxivCrawler + Database")
    print("=" * 60)

    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # 1. Initialize database
        print("\n[1] Initializing database...")
        db = Database(db_path=db_path)
        print("    Database created OK")

        # 2. Insert test professor
        print("\n[2] Inserting test professor...")
        test_prof = Professor(
            name="Test Professor",
            university="Test University",
            email="test@test.edu",
        )
        from phd_hunter.models import University
        test_uni = University(
            name="Test University",
            rank=1,
            score=100.0,
            paper_count=1000,
            cs_rankings_url="https://test.edu"
        )
        prof_id = db.upsert_professor(test_prof, test_uni)
        print(f"    Professor ID: {prof_id}")

        # 3. Fetch papers via ArxivCrawler
        print("\n[3] Fetching papers from arXiv...")
        crawler = ArxivCrawler(delay=0.5)
        papers = crawler.fetch(test_prof, max_papers=3)
        crawler.close()

        if papers:
            print(f"    Found {len(papers)} papers")
            for i, p in enumerate(papers, 1):
                print(f"      [{i}] {p.title[:60]}...")
        else:
            print("    No papers found (this is OK if test professor has no arXiv papers)")

        # 4. Save papers to database
        print("\n[4] Saving papers to database...")
        saved_count = 0
        for paper in papers:
            paper_data = {
                'arxiv_id': paper.arxiv_id,
                'title': paper.title,
                'abstract': paper.abstract,
                'year': paper.year,
                'venue': paper.venue,
                'url': paper.url,
                'openaccess_pdf': getattr(paper, 'pdf_url', None),
            }
            db.upsert_paper(prof_id, paper_data)
            saved_count += 1
        print(f"    Saved {saved_count} papers")

        # 5. Verify data
        print("\n[5] Verifying data...")
        stats = db.get_stats()
        print(f"    Universities: {stats['universities']}")
        print(f"    Professors: {stats['professors']}")
        print(f"    Papers: {stats['papers']}")

        papers_from_db = db.get_papers_by_professor(prof_id)
        print(f"    Papers for test professor: {len(papers_from_db)}")

        # 6. Export test
        print("\n[6] Testing export...")
        export_path = "test_export.json"
        db.export_to_json(export_path)
        print(f"    Exported to {export_path}")
        import json
        with open(export_path) as f:
            data = json.load(f)
        print(f"    Export contains {len(data['professors'])} professors, {sum(len(p['papers']) for p in data['professors'])} papers")

        print("\n" + "=" * 60)
        print("Integration test PASSED!")
        print("=" * 60)

    finally:
        # Cleanup
        try:
            db.close()
        except:
            pass
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except:
                pass
        if os.path.exists("test_export.json"):
            try:
                os.unlink("test_export.json")
            except:
                pass

if __name__ == "__main__":
    main()
