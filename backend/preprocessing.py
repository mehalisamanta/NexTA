"""
backend/preprocessing.py
Resume parsing — extract structured fields from raw resume text.

"""

import json
import re
import streamlit as st
from backend.openai_client import create_openai_completion


def _mask_pii(text: str) -> str:
    """Redact email addresses and phone numbers before sending to AI."""
    text = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[EMAIL]", text)
    text = re.sub(r"(\+?\d[\d\s\-().]{7,}\d)", "[PHONE]", text)
    return text


def parse_resume_with_openai(
    client,
    resume_text: str,
    filename: str,
    mask_pii: bool = True,
    upload_date: str = "",
) -> dict | None:
    """
    Parse a single resume into a structured dict using OpenAI gpt-4o-mini.

    Returns a dict with keys:
        name, email, phone, current_role, experience_years,
        tech_stack, education, key_projects, certifications,
        objective, submission_date, source_file
    Returns None if parsing fails.
    """
    if mask_pii:
        text_to_send = _mask_pii(resume_text)
    else:
        text_to_send = resume_text

    prompt = f"""You are an expert resume parser. Extract the following fields from the resume below.
Return ONLY a JSON object — no markdown, no explanation, no preamble.

Fields to extract:
{{
  "name":             "Full Name",
  "email":            "email address or empty string",
  "phone":            "phone number or empty string",
  "current_role":     "most recent job title",
  "experience_years": "total years of professional experience as a number e.g. 4.5",
  "tech_stack":       "comma-separated list of technical skills",
  "education":        "highest degree and institution",
  "key_projects":     "brief description of 1-3 key projects",
  "certifications":   "any certifications or empty string",
  "objective":        "professional summary or objective statement"
}}

RULES:
- experience_years must be a number (float or int). If not stated, estimate from work history.
- tech_stack must be a comma-separated string, not a list.
- If a field is not found, use an empty string.
- Do not fabricate information.

Resume text:
{text_to_send[:6000]}"""

    try:
        resp = create_openai_completion(
            client,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise resume parser. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=800,
        )
        raw     = resp.choices[0].message.content.strip()
        j_start = raw.find("{")
        j_end   = raw.rfind("}") + 1
        if j_start == -1 or j_end <= j_start:
            return None

        data = json.loads(raw[j_start:j_end])

        # Ensure experience_years is a number
        try:
            data["experience_years"] = float(str(data.get("experience_years", 0)).replace("+", ""))
        except (ValueError, TypeError):
            data["experience_years"] = 0.0

        # Add metadata fields
        data["submission_date"] = upload_date
        data["source_file"]     = filename
        return data

    except Exception as e:
        st.warning(f"Could not parse {filename}: {e}")
        return None