# utils/ppt_template_mapper.py

def map_to_ppt_format(candidate_data: dict) -> dict:
    """
    Standardizes raw candidate data (either from a parser or AI refiner)
    into the exact keys required by the PPT generator logic.
    """
    
    # Slide 1: Profile and Skills
    mapped_data = {
        "FULL_NAME": str(candidate_data.get("FULL_NAME", "")).strip().upper(),
        "CURRENT_ROLE": str(candidate_data.get("CURRENT_ROLE", "")),
        "PROFESSIONAL_SUMMARY": str(candidate_data.get("PROFESSIONAL_SUMMARY", "")),
        "EDUCATION_DETAILS": str(candidate_data.get("EDUCATION_DETAILS", "")),
        "TECHNICAL_SKILLS": str(candidate_data.get("TECHNICAL_SKILLS", "")),
    }

    # Slides 2-5: Project Details (Handled in a loop for 4 projects)
    for i in range(1, 5):
        # Text fields
        mapped_data[f"PROJECT{i}_NAME"] = candidate_data.get(f"PROJECT{i}_NAME", "")
        mapped_data[f"DURATION_PROJECT{i}"] = candidate_data.get(f"DURATION_PROJECT{i}", "")
        mapped_data[f"ROLE_PROJECT{i}"] = candidate_data.get(f"ROLE_PROJECT{i}", "")
        mapped_data[f"Project{i}_Description"] = candidate_data.get(f"Project{i}_Description", "")
        
        # Bullet points logic
        bullets = candidate_data.get(f"project{i}_bullets", [])
        
        # Ensure bullets is a list; if it's a string (common with some parsers), split it
        if isinstance(bullets, str):
            # Split by bullet symbol or newline if AI returned a string
            bullets = [b.strip() for b in bullets.split('\n') if b.strip()]
            
        mapped_data[f"project{i}_bullets"] = bullets

    return mapped_data

def get_ppt_refinement_schema():
    """
    Returns a sample structure that you can show the AI to ensure 
    it returns the correct JSON keys for this mapper.
    """
    return {
        "FULL_NAME": "",
        "CURRENT_ROLE": "",
        "PROFESSIONAL_SUMMARY": "Max 250 chars",
        "EDUCATION_DETAILS": "",
        "TECHNICAL_SKILLS": "Max 15 items",
        "PROJECT1_NAME": "",
        "DURATION_PROJECT1": "",
        "ROLE_PROJECT1": "",
        "Project1_Description": "Max 180 chars",
        "project1_bullets": ["Bullet 1", "Bullet 2", "Bullet 3"]
    }