"""
utils/preprocessing.py
Resume parsing — extract structured fields from raw resume text.

"""

import json
import re
import streamlit as st
from backend.openai_client import create_openai_completion
from utils.debug_log import debug_log


# Contact-info extractors

def _extract_email(text: str) -> str:
    """Extract first email address found in text."""
    match = re.search(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text or ""
    )
    return match.group(0).strip() if match else ""


def _extract_phone(text: str) -> str:
    """
    Extract first phone number found in text.
    Handles: +91-XXXXX-XXXXX, (XXX) XXX-XXXX, XXX.XXX.XXXX, 10-digit runs, etc.
    """
    patterns = [
        # International with country code
        r"\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{3,5}[\s\-.]?\d{3,5}(?:[\s\-.]?\d{1,5})?",
        # Parentheses style: (123) 456-7890
        r"\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}",
        # Indian mobile: 10 digits starting with 6-9
        r"(?<!\d)[6-9]\d{9}(?!\d)",
        # Generic: 7-15 digits possibly separated
        r"\b\d{3,5}[\s\-.]?\d{3,5}[\s\-.]?\d{3,5}\b",
    ]
    for pat in patterns:
        m = re.search(pat, text or "")
        if m:
            raw = m.group(0).strip()
            # Must have at least 7 actual digits
            if len(re.sub(r"\D", "", raw)) >= 7:
                return raw
    return ""

# Text helpers

def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _get_top_lines(text: str, n: int = 20) -> list:
    """Return up to n non-empty lines from the top of the resume."""
    lines = []
    for raw in (text or "").splitlines():
        ln = raw.strip()
        if not ln:
            continue
        # Strip common bullet characters
        ln = re.sub(r"^[\u2022\u25CF\u25AA\u25A0\-\*•►▪]+\s*", "", ln).strip()
        if ln:
            lines.append(ln)
        if len(lines) >= n:
            break
    return lines

# Name extraction

def _extract_name_heuristic(text: str) -> str:
    """
    Heuristically extract the candidate's full name from the top of the resume.

    Strategy (in order):
    1. Look for "Name:" label anywhere in first 15 lines
    2. Scan first 20 lines for a line that looks like a proper name
       (1–5 title-cased words, no digits, no special chars, not a section header)
    """
    top = _get_top_lines(text, n=20)

    # 1. Explicit label: "Name: John Doe" or "Full Name: ..."
    for ln in top[:15]:
        m = re.match(
            r"(?i)^(?:full\s+)?name\s*[:\-]\s*(.+)", ln
        )
        if m:
            cand = _norm_spaces(re.sub(r"[,;|/]+", " ", m.group(1)))
            parts = cand.split()
            if 1 <= len(parts) <= 5 and not re.search(r"\d", cand):
                return cand

    # 2. Scan top lines for a name-like line
    SKIP_RE = re.compile(
        r"(?i)(resume|curriculum|vitae|\bcv\b|email|phone|mobile|address|linkedin|"
        r"github|objective|summary|profile|experience|education|skills|"
        r"http|www\.|@|\d{4})"
    )
    for ln in top[:20]:
        if SKIP_RE.search(ln):
            continue
        # Remove common separators that sometimes appear inline
        cand = re.sub(r"[,;|/\\]+", " ", ln).strip()
        cand = _norm_spaces(cand)
        if len(cand) > 60:
            continue
        if re.search(r"\d", cand):
            continue
        # Allow letters, spaces, dots, hyphens, apostrophes (for names like O'Brien)
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]+", cand):
            continue
        parts = [p for p in cand.split() if p]
        if len(parts) < 1 or len(parts) > 5:
            continue
        # At least one part must start with uppercase
        if any(p[0].isupper() for p in parts if p):
            return cand

    return ""

# Experience extraction

def _extract_experience_years_heuristic(text: str) -> float:
    """
    Extract total years of experience.

    Looks for explicit statements first ("X years of experience"),
    then falls back to computing span from earliest to latest year found.
    """
    t = text or ""

    # 1. Explicit "N years" statements
    candidates = []
    for m in re.finditer(
        r"(?i)\b(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\b(?:\s+of\s+(?:total\s+)?(?:professional\s+)?experience)?",
        t,
    ):
        try:
            val = float(m.group(1))
            if 0.0 < val < 60.0:
                candidates.append(val)
        except Exception:
            continue

    if candidates:
        return max(candidates)

    # 2. Compute from year range in the document
    year_re = re.compile(r"\b(19[89]\d|20[0-2]\d)\b")
    years_found = [int(m.group()) for m in year_re.finditer(t)]
    if len(years_found) >= 2:
        span = max(years_found) - min(years_found)
        if 0 < span < 50:
            return float(span)

    return 0.0

