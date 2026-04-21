#!/usr/bin/env python3
"""Demo script to test arXiv author search effectiveness."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import arxiv
import time


def search_arxiv_by_author(name: str, max_results: int = 10) -> list:
    """Search arXiv for papers by author."""
    # arXiv query syntax: au:"Author Name"
    query = f'au:"{name}"'

    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate  # Sort by submission date (newest first)
        )

        papers = []
        for result in search.results():
            papers.append({
                'title': result.title,
                'authors': [a.name for a in result.authors],
                'year': result.published.year,
                'month': result.published.month,
                'pdf_url': result.pdf_url,
                'entry_id': result.entry_id,
                'categories': result.categories,
                'comment': result.comment,
            })

        return papers
    except Exception as e:
        print(f"  Error: {e}")
        return []


def main():
    print("=" * 70)
    print("arXiv Author Search Demo")
    print("=" * 70)

    # Test with professors from our database
    test_professors = [
        "Yangqiu Song",
        "Pascale Fung",
        "Xuming Hu",
    ]

    for prof_name in test_professors:
        print(f"\n{'='*70}")
        print(f"Searching for: {prof_name}")
        print("=" * 70)

        papers = search_arxiv_by_author(prof_name, max_results=10)

        if papers:
            print(f"Found {len(papers)} papers:")
            for i, paper in enumerate(papers, 1):
                print(f"\n  [{i}] {paper['title']}")
                print(f"      Authors: {', '.join(paper['authors'])}")
                print(f"      Year: {paper['year']}-{paper['month']:02d}")
                print(f"      Categories: {', '.join(paper['categories'])}")
                print(f"      PDF: {paper['pdf_url']}")
                if paper['comment']:
                    print(f"      Comment: {paper['comment']}")
        else:
            print("  No papers found!")

        time.sleep(3)  # Be respectful with rate limiting (3s between authors)

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
