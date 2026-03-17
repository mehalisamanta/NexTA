"""
utils/template_mapper.py
Maps candidate data into the flat key format expected by ppt_generator.py.

"""


def map_to_template_format(parsed_data: dict) -> dict:
    if not parsed_data:
        return {}

    def _get(*keys, default=""):
        for k in keys:
            v = parsed_data.get(k)
            if v is not None and str(v).strip() not in ("", "null", "None"):
                return str(v).strip()
        return default

    # Skills 
    tech_stack = parsed_data.get("tech_stack", "")
    if isinstance(tech_stack, list):
        skills_str = ", ".join(tech_stack)
    else:
        skills_str = str(tech_stack)

    # Projects — read from key_projects list 
    projects = parsed_data.get("key_projects", [])

    def _get_proj(idx):
        if idx < len(projects) and isinstance(projects[idx], dict):
            return projects[idx]
        return {}

    def _format_responsibilities(proj: dict) -> str:
        resps = proj.get("responsibilities", [])
        if isinstance(resps, list):
            return "\n".join(f"• {r}" for r in resps if r)
        return str(resps) if resps else ""

    projects_map = {}
    for i in range(1, 5):
        proj = _get_proj(i - 1)
        projects_map[f"PROJECT{i}_NAME"]             = proj.get("title",       "")
        projects_map[f"PROJECT{i}_DURATION"]         = proj.get("duration",    "")
        projects_map[f"PROJECT{i}_ROLE"]             = proj.get("role",        "")
        projects_map[f"PROJECT{i}_DESCRIPTION"]      = proj.get("description", "")
        projects_map[f"PROJECT{i}_RESPONSIBILITIES"] = _format_responsibilities(proj)
        # Keep bullet list for Word doc use
        projects_map[f"project{i}_bullets"]          = proj.get("responsibilities", [])

    mapped = {
        "FULL_NAME":            _get("name", "NAME"),
        "CURRENT_ROLE":         _get("current_role", "ROLE"),
        "PROFESSIONAL_SUMMARY": _get("objective", "summary", "PROFESSIONAL_SUMMARY"),
        "EXPERIENCE_YEARS":     _get("experience_years"),
        "TECHNICAL_SKILLS":     skills_str,
        "EDUCATION_DETAILS":    _get("education", "EDUCATION_DETAILS"),
        "CERTIFICATIONS":       _get("certifications"),
        **projects_map,
    }

    return mapped