"""
PPT Generator 

"""

import io
import os
import re

import streamlit as st
from pptx import Presentation

from utils.template_mapper import map_to_template_format

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates", "sample_ppt_template.pptx",
)

# Position thresholds in EMU (1 inch = 914 400 EMU)
_1_IN = 914_400
_5_IN = 5 * _1_IN


# Low-level helpers 

def _set_para(para, text: str) -> None:
    """
    Write text into the first run of a paragraph, blank all other runs.
    Preserves the original run's font, size, bold and colour exactly.
    Creates a run if the paragraph has none.
    """
    if not para.runs:
        para.add_run().text = text
        return
    para.runs[0].text = text
    for run in para.runs[1:]:
        run.text = ""


# Slide 1: profile 

def _fill_slide1(slide, d: dict) -> None:
    full_name  = (d.get("FULL_NAME") or "").strip()
    role       = (d.get("CURRENT_ROLE") or "").strip()
    summary    = (d.get("PROFESSIONAL_SUMMARY") or "").strip()
    education  = (d.get("EDUCATION_DETAILS") or "").strip()

    # Skills: accept comma-separated string or list
    raw_skills = d.get("TECHNICAL_SKILLS") or ""
    if isinstance(raw_skills, list):
        skill_lines = [s.strip() for s in raw_skills if str(s).strip()]
    else:
        skill_lines = [s.strip() for s in str(raw_skills).split(",") if s.strip()]

    # Split summary into individual sentences for multi-paragraph slots
    sentences = re.split(r'(?<=[.!?])\s+', summary)
    sentences = [s.strip() for s in sentences if s.strip()]

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue

        sname = shape.name
        tf    = shape.text_frame

        # Name / Role header 
        if "Google Shape" in sname or "g86061" in sname:
            header = f"{full_name}– {role} " if role else f"{full_name} "
            if tf.paragraphs and tf.paragraphs[0].runs:
                tf.paragraphs[0].runs[0].text = header
                for run in tf.paragraphs[0].runs[1:]:
                    run.text = ""

        # Three "object 3" boxes — tell apart by position 
        elif sname == "object 3":
            top  = shape.top   # EMU
            left = shape.left  # EMU

            if top < _1_IN:
                # Summary box (top ≈ 0.47 in) — 4 paragraph slots
                paras = tf.paragraphs
                for i, para in enumerate(paras):
                    _set_para(para, sentences[i] if i < len(sentences) else "")

            elif left > _5_IN:
                # Education box (left ≈ 8.33 in) — 1 paragraph
                _set_para(tf.paragraphs[0], education)

            else:
                # Skills box (left ≈ 0.27 in) — 15 paragraph slots
                paras = tf.paragraphs
                for i, para in enumerate(paras):
                    _set_para(para, skill_lines[i] if i < len(skill_lines) else "")

        # TextBox 16 ("Education" label) — leave untouched


# Project slides (slides 2–5) 

def _fill_project_slide(slide, proj_num: int, d: dict) -> None:
    pname    = (d.get(f"PROJECT{proj_num}_NAME") or "").strip()
    duration = (d.get(f"DURATION_PROJECT{proj_num}") or "").strip()
    role     = (d.get(f"ROLE_PROJECT{proj_num}") or "").strip()
    desc     = (d.get(f"Project{proj_num}_Description") or "").strip()
    resp_raw = d.get(f"Responsibilities_Project{proj_num}") or ""

    # Bullet lines — accept list or newline-separated string
    if isinstance(resp_raw, list):
        bullet_lines = [str(b).strip() for b in resp_raw if str(b).strip()]
    else:
        bullet_lines = [
            line.strip().lstrip("•- ")
            for line in str(resp_raw).splitlines()
            if line.strip()
        ]

    # Cap at 4 bullets to fit within the designed text box height
    bullet_lines = bullet_lines[:4]

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue

        sname = shape.name
        tf    = shape.text_frame

        # TextBox 6: Project name / Duration / Role 
        if sname == "TextBox 6":
            paras = tf.paragraphs

            # p[0]: "Project: {name}"
            if paras:
                p0_runs = paras[0].runs
                if len(p0_runs) >= 2:
                    p0_runs[0].text = "Project: "
                    p0_runs[-1].text = pname
                    for run in p0_runs[1:-1]:
                        run.text = ""
                elif len(p0_runs) == 1:
                    p0_runs[0].text = f"Project: {pname}"

            # p[1]: "Duration : {value}"
            if len(paras) > 1:
                p1_runs = paras[1].runs
                if len(p1_runs) >= 2:
                    p1_runs[0].text = "Duration : "
                    p1_runs[1].text = duration
                elif len(p1_runs) == 1:
                    p1_runs[0].text = f"Duration : {duration}"

            # p[2]: "Role" (bold run[0]) + ": {value}" (normal run[1])
            if len(paras) > 2:
                p2_runs = paras[2].runs
                if len(p2_runs) >= 2:
                    p2_runs[0].text = "Role"
                    p2_runs[1].text = f": {role}"
                elif len(p2_runs) == 1:
                    p2_runs[0].text = f"Role: {role}"

        # TextBox 10: Description + Responsibilities 
        elif sname == "TextBox 10":
            paras = tf.paragraphs

            # p[0] → description
            if paras:
                _set_para(paras[0], desc)

            # p[1] → blank separator
            if len(paras) > 1:
                _set_para(paras[1], "")

            # p[2] → "Responsibilities: " label
            if len(paras) > 2:
                _set_para(paras[2], "Responsibilities: ")

            # p[3]–p[6] → new candidate's bullet lines (max 4), blank unused slots
            for i in range(3, min(7, len(paras))):
                bi = i - 3
                _set_para(paras[i], bullet_lines[bi] if bi < len(bullet_lines) else "")

            for i in range(7, len(paras)):
                _set_para(paras[i], "")

        # TextBox 11 ("Description:" label) and TextBox 13 ("Project N") — leave untouched


# Public API 

def generate_candidate_ppt(candidate_data: dict) -> bytes | None:
    """
    Fill the NexTurn PPT template with candidate_data and return raw bytes.
    Returns None on error (error is also surfaced via st.error).
    """
    try:
        if not os.path.exists(TEMPLATE_PATH):
            st.error(
                f"PPT template not found. "
                f"Expected: {TEMPLATE_PATH}\n"
                f"Make sure 'sample_ppt_template.pptx' is in your templates/ folder."
            )
            return None

        prs = Presentation(TEMPLATE_PATH)
        d   = map_to_template_format(candidate_data)

        # Slide 1 — profile
        if prs.slides:
            _fill_slide1(prs.slides[0], d)

        # Slides 2–5 — projects
        for i in range(1, min(5, len(prs.slides))):
            _fill_project_slide(prs.slides[i], i, d)

        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.read()

    except Exception as exc:
        st.error(f"PPT Generation Error: {exc}")
        import traceback
        st.error(traceback.format_exc())
        return None