# Section extraction helper

def _extract_section(text: str, header_regex: str, max_lines: int = 15) -> str:
    """
    Extract lines under a section header matched by header_regex.
    Stops at the next all-caps section header or after max_lines.
    """
    lines = (text or "").splitlines()
    header = re.compile(header_regex, re.I)
    # Pattern for detecting the start of the NEXT section header
    next_header_re = re.compile(
        r"^\s*(?:[A-Z][A-Z &/,\-]{3,}|"
        r"(?:work\s+)?experience|education|skills|technical\s+skills|"
        r"projects?|certifications?|achievements?|summary|objective|"
        r"employment|career|qualifications?)\s*[:\-]?\s*$",
        re.I,
    )
    out = []
    started = False

    for raw in lines:
        ln = raw.strip()
        if not started:
            if header.search(ln):
                started = True
                remainder = header.sub("", ln).strip(" :-|\t")
                if remainder:
                    out.append(remainder)
            continue
        if not ln:
            if out:
                # Allow one blank line inside the section
                continue
            continue
        # Stop at next section header
        if not out and next_header_re.match(ln):
            break
        if out and next_header_re.match(ln) and len(ln) <= 50:
            break
        out.append(ln)
        if len(out) >= max_lines:
            break

    return "\n".join(out).strip()

# Skills extraction

_SKILL_HEADERS = (
    r"(?:technical\s+)?skills?",
    r"tech(?:nical)?\s+stack",
    r"technologies",
    r"tools?\s+(?:and\s+)?technologies",
    r"core\s+competencies",
    r"programming\s+languages?",
    r"languages?\s+(?:and\s+)?(?:frameworks?|tools?)",
)

def _extract_skills_heuristic(text: str) -> str:
    """
    Extract skills from various formats:
    - "Skills: Python, Java, ..."  (inline)
    - Section block under Skills/Technologies/etc.
    - Fallback: look for comma-separated tech keywords
    """
    combined_header = r"^\s*(?:" + "|".join(_SKILL_HEADERS) + r")\s*[:\-]?\s*"

    # 1. Inline on same line as header
    for ln in (text or "").splitlines():
        m = re.match(combined_header, ln, re.I)
        if m:
            inline = ln[m.end():].strip()
            if len(inline) > 5:
                tokens = _tokenize_skills(inline)
                if tokens:
                    return ", ".join(tokens[:40])

    # 2. Section block
    skills_block = _extract_section(text, combined_header, max_lines=20)
    if skills_block:
        tokens = _tokenize_skills(skills_block)
        if tokens:
            return ", ".join(tokens[:40])

    # 3. Fallback: scan entire text for known tech keywords
    TECH_KEYWORDS = [
        "Python", "Java", "JavaScript", "TypeScript", "C\\+\\+", "C#", "Go",
        "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R\\b",
        "React", "Angular", "Vue", "Node\\.js", "Django", "Flask", "FastAPI",
        "Spring", "Express",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Kafka", "RabbitMQ", "Spark", "Hadoop",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Git", "Jenkins", "Ansible", "Prometheus", "Grafana",
        "Linux", "Bash",
    ]
    found = []
    for kw in TECH_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", text or "", re.I):
            # Use the canonical form from TECH_KEYWORDS
            found.append(re.sub(r"\\b|\\", "", kw))
    return ", ".join(found[:30]) if found else ""


def _tokenize_skills(raw: str) -> list:
    """Split a skills string/block into individual skill tokens."""
    # Replace common separators with commas
    raw = re.sub(r"[•\u2022\u25CF\u25AA\u25A0►▪|\n;/]+", ",", raw)
    tokens = []
    seen = set()
    for tok in raw.split(","):
        s = _norm_spaces(tok)
        # Remove leading/trailing punctuation
        s = re.sub(r"^[\s\-\*•:]+|[\s\-\*•:]+$", "", s)
        if not s or len(s) > 50:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(s)
    return tokens

# Education extraction

_DEGREE_RE = re.compile(
    r"(?i)\b(b\.?\s*tech|b\.?\s*e\.?|b\.?\s*sc\.?|b\.?\s*c\.?\s*a|"
    r"bachelor|m\.?\s*tech|m\.?\s*e\.?|m\.?\s*sc\.?|m\.?\s*c\.?\s*a|"
    r"master|m\.?\s*b\.?\s*a|ph\.?\s*d\.?|doctor|"
    r"b\.?\s*com|m\.?\s*com|"
    r"diploma|associate)\b"
)

