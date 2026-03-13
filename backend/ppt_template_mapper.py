# backend/ppt_template_mapper.py

def map_to_ppt_format(candidate_data: dict) -> dict:
    """
    Standardizes raw candidate data into the exact keys used by 
    the PPT generator functions.
    """
    mapped_data = {
        "FULL_NAME": candidate_data.get("FULL_NAME", ""),
        "CURRENT_ROLE": candidate_data.get("CURRENT_ROLE", ""),
        "PROFESSIONAL_SUMMARY": candidate_data.get("PROFESSIONAL_SUMMARY", ""),
        "EDUCATION_DETAILS": candidate_data.get("EDUCATION_DETAILS", ""),
        "TECHNICAL_SKILLS": candidate_data.get("TECHNICAL_SKILLS", ""),
    }

    for i in range(1, 5):
        mapped_data[f"PROJECT{i}_NAME"] = candidate_data.get(f"PROJECT{i}_NAME", "")
        mapped_data[f"DURATION_PROJECT{i}"] = candidate_data.get(f"DURATION_PROJECT{i}", "")
        mapped_data[f"ROLE_PROJECT{i}"] = candidate_data.get(f"ROLE_PROJECT{i}", "")
        mapped_data[f"Project{i}_Description"] = candidate_data.get(f"Project{i}_Description", "")
        mapped_data[f"project{i}_bullets"] = candidate_data.get(f"project{i}_bullets", [])

    return mapped_data