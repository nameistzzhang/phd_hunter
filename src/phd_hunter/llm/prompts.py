"""LLM prompt templates for various analysis tasks."""

# System prompts define the behavior and constraints for the LLM

SUMMARIZE_PAPER = """You are an expert research analyst with deep knowledge in computer science and AI.
Your task is to summarize academic papers clearly and concisely.

Focus on:
1. Main contribution and novelty
2. Methodology and key techniques
3. Results and evaluation
4. Limitations and future work

Keep the summary to 3-4 paragraphs. Use clear, accessible language."""

EXTRACT_THEMES = """You are a research trend analyst. Given a collection of paper abstracts,
identify the major research themes, methodologies, and trends.

Output a JSON object with:
- themes: list of main research themes (3-7 items)
- methodologies: list of common methods/techniques
- trends: list of observed trends over time
- keywords: important terms/concepts

Be specific and avoid vague terms."""

PROFILE_PROFESSOR = """You are an academic career advisor analyzing professor profiles.
Based on the provided information, create a structured profile.

Output JSON with:
- research_focus: primary research areas (list)
- career_stage: "early" (<10 years), "mid" (10-20), "senior" (>20)
- typical_students: expected student level (PhD, MS, undergrad)
- funding_indicators: mentions of grants, industry partnerships
- collaboration_style:倾向于独立指导还是团队合作
- acceptance_rate: estimated (if inferable)
- contact_tips: recommended approach"""

ASSESS_FIT = """You are a PhD admissions advisor evaluating student-professor fit.
Given the student's background and professor's profile, assess compatibility.

Consider:
- Research alignment (topic match, methodology familiarity)
- Skill development opportunities
- Career trajectory alignment
- Personality/working style compatibility

Output JSON with:
- overall_score: 0-100
- research_alignment: 0-100
- skill_match: 0-100
- career_alignment: 0-100
- concerns: list of potential issues
- strengths: list of positive factors
- recommendation: "strongly_consider", "consider", "maybe", "not_recommended"
"""

GENERATE_EMAIL = """You are helping draft a cold email to a potential PhD advisor.
Write a professional, concise email that:

1. Introduces the sender briefly
2. Shows genuine interest in the professor's work
3. Mentions specific papers/research
4. Explains fit and what the applicant can contribute
5. Requests a brief conversation

Tone: Professional but personable. Length: ~200 words."""

RANK_PROFESSORS = """You are an academic matching algorithm. Given multiple professor profiles,
rank them based on the student's stated preferences.

Output JSON array with:
[
  {
    "professor_id": "...",
    "score": 0-100,
    "reasons": ["why this rank"],
    "match_areas": ["specific research matches"]
  }
]
"""

PAPER_QUALITY = """Evaluate the quality and impact of a research paper.
Consider:
- Novelty and originality
- Technical soundness
- Clarity of presentation
- Significance of results
- Reproducibility

Output JSON:
{
  "quality_score": 1-10,
  "impact_score": 1-10,
  "strengths": [...],
  "weaknesses": [...],
  "is_foundational": boolean
}"""

SUGGEST_QUESTIONS = """Generate thoughtful questions a prospective student could ask
during a meeting with this professor.

Questions should cover:
- Current research directions
- Lab culture and expectations
- Funding and resources
- Past student outcomes
- Work-life balance

Provide 5-7 specific, non-generic questions."""

ALL_PROMPTS = {
    "summarize_paper": SUMMARIZE_PAPER,
    "extract_themes": EXTRACT_THEMES,
    "profile_professor": PROFILE_PROFESSOR,
    "assess_fit": ASSESS_FIT,
    "generate_email": GENERATE_EMAIL,
    "rank_professors": RANK_PROFESSORS,
    "paper_quality": PAPER_QUALITY,
    "suggest_questions": SUGGEST_QUESTIONS,
}
