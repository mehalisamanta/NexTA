"""
utils/resume_analysis.py
Resume Quality Analysis — checks for career gaps, anomalies, concerns.

"""

import json
import streamlit as st
from backend.openai_client import create_openai_completion


class ResumeAnalyzer:
    def __init__(self, client):
        self.client = client

    def analyze_resume(self, resume_text: str, mask_pii_enabled: bool = False) -> dict:
        """
        Analyse resume for quality checks.
        Returns dict with career_gaps, technical_anomalies, fake_indicators, etc.
        """
        prompt = f"""Review the following resume for quality and completeness.

EVALUATION CHECKLIST:
1. PREVIOUS EMPLOYMENT: Did the candidate previously work at "NexTurn"?
2. EMPLOYMENT GAPS: Identify any gaps in employment history exceeding 6 months.
3. EXPERIENCE CONSISTENCY: Check if years of experience with specific technologies
   seem realistic (e.g., 10 years in a technology only 3 years old).
4. OVERLAPPING DATES: Identify overlapping employment dates or suspicious claims.
5. EXPERTISE AREAS: List primary areas of expertise and domain knowledge.
6. CONTACT INFORMATION: Check if phone number and email address are present.
   If either is missing, list them in missing_contact_info.

Resume Text:
{resume_text[:8000]}

Return ONLY a valid JSON object with this exact structure:
{{
    "is_previous_employee": false,
    "nexturn_history_details": "None or description if previously employed",
    "career_gaps": ["gap description 1", "gap description 2"],
    "technical_anomalies": ["anomaly description 1"],
    "fake_indicators": ["concern description 1"],
    "domain_knowledge": ["expertise area 1", "expertise area 2"],
    "missing_contact_info": [],
    "summary": "brief overall assessment"
}}

Use empty arrays for any category with no findings."""

        try:
            response = create_openai_completion(
                self.client,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume reviewer. Return only valid JSON with the exact structure requested.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=1500,
            )
            content    = response.choices[0].message.content.strip()
            json_start = content.find("{")
            json_end   = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except Exception as e:
            st.warning(f"Resume analysis error: {e}")

        return self._empty_result()

    def _empty_result(self) -> dict:
        return {
            "is_previous_employee":    False,
            "nexturn_history_details": "None",
            "career_gaps":             [],
            "technical_anomalies":     [],
            "fake_indicators":         [],
            "domain_knowledge":        [],
            "missing_contact_info":    [],
            "summary":                 "Analysis could not be completed",
        }