def _extract_education_heuristic(text: str) -> str:
    """
    Extract highest education qualification.
    Tries section extraction first, then full-text degree search.
    """
    edu_header = (
        r"^\s*(?:education(?:al)?\s*(?:background|details|qualifications?)?|"
        r"academic(?:s|\s+background|\s+qualifications?)?|"
        r"qualifications?)\s*[:\-]?\s*$"
    )
    edu_block = _extract_section(text, edu_header, max_lines=12)

    if edu_block:
        for ln in edu_block.splitlines():
            if _DEGREE_RE.search(ln):
                return _norm_spaces(ln)
        # Return first non-empty line of the block
        first = edu_block.splitlines()[0].strip()
        if first:
            return _norm_spaces(first)

    # Full-text fallback: find ANY line with a degree keyword
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if _DEGREE_RE.search(ln) and len(ln) < 150:
            return _norm_spaces(ln)

    return ""

# Local (heuristic-only) parse — used as fallback

def parse_resume_locally(resume_text: str) -> dict:
    text = resume_text or ""
    return {
        "name":             _extract_name_heuristic(text),
        "email":            _extract_email(text),
        "phone":            _extract_phone(text),
        "experience_years": _extract_experience_years_heuristic(text),
        "tech_stack":       _extract_skills_heuristic(text),
        "education":        _extract_education_heuristic(text),
    }

# PII masking

def _mask_pii(text: str) -> str:
    text = re.sub(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "[EMAIL]", text
    )
    text = re.sub(r"(\+?\d[\d\s\-().]{7,}\d)", "[PHONE]", text)
    return text

# Helper: ensure value is non-empty / not a placeholder

def _is_empty(val) -> bool:
    if val is None:
        return True
    s = str(val).strip()
    return s in ("", "n/a", "N/A", "none", "None", "null", "nan",
                 "[EMAIL]", "[PHONE]", "Not found", "Not specified")


# Main public function

