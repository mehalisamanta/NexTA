import streamlit as st
import os
import sys

# Ensure root directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import your custom modules
from backend.file_handlers import extract_text_from_file
from backend.openai_client import init_openai_client, OpenAI
from backend.preprocessing import parse_resume_with_openai
from backend.ppt_generator import generate_candidate_ppt

def main():
    st.set_page_config(page_title="NexTA Resume to PPT", layout="centered", page_icon="📄")
    st.title("📄 Resume to PPT Generator")

    # Sidebar for API Key
    st.sidebar.header("Configuration")
    api_key_input = st.sidebar.text_input("Enter OpenAI API Key", type="password", help="Overrides environment variables")

    uploaded_file = st.file_uploader("Upload Candidate Resume", type=["pdf", "docx"])

    if uploaded_file is not None and st.button("🚀 Process & Generate PPT"):
        with st.spinner("Extracting and Parsing..."):
            try:
                # 1. Initialize Client
                if api_key_input:
                    client = OpenAI(api_key=api_key_input)
                else:
                    client = init_openai_client()

                # 2. Extract text
                raw_text = extract_text_from_file(uploaded_file)
                
                # 3. Parse resume
                parsed_data = parse_resume_with_openai(
                    client=client,
                    resume_text=raw_text,
                    filename=uploaded_file.name
                )
                
                # --- NEW DEBUG BLOCK ---
                if parsed_data:
                    with st.expander("🔍 View AI Parsed Data (Debug)"):
                        st.json(parsed_data)
                else:
                    st.error("AI parsing failed.")
                    return
                # -----------------------

                # 4. Generate PPT
                ppt_bytes = generate_candidate_ppt(parsed_data)

                if ppt_bytes:
                    st.balloons()
                    st.success("PowerPoint generated successfully!")
                    st.download_button(
                        label="📥 Download PowerPoint",
                        data=ppt_bytes,
                        file_name=f"PPT_{uploaded_file.name.split('.')[0]}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                else:
                    st.error("Failed to generate PowerPoint. Check console for details.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()