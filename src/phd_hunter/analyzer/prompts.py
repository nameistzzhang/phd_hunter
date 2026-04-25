"""Prompt templates for the Analyzer module (professor analysis + cold email)."""

from typing import Dict, List, Any


ANALYZER_SYSTEM_PROMPT = """You are an expert PhD application advisor with deep knowledge of computer science research and academic admissions worldwide.

Your task is to analyze a potential PhD advisor's profile and provide a comprehensive assessment plus a personalized cold email draft for the applicant.

## Analysis Guidelines

1. **Professor Analysis**: Study the professor's homepage summary, recent papers, and research interests to understand their current focus, lab direction, and research style.

2. **Match Assessment**: Compare the professor's work with the applicant's background (CV, personal statement, published papers, preferences) to identify genuine points of alignment.

3. **Cold Email Strategy**: Based on the match analysis, provide concrete advice on how to craft an effective cold email — what angles to emphasize, what to avoid, and how to stand out.

4. **Email Draft**: Write a complete, polished cold email that the applicant can send directly or adapt.

## Output Format

Respond in Markdown with the following sections (use ## headings):

## 1. Professor Overview
- Brief background (current position, lab, research focus)
- Recent research directions based on papers
- Any recruiting signals from homepage

## 2. Match Analysis
- Key alignment points between applicant and professor
- Strengths the applicant should highlight
- Potential gaps or concerns
- Overall fit assessment

## 3. Cold Email Strategy
- Recommended angle/theme for the email
- Specific points to mention
- Points to avoid or downplay
- Timing and follow-up suggestions

## 4. Cold Email Draft
A complete, ready-to-send email with:
- Professional subject line
- Proper greeting
- 3-4 concise paragraphs
- Specific connection to professor's work
- Clear call to action
- Professional closing

## Rules
- Be honest and specific — generic praise is useless
- Cite specific papers or projects when possible
- Keep the email draft under 300 words
- Do not invent facts not present in the provided materials
- Write in a professional but warm tone"""


def build_analyzer_initial_prompt(
    applicant_profile: Dict[str, Any],
    professor_data: Dict[str, Any],
) -> str:
    """Build the initial user prompt for analyzer first-time analysis.

    Args:
        applicant_profile: Dict with keys:
            - cv_text: str, extracted text from CV PDF
            - ps_text: str, extracted text from Personal Statement PDF
            - paper_abstracts: List[str], applicant's published paper abstracts/titles
            - preferences: str, applicant's stated preferences/research interests
        professor_data: Dict with keys:
            - name: str
            - university_name: str
            - university_rank: int
            - research_interests: List[str]
            - homepage_summary: str
            - papers: List[Dict], each with 'title', 'abstract', 'year', 'venue'
            - total_papers: int
            - recent_papers: int

    Returns:
        Formatted user prompt string
    """
    sections = ["=== APPLICANT PROFILE ===\n"]

    if applicant_profile.get("cv_text"):
        sections.append(f"**CV Extract:**\n{applicant_profile['cv_text'][:2000]}\n")

    if applicant_profile.get("ps_text"):
        sections.append(f"**Personal Statement Extract:**\n{applicant_profile['ps_text'][:1500]}\n")

    papers = applicant_profile.get("paper_abstracts", [])
    if papers:
        sections.append(f"**Applicant's Published Papers ({len(papers)} total):**")
        for i, abstract in enumerate(papers[:5], 1):
            sections.append(f"\nPaper {i}:\n{abstract[:1000]}")
        sections.append("")

    if applicant_profile.get("preferences"):
        sections.append(f"**Applicant Preferences / Research Interests:**\n{applicant_profile['preferences']}\n")

    sections.append("\n=== PROFESSOR PROFILE ===\n")
    sections.append(f"**Name:** {professor_data.get('name', 'Unknown')}")
    sections.append(f"**University:** {professor_data.get('university_name', 'Unknown')}")
    if professor_data.get("university_rank"):
        sections.append(f"**University Rank (CS):** #{professor_data['university_rank']}")

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
            sections.append(f"\n  [{i}] {title} ({year}, {venue})")
            if abstract:
                sections.append(f"  Abstract: {abstract[:600]}")

    sections.append("\n\n=== YOUR TASK ===")
    sections.append("Please provide a comprehensive analysis and a cold email draft following the format specified in your system instructions.")
    sections.append("Write your response in Markdown.")

    return "\n".join(sections)
