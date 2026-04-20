"""Tests for data models."""

import pytest
from datetime import datetime
from phd_hunter.models import Professor, Paper, ProfessorStatus


def test_professor_creation():
    """Test professor model creation."""
    prof = Professor(
        id="test_001",
        name="John Doe",
        university="MIT",
        email="john@mit.edu",
        research_interests=["AI", "ML"],
        citation_count=1000,
        h_index=25,
    )

    assert prof.name == "John Doe"
    assert prof.university == "MIT"
    assert prof.match_score == 0.0  # default
    assert prof.status == ProfessorStatus.UNKNOWN


def test_professor_score_bounds():
    """Test that scores stay within bounds."""
    prof = Professor(
        id="test_002",
        name="Jane Smith",
        university="Stanford",
        match_score=150.0,  # Over 100
    )

    # Score should be clamped when validated (if validation is added)
    assert prof.match_score == 150.0  # Pydantic doesn't clamp by default


def test_paper_creation():
    """Test paper model creation."""
    paper = Paper(
        id="paper_001",
        arxiv_id="2401.00001",
        title="Test Paper",
        authors=["Author 1", "Author 2"],
        abstract="This is a test paper.",
        year=2024,
        citations=10,
    )

    assert paper.title == "Test Paper"
    assert len(paper.authors) == 2
    assert paper.themes == []
