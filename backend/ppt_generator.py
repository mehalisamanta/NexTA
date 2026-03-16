import io
import os
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE

from backend.ppt_template_mapper import map_to_ppt_format


TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "inputs",
    "sample_ppt_template.pptx"
)

RED = RGBColor(0xFF, 0x00, 0x00)
BLACK = RGBColor(0x00, 0x00, 0x00)


def _enable_autofit(shape):
    """Enable auto-fit so text shrinks to fit the text box."""
    if shape.has_text_frame:
        tf = shape.text_frame
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.word_wrap = True

        for para in tf.paragraphs:
            for run in para.runs:
                if run.font.size is None:
                    run.font.size = Pt(12)


def _apply_missing_style(paragraph):
    """Apply red bold styling for missing information."""
    for run in paragraph.runs:
        run.font.color.rgb = RED
        run.font.bold = True


def _populate_slide1(slide, d):
    mapping = {
        "{FULL_NAME}": d.get("FULL_NAME", ""),
        "{CURRENT_ROLE}": d.get("CURRENT_ROLE", ""),
        "{PROFESSIONAL_SUMMARY}": d.get("PROFESSIONAL_SUMMARY", ""),
        "{EDUCATION_DETAILS}": d.get("EDUCATION_DETAILS", ""),
        "{TECHNICAL_SKILLS}": d.get("TECHNICAL_SKILLS", "")
    }

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue

        _enable_autofit(shape)

        for para in shape.text_frame.paragraphs:
            for placeholder, value in mapping.items():

                if placeholder in para.text:

                    content = str(value) if value else "Information Missing"
                    para.text = para.text.replace(placeholder, content)

                    for run in para.runs:

                        if content == "Information Missing":
                            run.font.color.rgb = RED
                            run.font.bold = True
                        else:
                            run.font.color.rgb = BLACK   # <-- ADD THIS


def _populate_project_slide(slide, proj_num, d):
    """Populate slides containing project information."""

    mapping = {
        f"{{PROJECT{proj_num}_NAME}}": d.get(f"PROJECT{proj_num}_NAME", ""),
        f"{{PROJECT{proj_num}_DURATION}}": d.get(f"PROJECT{proj_num}_DURATION", ""),
        f"{{PROJECT{proj_num}_ROLE}}": d.get(f"PROJECT{proj_num}_ROLE", ""),
        f"{{PROJECT{proj_num}_DESCRIPTION}}": d.get(f"PROJECT{proj_num}_DESCRIPTION", ""),
        f"{{PROJECT{proj_num}_RESPONSIBILITIES}}": d.get(f"PROJECT{proj_num}_RESPONSIBILITIES", "")
    }

    for shape in slide.shapes:

        if not shape.has_text_frame:
            continue

        tf = shape.text_frame

        for para in tf.paragraphs:

            for placeholder, value in mapping.items():

                if placeholder in para.text:

                    if not value:
                        value = "Information Missing"

                    # Handle responsibilities bullet list
                    if placeholder.endswith("RESPONSIBILITIES") and isinstance(value, str):

                        lines = [line.strip() for line in value.split("\n") if line.strip()]

                        if lines:
                            para.text = lines[0]

                            for line in lines[1:]:
                                new_p = tf.add_paragraph()
                                new_p.text = line
                                new_p.level = 0

                    else:
                        para.text = para.text.replace(placeholder, str(value))

                    if value == "Information Missing":
                        _apply_missing_style(para)


def generate_candidate_ppt(candidate_data: dict):
    """Generate candidate PPT from template."""

    try:

        if not os.path.exists(TEMPLATE_PATH):
            print("Template file not found.")
            return None

        prs = Presentation(TEMPLATE_PATH)

        # Convert candidate data → template placeholders
        mapped_data = map_to_ppt_format(candidate_data)

        # Slide 1 (Profile)
        if len(prs.slides) >= 1:
            _populate_slide1(prs.slides[0], mapped_data)

        # Slides 2–5 (Projects)
        for i in range(1, min(5, len(prs.slides))):
            _populate_project_slide(prs.slides[i], i, mapped_data)

        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        return buf.read()

    except Exception as e:
        print(f"Error generating PPT: {e}")
        return None