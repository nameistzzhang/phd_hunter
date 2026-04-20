"""Data models and schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ProfessorStatus(str, Enum):
    """Professor availability status."""
    ACCEPTING = "accepting"
    NOT_ACCEPTING = "not_accepting"
    UNKNOWN = "unknown"
    CONDITIONAL = "conditional"


class University(BaseModel):
    """University/institution data from CSRankings."""
    id: Optional[int] = None
    name: str
    rank: int
    score: float
    paper_count: int
    cs_rankings_url: str
    department_url: Optional[str] = None
    location: Optional[str] = None  # city, country
    # Will be populated from faculty pages
    professor_count: int = 0
    faculty_url: Optional[str] = None


class Professor(BaseModel):
    """Professor data model."""
    id: Optional[int] = None
    name: str
    university: str
    department: Optional[str] = None
    homepage: Optional[str] = None
    scholar_url: Optional[str] = None
    email: Optional[str] = None
    research_interests: List[str] = Field(default_factory=list)
    status: ProfessorStatus = ProfessorStatus.UNKNOWN

    # Metrics from Google Scholar
    citation_count: int = 0
    h_index: int = 0
    i10_index: int = 0

    # Activity metrics
    total_papers: int = 0
    recent_papers: int = 0  # Last 5 years
    papers_per_year: float = 0.0

    # Computed scores
    match_score: float = 0.0  # 0-100
    research_alignment: float = 0.0
    activity_score: float = 0.0

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    source_urls: List[str] = Field(default_factory=list)


class Paper(BaseModel):
    """Paper data model."""
    id: Optional[int] = None
    arxiv_id: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str
    venue: Optional[str] = None
    year: int
    citations: int = 0
    url: Optional[str] = None
    pdf_path: Optional[str] = None

    # LLM analysis results
    themes: List[str] = Field(default_factory=list)
    methodologies: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    quality_score: Optional[float] = None


class AnalysisResult(BaseModel):
    """LLM analysis result for a paper or professor."""
    id: str
    target_id: str  # Professor or paper ID
    analysis_type: str  # "paper", "professor", "fit"
    content: dict
    llm_model: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)


class FitAssessment(BaseModel):
    """Student-professor fit assessment."""
    professor_id: str
    overall_score: float = Field(ge=0, le=100)
    research_alignment: float = Field(ge=0, le=100)
    skill_match: float = Field(ge=0, le=100)
    career_alignment: float = Field(ge=0, le=100)

    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    recommendation: str  # "strongly_consider", "consider", "maybe", "not_recommended"
    reasoning: str


class Report(BaseModel):
    """Generated report model."""
    professor_id: str
    report_type: str  # "full", "summary", "comparison"
    format: str  # "html", "pdf", "json", "markdown"

    executive_summary: str
    professor_profile: Professor
    research_analysis: dict
    fit_assessment: FitAssessment
    application_strategy: str
    risk_factors: List[str]

    generated_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[str] = None


class SearchQuery(BaseModel):
    """Search query parameters."""
    universities: List[str] = Field(default_factory=list)
    research_area: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    min_match_score: float = 50.0
    max_professors: int = 50
    include_papers: bool = True


class SearchResult(BaseModel):
    """Search results container."""
    search_id: str
    query: SearchQuery
    professors: List[Professor]
    total_found: int
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