def parse_resume_with_openai(
    client,
    resume_text: str,
    filename: str,
    mask_pii: bool = True,
    upload_date: str = "",
) -> dict | None:
    """
    Parse a single resume into a structured dict using OpenAI gpt-4o-mini.

    Improvements over original:
    - Real contact info extracted BEFORE masking and restored afterwards
    - Local heuristic fill-in for ALL fields OpenAI may miss
    - key_projects always normalized to list of exactly 4 structured dicts
    - experience_years computed from heuristic if AI returns 0
    - tech_stack merged from AI + heuristic keyword scan to maximize coverage
    """

    # 1. Extract real PII before any masking 
    real_email = _extract_email(resume_text)
    real_phone = _extract_phone(resume_text)
    local      = parse_resume_locally(resume_text)

    # 2. Prepare text to send to AI 
    text_to_send = _mask_pii(resume_text) if mask_pii else resume_text

    # 3. Build prompt 
    prompt = f"""You are an expert resume parser. Extract the following fields from the resume below.
Return ONLY a valid JSON object. Do not include any markdown backticks, explanations, or preamble.

Fields to extract:
{{
  "name":             "Full Name of the candidate",
  "email":            "email address or empty string",
  "phone":            "phone number or empty string",
  "current_role":     "most recent job title",
  "experience_years": "total years of professional experience as a number e.g. 4.5",
  "tech_stack":       "comma-separated list of ALL technical skills, programming languages, tools, frameworks",
  "education":        "highest degree and institution e.g. B.Tech in Computer Science - XYZ University",
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

CRITICAL RULES:
- name: Extract the candidate's FULL NAME from the very top of the resume. It is usually the first prominent line.
- experience_years: Look for "X years of experience" statements, OR compute from the earliest to latest date found. Return a number only.
- tech_stack: Extract EVERY technical skill, tool, language, and framework mentioned anywhere in the resume. Separate with commas.
- education: Include degree type, field, and institution name.
- key_projects: Extract exactly 4 projects/jobs. If fewer than 4 exist, fill remaining entries with empty string fields.
- responsibilities must always be a LIST of strings, never a plain string.
- duration, role, title, description must always be strings.
- If a field is not found, use an empty string "".
- Do NOT fabricate any information.

Resume text:
{text_to_send[:6000]}"""

    # 4. Call OpenAI 
    try:
        resp = create_openai_completion(
            client,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise resume parser. "
                        "Return only valid JSON with no markdown or explanation."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1500,
        )
        raw     = resp.choices[0].message.content.strip()
        j_start = raw.find("{")
        j_end   = raw.rfind("}") + 1
        if j_start == -1 or j_end <= j_start:
            raise ValueError("No JSON object found in AI response")

        data = json.loads(raw[j_start:j_end])

    except Exception as e:
        st.warning(f"Could not parse {filename} with AI: {e}. Falling back to local extraction.")
        debug_log(
            location="utils/preprocessing.py:parse_resume_with_openai:ai_failed",
            message="AI parse failed, using local fallback",
            hypothesis_id="H1",
            data={"filename": filename, "error": repr(e)},
        )
        # Build a minimal dict from local extraction so we always return something
        data = {
            "name":             local.get("name", ""),
            "email":            real_email,
            "phone":            real_phone,
            "current_role":     "",
            "experience_years": local.get("experience_years", 0),
            "tech_stack":       local.get("tech_stack", ""),
            "education":        local.get("education", ""),
            "key_projects":     [],
            "certifications":   "",
            "objective":        "",
        }

    # 5. Normalize key_projects 
    if not isinstance(data.get("key_projects"), list):
        data["key_projects"] = []

    # Ensure exactly 4 project slots
    while len(data["key_projects"]) < 4:
        data["key_projects"].append({
            "title": "", "duration": "", "role": "",
            "description": "", "responsibilities": [],
        })

    for proj in data["key_projects"]:
        if not isinstance(proj, dict):
            proj = {"title": "", "duration": "", "role": "", "description": "", "responsibilities": []}
        # responsibilities must be a list of strings
        resps = proj.get("responsibilities", [])
        if isinstance(resps, str):
            # Split on newlines or semicolons
            proj["responsibilities"] = [
                r.strip() for r in re.split(r"[\n;]+", resps) if r.strip()
            ]
        elif isinstance(resps, list):
            proj["responsibilities"] = [str(r).strip() for r in resps if r]
        else:
            proj["responsibilities"] = []

    # 6. Restore real contact info (always override AI placeholders) 
    # AI sees [EMAIL] / [PHONE] when PII masking is on — always put the real values back
    if mask_pii or _is_empty(data.get("email")):
        data["email"] = real_email
    if mask_pii or _is_empty(data.get("phone")):
        data["phone"] = real_phone

    # If regex-based extraction also failed, try one more pass on unmasked text
    if _is_empty(data.get("email")):
        data["email"] = _extract_email(resume_text)
    if _is_empty(data.get("phone")):
        data["phone"] = _extract_phone(resume_text)

    # 7. Normalize experience_years 
    try:
        exp_val = float(str(data.get("experience_years", 0)).replace("+", "").strip() or 0)
    except (ValueError, TypeError):
        exp_val = 0.0

    if exp_val <= 0:
        exp_val = local.get("experience_years", 0.0) or 0.0

    data["experience_years"] = exp_val

    # 8. Fill missing core fields from local heuristic 
    fill_log = {}

    if _is_empty(data.get("name")) and (local.get("name") or "").strip():
        data["name"] = local["name"]
        fill_log["name"] = "local"

    if _is_empty(data.get("tech_stack")):
        if (local.get("tech_stack") or "").strip():
            data["tech_stack"] = local["tech_stack"]
            fill_log["tech_stack"] = "local"
    else:
        # Merge AI skills with keyword-scan skills to maximize coverage
        ai_skills   = set(s.strip().lower() for s in str(data["tech_stack"]).split(",") if s.strip())
        local_skills = [s.strip() for s in (local.get("tech_stack") or "").split(",") if s.strip()]
        extras = [s for s in local_skills if s.lower() not in ai_skills]
        if extras:
            merged = data["tech_stack"].rstrip(", ") + ", " + ", ".join(extras)
            data["tech_stack"] = merged
            fill_log["tech_stack_merge"] = len(extras)

    if _is_empty(data.get("education")):
        if (local.get("education") or "").strip():
            data["education"] = local["education"]
            fill_log["education"] = "local"

    if _is_empty(data.get("current_role")):
        # Try to derive current_role from first project's role field
        for proj in data["key_projects"]:
            if isinstance(proj, dict) and (proj.get("role") or "").strip():
                data["current_role"] = proj["role"].strip()
                fill_log["current_role"] = "from_project"
                break

    # 9. Log debug info 
    try:
        debug_log(
            location="utils/preprocessing.py:parse_resume_with_openai:complete",
            message="resume parse complete",
            hypothesis_id="H1",
            data={
                "filename": filename,
                "mask_pii": bool(mask_pii),
                "has_name":     not _is_empty(data.get("name")),
                "has_email":    not _is_empty(data.get("email")),
                "has_phone":    not _is_empty(data.get("phone")),
                "has_skills":   not _is_empty(data.get("tech_stack")),
                "has_education": not _is_empty(data.get("education")),
                "exp_years":    data.get("experience_years"),
                "projects_filled": sum(
                    1 for p in data["key_projects"]
                    if isinstance(p, dict) and (p.get("title") or "").strip()
                ),
                "fill_log": fill_log,
            },
        )
    except Exception:
        pass

    # 10. Final metadata 
    data["submission_date"] = upload_date
    data["source_file"]     = filename
    return data