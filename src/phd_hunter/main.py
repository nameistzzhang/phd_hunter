"""Main application entry point."""

import asyncio
from typing import Optional

from .crawlers import CSRankingsCrawler
from .agents.base import BaseAgent, AgentMessage, AgentResult
from .llm import LLMClient
from .utils import get_logger
from .models import Professor, SearchQuery, SearchResult

logger = get_logger(__name__)


class PhDHunter:
    """Main application class for PhD Hunter."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        llm_provider: Optional[str] = None,
    ):
        """Initialize PhD Hunter.

        Args:
            config_path: Path to configuration file
            llm_provider: Override LLM provider (openai/anthropic)
        """
        from .utils.config import load_config

        self.config = load_config(config_path)

        # Override LLM provider if specified
        if llm_provider:
            self.config.llm.provider = llm_provider

        # Initialize LLM client
        self.llm = LLMClient(self.config.llm)

        logger.info(f"PhD Hunter initialized with {self.config.llm.provider}/{self.config.llm.model}")

    async def search(
        self,
        universities: Optional[list[str]] = None,
        research_area: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        max_professors: int = 50,
    ) -> SearchResult:
        """Search for professors.

        Args:
            universities: List of university names
            research_area: Research area/field
            keywords: Additional keywords
            max_professors: Maximum number of professors to return

        Returns:
            SearchResult with professor list
        """
        logger.info(f"Starting search: universities={universities}, area={research_area}")

        # Step 1: Fetch professors from CSRankings
        crawler = CSRankingsCrawler(
            headless=self.config.crawlers.get("headless", True),
            cache_enabled=True,
        )

        areas = [research_area] if research_area else None
        professors = crawler.fetch(
            universities=universities,
            areas=areas,
        )

        # Limit results
        professors = professors[:max_professors]

        logger.info(f"Search complete: found {len(professors)} professors")

        return SearchResult(
            search_id=f"search_{hash(str(universities) + str(research_area))}",
            query=SearchQuery(
                universities=universities or [],
                research_area=research_area,
                keywords=keywords or [],
                max_professors=max_professors,
            ),
            professors=professors,
            total_found=len(professors),
            completed=True,
        )


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="PhD Hunter - PhD advisor matching system")
    parser.add_argument("--universities", nargs="+", help="University names")
    parser.add_argument("--area", help="Research area")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--llm", choices=["openai", "anthropic"], help="LLM provider")

    args = parser.parse_args()

    hunter = PhDHunter(config_path=args.config, llm_provider=args.llm)

    result = asyncio.run(hunter.search(
        universities=args.universities,
        research_area=args.area,
    ))

    print(f"\nFound {len(result.professors)} professors:")
    for prof in result.professors:
        print(f"  - {prof.name} ({prof.university}) - Score: {prof.match_score:.1f}")


if __name__ == "__main__":
    main()
