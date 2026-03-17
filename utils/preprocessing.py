"""
utils/preprocessing.py
Resume parsing — extract structured fields from raw resume text.

"""

import json
import re
import streamlit as st
from backend.openai_client import create_openai_completion


def _extract_email(text: str) -> str:
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return match.group(0).strip() if match else ""


def _extract_phone(text: str) -> str:
    match = re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text)
    return match.group(0).strip() if match else ""


def _mask_pii(text: str) -> str:
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

    key_projects is a list of exactly 4 structured dicts:
      [{"title": "", "duration": "", "role": "", "description": "",
        "responsibilities": ["bullet 1", "bullet 2"]}, ...]
    """
    real_email = _extract_email(resume_text)
    real_phone = _extract_phone(resume_text)

    if mask_pii:
        text_to_send = _mask_pii(resume_text)
    else:
        text_to_send = resume_text

    prompt = f"""You are an expert resume parser. Extract the following fields from the resume below.
Return ONLY a valid JSON object. Do not include any markdown backticks, explanations, or preamble.

Fields to extract:
{{
  "name":             "Full Name",
  "email":            "email address or empty string",
  "phone":            "phone number or empty string",
  "current_role":     "most recent job title",
  "experience_years": "total years of professional experience as a number e.g. 4.5",
  "tech_stack":       "comma-separated list of technical skills",
  "education":        "highest degree and institution",
  "key_projects": [
    {{
      "title":            "Project or Company Name",
      "duration":         "Duration or Dates e.g. Jan 2022 - Present",
      "role":             "Job title or role on this project",
      "description":      "Short project summary (1-2 sentences)",
      "responsibilities": ["bullet point 1", "bullet point 2", "bullet point 3"]
    }}
  ],
  "certifications": "any certifications or empty string",
  "objective":      "professional summary or objective statement"
}}

RULES:
- Extract exactly 4 projects. If fewer than 4 exist, fill remaining with empty string fields.
- responsibilities must be a list of strings, never a plain string.
- duration, role, title, description must be strings.
- If a field is not found, use an empty string.
- Do not fabricate information.

Resume text:
{text_to_send[:6000]}"""

    try:
        resp = create_openai_completion(
            client,
            messages=[
                {"role": "system", "content": "You are a precise resume parser. Return only valid JSON."},
                {"role": "user",   "content": prompt},
            ],
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1200,
        )
        raw     = resp.choices[0].message.content.strip()
        j_start = raw.find("{")
        j_end   = raw.rfind("}") + 1
        if j_start == -1 or j_end <= j_start:
            return None

        data = json.loads(raw[j_start:j_end])

        # Ensure key_projects is always a list of exactly 4 items
        if not isinstance(data.get("key_projects"), list):
            data["key_projects"] = []
        while len(data["key_projects"]) < 4:
            data["key_projects"].append(
                {"title": "", "duration": "", "role": "", "description": "", "responsibilities": []}
            )
        for proj in data["key_projects"]:
            if not isinstance(proj.get("responsibilities"), list):
                proj["responsibilities"] = []

        # Restore real contact details
        if mask_pii:
            data["email"] = real_email
            data["phone"] = real_phone

        try:
            data["experience_years"] = float(
                str(data.get("experience_years", 0)).replace("+", "")
            )
        except (ValueError, TypeError):
            data["experience_years"] = 0.0

        data["submission_date"] = upload_date
        data["source_file"]     = filename
        return data

    except Exception as e:
        st.warning(f"Could not parse {filename}: {e}")
        return None