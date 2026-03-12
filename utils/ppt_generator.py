import io
import os
import re
import json
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Pt

# Configuration
TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates", "sample_ppt_template.pptx"
)

RED = RGBColor(0xFF, 0x00, 0x00)
BLACK = RGBColor(0x00, 0x00, 0x00)

# ---------------------------------------------------------
# AI Content Refinement Logic
# ---------------------------------------------------------

def refine_content_with_ai(client, raw_data: dict) -> dict:
    """
    Uses AI to compress and summarize the extracted resume data 
    specifically for the physical boundaries of the PPT slides.
    """
    prompt = f"""
    You are a professional document editor. Rewrite the following resume data to fit 
    into a PowerPoint template without overflowing textboxes.

    CONSTRAINTS:
    - PROFESSIONAL_SUMMARY: Max 250 characters.
    - Project_Description: Max 180 characters per project.
    - project_bullets: Exactly 3 high-impact technical bullet points per project.
    - TECHNICAL_SKILLS: Max 15 key technologies/tools.

    RAW DATA:
    {json.dumps(raw_data)}

    Return ONLY a JSON object that matches the structure of the input data.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # gpt-4o is better at following length constraints
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Refinement Error: {e}")
        return raw_data # Fallback to raw data if AI fails

# ---------------------------------------------------------
# Helpers & Formatting
# ---------------------------------------------------------

def _enable_autofit(shape):
    if shape.has_text_frame:
        tf = shape.text_frame
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.word_wrap = True

def _safe_write(para, text, missing=False):
    """Writes text and applies dynamic font scaling based on content length."""
    if not para.runs:
        para.add_run()
    
    run = para.runs[0]
    content = text if text else "Information Missing"
    run.text = content
    
    # Dynamic Font Scaling (The Safety Valve)
    if len(content) > 200:
        run.font.size = Pt(9)   # Very long text
    elif len(content) > 120:
        run.font.size = Pt(10)  # Moderate text
    else:
        run.font.size = Pt(11)  # Standard

    run.font.color.rgb = RED if (missing or not text) else BLACK
    run.font.bold = True if (missing or not text) else False

    # Remove fragmented runs often created by PPT templates
    for r in para.runs[1:]:
        r._r.getparent().remove(r._r)

# ---------------------------------------------------------
# Slide Population Logic
# ---------------------------------------------------------

def _populate_slide1(slide, d):
    mapping = {
        "{FULL_NAME}": d.get("FULL_NAME", ""),
        "{CURRENT_ROLE}": d.get("CURRENT_ROLE", ""),
        "{PROFESSIONAL_SUMMARY}": d.get("PROFESSIONAL_SUMMARY", ""),
        "{EDUCATION_DETAILS}": d.get("EDUCATION_DETAILS", ""),
        "{TECHNICAL_SKILLS}": d.get("TECHNICAL_SKILLS", "")
    }

    for shape in slide.shapes:
        if not shape.has_text_frame: continue
        _enable_autofit(shape)
        
        for para in shape.text_frame.paragraphs:
            full_text = "".join(run.text for run in para.runs)
            for placeholder, value in mapping.items():
                if placeholder in full_text:
                    new_text = full_text.replace(placeholder, value if value else "")
                    _safe_write(para, new_text, missing=not value)
                    full_text = new_text

def _populate_project_slide(slide, proj_num, d):
    # Mapping for project tags with case-insensitive support
    p_map = {
        f"{{project{proj_num}_name}}": d.get(f"PROJECT{proj_num}_NAME", ""),
        f"{{duration_project{proj_num}}}": d.get(f"DURATION_PROJECT{proj_num}", ""),
        f"{{role_project{proj_num}}}": d.get(f"ROLE_PROJECT{proj_num}", ""),
        f"{{project{proj_num}_description}}": d.get(f"Project{proj_num}_Description", ""),
        f"{{responsibilities_project{proj_num}}}": d.get(f"project{proj_num}_bullets", [])
    }

    for shape in slide.shapes:
        if not shape.has_text_frame: continue
        _enable_autofit(shape)

        for para in list(shape.text_frame.paragraphs):
            full_text = "".join(run.text for run in para.runs)
            lower_text = full_text.lower()

            for placeholder, value in p_map.items():
                if placeholder in lower_text:
                    if isinstance(value, list):
                        if value:
                            _safe_write(para, value[0])
                            for bullet in value[1:]:
                                new_p = shape.text_frame.add_paragraph()
                                new_p.text = bullet
                                new_p.level = para.level
                        else:
                            _safe_write(para, "Information Missing", missing=True)
                    else:
                        pattern = re.compile(re.escape(placeholder), re.IGNORECASE)
                        new_text = pattern.sub(str(value) if value else "", full_text)
                        _safe_write(para, new_text, missing=not value)
                        full_text = new_text

# ---------------------------------------------------------
# Entry Point
# ---------------------------------------------------------

def generate_candidate_ppt(candidate_data: dict, openai_client=None):
    """
    Main entry point. If openai_client is provided, it refines content 
    before generation to prevent overflow.
    """
    try:
        if not os.path.exists(TEMPLATE_PATH):
            print(f"Template not found at {TEMPLATE_PATH}")
            return None
        
        # 1. AI Integration: Refine text if a client is available
        if openai_client:
            candidate_data = refine_content_with_ai(openai_client, candidate_data)

        # 2. Map data to template keys
        d = map_to_ppt_format(candidate_data) 
        
        # 3. Process Slides
        prs = Presentation(TEMPLATE_PATH)
        if len(prs.slides) >= 1:
            _populate_slide1(prs.slides[0], d)
            
        for i in range(1, min(5, len(prs.slides))):
            _populate_project_slide(prs.slides[i], i, d)

        # 4. Save to buffer
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"Error generating PPT: {e}")
        return None