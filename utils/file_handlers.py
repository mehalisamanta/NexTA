"""
File handling utilities for PDF and DOCX extraction

"""

import streamlit as st
import PyPDF2
import docx2txt
import io
from utils.debug_log import debug_log
import re as _re

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def extract_text_from_docx(docx_file):
    """Extract text from DOCX file"""
    try:
        text = docx2txt.process(docx_file)
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return ""

def extract_text_from_file(uploaded_file):
    """Extract text from PDF or DOCX only"""
    if isinstance(uploaded_file, dict):  # SharePoint file
        file_ext = uploaded_file['name'].split('.')[-1].lower()
        file_content = io.BytesIO(uploaded_file['content'])
    else:  # Regular upload
        file_ext = uploaded_file.name.split('.')[-1].lower()
        file_content = uploaded_file
    
    if file_ext == 'pdf':
        text = extract_text_from_pdf(file_content)
    elif file_ext == 'docx':
        text = extract_text_from_docx(file_content)
    else:
        st.warning(f"⚠️ Unsupported file format: {file_ext}. Please upload PDF or DOCX files only.")
        return ""

    # #region agent log
    try:
        # Do NOT log resume content; only structural signals.
        email_found = bool(_re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text or ""))
        phone_found = bool(_re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text or ""))
        debug_log(
            location="utils/file_handlers.py:extract_text_from_file",
            message="extracted text from resume file",
            hypothesis_id="H5",
            data={
                "file_ext": file_ext,
                "text_len": len(text or ""),
                "has_education_keyword": ("education" in (text or "").lower()),
                "has_experience_keyword": ("experience" in (text or "").lower()),
                "email_found": email_found,
                "phone_found": phone_found,
            },
        )
    except Exception:
        pass
    # #endregion

    return text