import io
import os
import re
import streamlit as st
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE
from utils.ppt_template_mapper import map_to_ppt_format

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates", "sample_ppt_template.pptx"
)

RED = RGBColor(0xFF, 0x00, 0x00)
BLACK = RGBColor(0x00, 0x00, 0x00)

def _enable_autofit(shape):
    if shape.has_text_frame:
        tf = shape.text_frame
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.word_wrap = True

def _set_run_text(run, text, missing=False):
    run.text = text if text else "Information Missing"
    run.font.color.rgb = RED if (missing or not text) else BLACK
    run.font.bold = True if (missing or not text) else False

def _safe_write(para, text, missing=False):
    if not para.runs: para.add_run()
    _set_run_text(para.runs[0], text, missing)
    for r in para.runs[1:]:
        r._r.getparent().remove(r._r)

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
    # Mapping for both text and bullet points
    p_map = {
        f"{{PROJECT{proj_num}_NAME}}": d.get(f"PROJECT{proj_num}_NAME", ""),
        f"{{DURATION_PROJECT{proj_num}}}": d.get(f"DURATION_PROJECT{proj_num}", ""),
        f"{{ROLE_PROJECT{proj_num}}}": d.get(f"ROLE_PROJECT{proj_num}", ""),
        f"{{Project{proj_num}_Description}}": d.get(f"Project{proj_num}_Description", ""),
        f"{{Responsibilities_Project{proj_num}}}": d.get(f"project{proj_num}_bullets", []),
        f"{{Responsibilities_project{proj_num}}}": d.get(f"project{proj_num}_bullets", [])
    }

    for shape in slide.shapes:
        if not shape.has_text_frame: continue
        _enable_autofit(shape)
        for para in list(shape.text_frame.paragraphs):
            full_text = "".join(run.text for run in para.runs)
            for placeholder, value in p_map.items():
                if placeholder.lower() in full_text.lower():
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

def generate_candidate_ppt(candidate_data: dict):
    try:
        if not os.path.exists(TEMPLATE_PATH):
            return None
        
        prs = Presentation(TEMPLATE_PATH)
        
        # FIX: Ensure this matches the function name imported from your mapper
        d = map_to_ppt_format(candidate_data) 

        if len(prs.slides) >= 1:
            _populate_slide1(prs.slides[0], d)
            
        for i in range(1, min(5, len(prs.slides))):
            _populate_project_slide(prs.slides[i], i, d)

        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"Error generating PPT: {e}")
        return None