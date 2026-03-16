def map_to_ppt_format(candidate_data: dict) -> dict:
    mapped = {
        "FULL_NAME": candidate_data.get("name", "Information Missing"),
        "CURRENT_ROLE": candidate_data.get("current_role", "Information Missing"),
        "PROFESSIONAL_SUMMARY": candidate_data.get("objective", "Information Missing"),
        "EDUCATION_DETAILS": candidate_data.get("education", "Information Missing"),
        "TECHNICAL_SKILLS": candidate_data.get("tech_stack", "Information Missing"),
    }

    projects = candidate_data.get("key_projects", [])

    # Helper function to safely fetch project
    def get_project(idx):
        if idx < len(projects):
            return projects[idx]
        return {}

    # Helper to convert responsibilities list into bullet string
    def format_responsibilities(resps):
        if isinstance(resps, list):
            return "\n".join(f"• {r}" for r in resps)
        return resps if resps else ""

    # PROJECT 1
    p1 = get_project(0)
    mapped["PROJECT1_NAME"] = p1.get("title", "")
    mapped["PROJECT1_DURATION"] = p1.get("duration", "")
    mapped["PROJECT1_ROLE"] = p1.get("role", "")
    mapped["PROJECT1_DESCRIPTION"] = p1.get("description", "")
    mapped["PROJECT1_RESPONSIBILITIES"] = format_responsibilities(
        p1.get("responsibilities", [])
    )

    # PROJECT 2
    p2 = get_project(1)
    mapped["PROJECT2_NAME"] = p2.get("title", "")
    mapped["PROJECT2_DURATION"] = p2.get("duration", "")
    mapped["PROJECT2_ROLE"] = p2.get("role", "")
    mapped["PROJECT2_DESCRIPTION"] = p2.get("description", "")
    mapped["PROJECT2_RESPONSIBILITIES"] = format_responsibilities(
        p2.get("responsibilities", [])
    )

    # PROJECT 3
    p3 = get_project(2)
    mapped["PROJECT3_NAME"] = p3.get("title", "")
    mapped["PROJECT3_DURATION"] = p3.get("duration", "")
    mapped["PROJECT3_ROLE"] = p3.get("role", "")
    mapped["PROJECT3_DESCRIPTION"] = p3.get("description", "")
    mapped["PROJECT3_RESPONSIBILITIES"] = format_responsibilities(
        p3.get("responsibilities", [])
    )

    # PROJECT 4
    p4 = get_project(3)
    mapped["PROJECT4_NAME"] = p4.get("title", "")
    mapped["PROJECT4_DURATION"] = p4.get("duration", "")
    mapped["PROJECT4_ROLE"] = p4.get("role", "")
    mapped["PROJECT4_DESCRIPTION"] = p4.get("description", "")
    mapped["PROJECT4_RESPONSIBILITIES"] = format_responsibilities(
        p4.get("responsibilities", [])
    )

    return mapped