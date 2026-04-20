"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add src to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_professor():
    """Provide a sample professor for tests."""
    from phd_hunter.models import Professor, ProfessorStatus

    return Professor(
        id="test_prof",
        name="Test Professor",
        university="Test University",
        email="test@test.edu",
        research_interests=["AI", "ML"],
        status=ProfessorStatus.ACCEPTING,
        citation_count=5000,
        h_index=30,
    )


@pytest.fixture
def sample_paper():
    """Provide a sample paper for tests."""
    from phd_hunter.models import Paper

    return Paper(
        id="test_paper",
        title="Test Paper",
        authors=["Author A", "Author B"],
        abstract="Test abstract",
        year=2024,
        citations=10,
    )
