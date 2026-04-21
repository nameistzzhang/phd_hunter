#!/usr/bin/env python3
"""PhD Hunter - Simplified CLI for CS professor research.

Workflow:
  1. crawl: 从 CSRankings 爬取教授信息并存入数据库
  2. fetch-papers: 从 arXiv 获取每位教授的最新论文
  3. stats: 查看数据库统计信息
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from phd_hunter.crawlers import CSRankingsCrawler, ArxivCrawler
from phd_hunter.database import Database
from phd_hunter.utils.logger import get_logger, setup_logger
from phd_hunter.models import Professor, University

logger = get_logger(__name__)


def cmd_crawl(args):
    """Crawl CSRankings for professor data."""
    print("=" * 70)
    print("Phase 1: 从 CSRankings 爬取教授信息")
    print("=" * 70)

    db = Database(db_path=args.db)

    crawler = CSRankingsCrawler(
        headless=args.headless,
        timeout=args.timeout,
        verbose=args.verbose,
        db_path=args.db,
    )

    try:
        result = crawler.fetch(
            areas=[args.area] if args.area else None,
            region=args.region,
            include_professors=True,
            max_universities=args.max_universities,
            max_professors=args.max_professors,
        )

        # Unpack result
        universities, professors = result

        print(f"\n[OK] 成功爬取 {len(universities)} 所大学")
        print(f"[OK] 成功获取 {len(professors)} 位教授")

        # Build university lookup dict
        uni_by_name = {uni.name: uni for uni in universities}

        # Save to database
        print("\nSaving to database...")
        saved_count = 0
        for prof in professors:
            # Get university info
            uni = uni_by_name.get(prof.university)
            if not uni:
                # Create minimal uni record if not found
                uni = University(
                    name=prof.university,
                    rank=0,
                    score=0.0,
                    paper_count=0,
                    cs_rankings_url="",
                )
            db.upsert_professor(prof, uni)
            saved_count += 1

        print(f"[OK] 已保存 {saved_count} 位教授到数据库")

        # Show top universities
        print("\nTop universities:")
        for uni in universities[:5]:
            print(f"  {uni.rank}. {uni.name} (score: {uni.score:.1f})")

        # Show professors summary
        if professors:
            print(f"\nProfessors (first 10):")
            for prof in professors[:10]:
                print(f"  - {prof.name} ({prof.university})")

    finally:
        crawler.close()

    print("\n[OK] 爬取完成！")


def cmd_fetch_papers(args):
    """Fetch papers from arXiv for all professors in database."""
    print("=" * 70)
    print("Phase 2: 从 arXiv 获取教授论文")
    print("=" * 70)

    db = Database(db_path=args.db)
    arxiv_crawler = ArxivCrawler(delay=args.delay)

    try:
        # Get all professors from database
        professors = db.list_professors(limit=args.max_professors)

        if not professors:
            print("[WARN] 数据库中没有教授记录。请先运行 'crawl' 命令。")
            return

        print(f"找到 {len(professors)} 位教授，开始获取论文...\n")

        total_papers = 0
        success_count = 0

        for i, prof_dict in enumerate(professors, 1):
            prof_name = prof_dict['name']
            prof_id = prof_dict['id']

            print(f"[{i}/{len(professors)}] {prof_name}")

            # Reconstruct Professor object
            prof = Professor(
                id=prof_id,
                name=prof_name,
                university=prof_dict['university_name'],
            )

            # Fetch papers from arXiv
            papers = arxiv_crawler.fetch(prof, max_papers=args.max_papers)

            if papers:
                print(f"    [OK] 找到 {len(papers)} 篇论文")
                total_papers += len(papers)
                success_count += 1

                # Save papers to database
                for paper in papers:
                    paper_data = {
                        's2_paper_id': paper.arxiv_id,  # Use arxiv_id as paper identifier
                        'title': paper.title,
                        'abstract': paper.abstract,
                        'year': paper.year,
                        'venue': paper.venue,
                        'url': paper.url,
                        'openaccess_pdf': paper.pdf_url if hasattr(paper, 'pdf_url') else None,
                    }
                    db.upsert_paper(prof_id, paper_data)
            else:
                print(f"    [WARN] 未找到论文")

            # Progress separator
            if i % 10 == 0:
                print(f"\n    Progress: {i}/{len(professors)} professors processed\n")

        print("\n" + "=" * 70)
        print(f"[OK] 完成！成功获取 {total_papers} 篇论文（{success_count}/{len(professors)} 位教授）")
        print("=" * 70)

    finally:
        arxiv_crawler.close()


def cmd_stats(args):
    """Show database statistics."""
    db = Database(db_path=args.db)

    stats = db.get_stats()

    print("=" * 70)
    print("数据库统计")
    print("=" * 70)
    print(f"  大学数量 : {stats['universities']}")
    print(f"  教授数量 : {stats['professors']}")
    print(f"  论文数量 : {stats['papers']}")
    print(f"  有 PDF   : {stats['papers_with_pdf']}")
    print(f"  平均论文 : {stats['avg_papers']}")
    print(f"  平均匹配分: {stats['avg_match_score']}")
    print("\n教授状态分布:")
    for status, count in stats.get('by_status', {}).items():
        print(f"  {status}: {count}")
    print("=" * 70)


def cmd_list(args):
    """List professors in database."""
    db = Database(db_path=args.db)

    professors = db.list_professors(
        min_match_score=args.min_score,
        limit=args.limit
    )

    print("=" * 70)
    print(f"教授列表 (共 {len(professors)} 位)")
    print("=" * 70)

    for prof in professors:
        print(f"\n  {prof['name']}")
        print(f"    大学    : {prof['university_name']}")
        print(f"    状态    : {prof['status']}")
        print(f"    论文数  : {prof['total_papers']}")
        print(f"    匹配分  : {prof['match_score']:.1f}")
        if prof.get('research_interests'):
            import json
            interests = json.loads(prof['research_interests'])
            if interests:
                print(f"    研究方向: {', '.join(interests[:3])}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        prog="phd-hunter",
        description="PhD 导师套磁筛选助手 - 自动化 CS 教授信息收集与分析"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # Global options
    parser.add_argument(
        "--db", default="phd_hunter.db",
        help="SQLite 数据库路径 (默认: phd_hunter.db)"
    )

    # --- crawl 命令 ---
    crawl_parser = subparsers.add_parser("crawl", help="从 CSRankings 爬取教授信息")
    crawl_parser.add_argument(
        "--area", default="ai",
        help="研究领域 (默认: ai)。可选: ai, systems, theory, etc."
    )
    crawl_parser.add_argument(
        "--region", default="world",
        help="地区过滤 (默认: world)。可选: us, cn, northamerica, europe, etc."
    )
    crawl_parser.add_argument(
        "--max-universities", type=int, default=None,
        help="最大处理大学数量 (默认: 全部)"
    )
    crawl_parser.add_argument(
        "--max-professors", type=int, default=5,
        help="每所大学最大教授数量 (默认: 5)"
    )
    crawl_parser.add_argument(
        "--no-headless", dest="headless", action="store_false", default=True,
        help="显示浏览器窗口（默认无头模式）"
    )
    crawl_parser.add_argument(
        "--timeout", type=int, default=30,
        help="页面加载超时（秒）"
    )
    crawl_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="详细日志输出"
    )

    # --- fetch-papers 命令 ---
    fetch_parser = subparsers.add_parser(
        "fetch-papers",
        help="从 arXiv 获取教授论文"
    )
    fetch_parser.add_argument(
        "--max-papers", type=int, default=10,
        help="每位教授最大论文数 (默认: 10)"
    )
    fetch_parser.add_argument(
        "--max-professors", type=int, default=None,
        help="最大处理教授数量 (默认: 全部)"
    )
    fetch_parser.add_argument(
        "--delay", type=float, default=3.0,
        help="请求间隔（秒），避免速率限制 (默认: 3.0)"
    )

    # --- stats 命令 ---
    subparsers.add_parser("stats", help="显示数据库统计信息")

    # --- list 命令 ---
    list_parser = subparsers.add_parser("list", help="列出数据库中的教授")
    list_parser.add_argument(
        "--limit", type=int, default=20,
        help="最大显示数量 (默认: 20)"
    )
    list_parser.add_argument(
        "--min-score", type=float, default=0.0,
        help="最低匹配分数过滤 (默认: 0)"
    )

    args = parser.parse_args()

    # Setup logger
    setup_logger(level="INFO")

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "crawl":
            cmd_crawl(args)
        elif args.command == "fetch-papers":
            cmd_fetch_papers(args)
        elif args.command == "stats":
            cmd_stats(args)
        elif args.command == "list":
            cmd_list(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\n\n[WARN] 操作被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
