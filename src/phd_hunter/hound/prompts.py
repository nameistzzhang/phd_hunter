"""Prompt templates for hound LLM agents."""

from typing import Dict, List, Any


SCORER_SYSTEM_PROMPT = """You are an expert PhD application advisor with deep knowledge of computer science research areas and academic admissions.

Your task is to evaluate the fit between a PhD applicant's profile and a potential advisor's research, then provide two scores on a 5-point scale:

1. **Direction Match (1-5)**: How well does the applicant's research background, interests, and published work align with the professor's research direction?
   - 5: Perfect alignment — the applicant has published in this exact area and their stated interests directly match the professor's work
   - 4: Strong alignment — significant overlap in methodology or application domain
   - 3: Moderate alignment — some overlapping interests but gaps exist
   - 2: Weak alignment — tangential connection, would require significant pivot
   - 1: Poor alignment — little to no overlap in research interests

2. **Admission Difficulty (1-5)**: How difficult would it be for THIS specific applicant to get admitted to work with THIS professor?
   - 5: Very difficult — top-tier school + highly competitive professor, applicant's background may be insufficient
   - 4: Difficult — strong school or competitive professor, applicant needs to stand out
   - 3: Moderate — reasonable match of applicant quality vs. program competitiveness
   - 2: Achievable — applicant's background exceeds typical requirements
   - 1: High likelihood — safety school or professor actively recruiting in this area

Consider:
- Applicant's research publications (quality, venue, relevance)
- Applicant's stated research interests and career goals
- Professor's research output (volume, recency, citations)
- University ranking and program competitiveness
- Whether the professor's work directly builds on or extends the applicant's existing research

Respond ONLY with a valid JSON object in this exact format:
{
  "direction_match": <int 1-5>,
  "admission_difficulty": <int 1-5>,
  "reasoning": "<brief explanation of your assessment>"
}

Be honest and critical in your assessment. Do not inflate scores to be nice."""


HOMEPAGE_EXTRACTION_PROMPT = """Below is the extracted text from the homepage of Professor {professor_name}. Please extract the following information and return ONLY a valid JSON object:

Extracted homepage text:
---
{homepage_text}
---

Please return a JSON object with these exact keys:
{{
  "email": "professor's email if found, otherwise empty string",
  "research_focus": "concise description of their current research focus (50 words max)",
  "recruiting_status": "one of: accepting / not_accepting / unknown",
  "summary": "brief summary of the professor's research interests, recent projects, and lab direction (200 words max)"
}}

Rules:
- If no email is visible, use empty string ""
- recruiting_status: use "accepting" only if the page explicitly mentions recruiting PhD students, hiring, or open positions
- Be concise and factual. Do not hallucinate information not present in the text."""


def build_scorer_user_prompt(
    applicant_profile: Dict[str, Any],
    professor_data: Dict[str, Any],
) -> str:
    """Build the user prompt for scoring a single professor.

    Args:
        applicant_profile: Dict with keys:
            - cv_text: str, extracted text from CV PDF
            - ps_text: str, extracted text from Personal Statement PDF
            - paper_abstracts: List[str], applicant's published paper abstracts
            - preferences: str, applicant's stated preferences/research interests
        professor_data: Dict with keys:
            - name: str
            - university_name: str
            - university_rank: int
            - research_interests: List[str]
            - papers: List[Dict], each with 'title', 'abstract', 'year', 'venue', 'citation_count'
            - total_papers: int
            - recent_papers: int

    Returns:
        Formatted user prompt string
    """
    # Build applicant section
    sections = ["=== APPLICANT PROFILE ===\n"]

    if applicant_profile.get("cv_text"):
        sections.append(f"**CV Extract:**\n{applicant_profile['cv_text'][:2000]}\n")

    if applicant_profile.get("ps_text"):
        sections.append(f"**Personal Statement Extract:**\n{applicant_profile['ps_text'][:1500]}\n")

    papers = applicant_profile.get("paper_abstracts", [])
    if papers:
        sections.append(f"**Applicant's Published Papers ({len(papers)} total):**")
        for i, abstract in enumerate(papers[:3], 1):
            sections.append(f"\nPaper {i} Abstract:\n{abstract[:800]}")
        sections.append("")

    if applicant_profile.get("preferences"):
        sections.append(f"**Applicant Preferences:**\n{applicant_profile['preferences']}\n")

    # Build professor section
    sections.append("\n=== PROFESSOR PROFILE ===\n")
    sections.append(f"**Name:** {professor_data.get('name', 'Unknown')}")
    sections.append(f"**University:** {professor_data.get('university_name', 'Unknown')}")
    sections.append(f"**University Rank (CS):** {professor_data.get('university_rank', 'N/A')}")
    sections.append(f"**Total Papers:** {professor_data.get('total_papers', 0)}")
    sections.append(f"**Recent Papers (2024+):** {professor_data.get('recent_papers', 0)}")

    interests = professor_data.get("research_interests", [])
    if interests:
        sections.append(f"**Research Interests:** {', '.join(interests)}")

    homepage_summary = professor_data.get("homepage_summary", "")
    if homepage_summary:
        sections.append(f"\n**Homepage Summary:**\n{homepage_summary}\n")

    prof_papers = professor_data.get("papers", [])
    if prof_papers:
        sections.append(f"\n**Professor's Recent Papers ({min(len(prof_papers), 5)} shown):**")
        for i, paper in enumerate(prof_papers[:5], 1):
            title = paper.get("title", "Untitled")
            abstract = paper.get("abstract", "")
            year = paper.get("year", "N/A")
            venue = paper.get("venue", "N/A")
            citations = paper.get("citation_count", 0)
            sections.append(f"\n  [{i}] {title} ({year}, {venue}, {citations} citations)")
            if abstract:
                sections.append(f"  Abstract: {abstract[:500]}")

    sections.append("\n\n=== YOUR TASK ===")
    sections.append("Evaluate the fit between this applicant and professor.")
    sections.append("Return ONLY the JSON object with direction_match, admission_difficulty, and reasoning.")

    return "\n".join(sections)
