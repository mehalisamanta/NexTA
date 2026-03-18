"""
utils/template_mapper.py
Maps candidate data into the flat key format expected by ppt_generator.py.

"""


def _is_empty(val) -> bool:
    """Return True if val is effectively absent / a placeholder."""
    if val is None:
        return True
    s = str(val).strip()
    return s in ("", "null", "None", "N/A", "n/a", "nan", "None", "Information Missing")


def map_to_template_format(parsed_data: dict) -> dict:
    if not parsed_data:
        return {}

    # Helpers 

    def _get(*keys, default=""):
        """Return the first non-empty value found under any of the given keys."""
        for k in keys:
            v = parsed_data.get(k)
            if not _is_empty(v):
                return str(v).strip()
        return default

    def _join_nonempty(*vals) -> str:
        out = []
        for v in vals:
            s = str(v or "").strip()
            if not _is_empty(s):
                out.append(s)
        return " | ".join(out)

    # Skills 
    tech_stack = parsed_data.get("tech_stack", "")
    if isinstance(tech_stack, list):
        skills_str = ", ".join(str(s) for s in tech_stack if s)
    else:
        skills_str = str(tech_stack or "")

    # Education — try every possible key combination 
    education_details = _get(
        "education",
        "EDUCATION_DETAILS",
        "HIGHEST_EDUCATION",
        default="",
    )
    if _is_empty(education_details):
        # Try joining degree + college + dates
        parts = [
            _get("HIGHEST_EDUCATION", default=""),
            _get("COLLEGE_NAME",      default=""),
            _get("EDUCATION_DATES",   default=""),
        ]
        education_details = _join_nonempty(*parts)

    # Determine which project shape is available 
    projects = parsed_data.get("key_projects")

    # Check whether the key_projects list has usable content
    using_key_projects = (
        isinstance(projects, list)
        and len(projects) > 0
        and any(
            isinstance(p, dict)
            and not _is_empty(p.get("title"))
            for p in projects
        )
    )

    # Build project placeholders 

    def _get_proj(idx: int) -> dict:
        """Safely get a project dict from the key_projects list."""
        if projects and idx < len(projects) and isinstance(projects[idx], dict):
            return projects[idx]
        return {}

    def _format_responsibilities(proj: dict) -> str:
        resps = proj.get("responsibilities", [])
        if isinstance(resps, list):
            return "\n".join(f"• {r}" for r in resps if r)
        if isinstance(resps, str) and resps.strip():
            return resps.strip()
        return ""

    def _bullets_list(proj: dict) -> list:
        resps = proj.get("responsibilities", [])
        if isinstance(resps, list):
            return [str(r) for r in resps if r]
        return []

    projects_map = {}

    for i in range(1, 5):
        if using_key_projects:
            # Shape A: key_projects list 
            proj = _get_proj(i - 1)

            # Duration: prefer explicit "duration" field; fall back to
            # START_DATE / END_DATE for project 1
            duration = str(proj.get("duration", "") or "").strip()
            if _is_empty(duration) and i == 1:
                start = _get("START_DATE", default="")
                end   = _get("END_DATE",   default="")
                if start or end:
                    duration = f"{start} – {end}".strip(" –")

            # Role: prefer explicit "role" field; fall back to ROLE / current_role
            role_str = str(proj.get("role", "") or "").strip()
            if _is_empty(role_str) and i == 1:
                role_str = _get("ROLE", "current_role", "CURRENT_ROLE", default="")

            # Title
            title = str(proj.get("title", "") or "").strip()
            if _is_empty(title) and i == 1:
                title = _get("PROJECT1_NAME", "COMPANY_NAME", default="")

            # Description
            desc = str(proj.get("description", "") or "").strip()

            projects_map[f"PROJECT{i}_NAME"]             = title
            projects_map[f"PROJECT{i}_DURATION"]         = duration
            projects_map[f"PROJECT{i}_ROLE"]             = role_str
            projects_map[f"PROJECT{i}_DESCRIPTION"]      = desc
            projects_map[f"PROJECT{i}_RESPONSIBILITIES"] = _format_responsibilities(proj)
            projects_map[f"project{i}_bullets"]          = _bullets_list(proj)

        else:
            # Shape B: flat PROJECT{n}_* keys (legacy / Word-template shape)
            # Determine which bullet key prefix to use
            if i == 1:
                bullet_prefix = "ABOUT_PROJECT_BULLET_"
                bullet_range  = range(1, 7)
            else:
                bullet_prefix = f"PROJECT{i}_BULLET_"
                bullet_range  = range(1, 6)

            bullets_raw = [
                _get(f"{bullet_prefix}{b}", default="")
                for b in bullet_range
            ]
            bullets_clean = [b for b in bullets_raw if not _is_empty(b)]

            resp_text = "\n".join(f"• {b}" for b in bullets_clean) if bullets_clean else ""

            projects_map[f"PROJECT{i}_NAME"]             = _get(f"PROJECT{i}_NAME", default="")
            projects_map[f"PROJECT{i}_DURATION"]         = _get(f"PROJECT{i}_DURATION", default="")
            projects_map[f"PROJECT{i}_ROLE"]             = _get(f"PROJECT{i}_ROLE", default="")
            projects_map[f"PROJECT{i}_DESCRIPTION"]      = _get(f"PROJECT{i}_DESCRIPTION", default="")
            projects_map[f"PROJECT{i}_RESPONSIBILITIES"] = resp_text
            projects_map[f"project{i}_bullets"]          = bullets_clean

    # Assemble final mapped dict 
    mapped = {
        "FULL_NAME":            _get("name", "NAME", "FULL_NAME"),
        "CURRENT_ROLE":         _get("current_role", "ROLE", "CURRENT_ROLE"),
        "PROFESSIONAL_SUMMARY": _get("objective", "summary", "PROFESSIONAL_SUMMARY"),
        "EXPERIENCE_YEARS":     _get("experience_years", "EXPERIENCE_YEARS"),
        "TECHNICAL_SKILLS":     skills_str if skills_str else _get("tech_stack", "TECHNICAL_SKILLS"),
        "EDUCATION_DETAILS":    education_details,
        "CERTIFICATIONS":       _get("certifications", "CERTIFICATIONS"),
        **projects_map,
    }

    return mapped