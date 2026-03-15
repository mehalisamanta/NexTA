"""
frontend/app.py
AI-Powered Resume Screening System — main entry point.

"""

import os
import sys
import streamlit as st
from datetime import datetime, timedelta
from PIL import Image

# Make project root importable
_by_file = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_by_cwd = os.getcwd()
for _root in (_by_file, _by_cwd):
    if _root not in sys.path:
        sys.path.insert(0, _root)

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from config.settings import PAGE_CONFIG, CUSTOM_CSS
from backend.openai_client import init_openai_client
from backend.sso import render_sso_login, render_user_badge
from frontend.tabs import render_upload_tab, render_analytics_tab
from frontend.analysis_tab import render_analysis_tab
from frontend.candidate_pool_tab import render_candidate_pool_tab

# Page config (must be first Streamlit call)
st.set_page_config(**PAGE_CONFIG)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span {
    font-size: 1.08rem !important;
    font-weight: 700 !important;
    color: #111827 !important;
}
</style>
""", unsafe_allow_html=True)


# Session state defaults
_defaults = {
    "parsed_resumes":    [],
    "candidates_df":     None,
    "matched_results":   None,
    "review_results":    None,
    "selected_for_pool": set(),
    "resume_texts":      {},
    "resume_metadata":   {},
    "logged_in":         False,
    "sharepoint_config": {
        "tenant_id":          os.getenv("TENANT_ID",           ""),
        "client_id":          os.getenv("CLIENT_ID",           ""),
        "client_secret":      os.getenv("CLIENT_SECRET",       ""),
        "site_id":            os.getenv("SHAREPOINT_SITE_ID",  ""),
        "drive_id":           os.getenv("SHAREPOINT_DRIVE_ID", ""),
        "input_folder_path":  os.getenv("INPUT_FOLDER_PATH",  "Demair/Sample resumes"),
        "output_folder_path": os.getenv("OUTPUT_FOLDER_PATH", "Demair/Resumes_database"),
        "jd_folder_path":     os.getenv("JD_FOLDER_PATH",     "Demair/Job_Descriptions"),
        "connected":          False,
    },
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def _init_openai():
    if st.session_state.get("client") is None:
        try:
            st.session_state["client"] = init_openai_client()
        except Exception as e:
            st.warning(f"⚠️ OpenAI client could not be initialised: {e}")
            st.session_state["client"] = None


def _init_sharepoint():
    sp = st.session_state.sharepoint_config
    if sp.get("connected"):
        return
    required = [sp.get("tenant_id"), sp.get("client_id"),
                sp.get("client_secret"), sp.get("site_id"), sp.get("drive_id")]
    if not all(required):
        return
    try:
        import msal
        authority = f"https://login.microsoftonline.com/{sp['tenant_id']}"
        app = msal.ConfidentialClientApplication(
            sp["client_id"], authority=authority,
            client_credential=sp["client_secret"],
        )
        token = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" in token:
            sp["connected"] = True
            st.session_state.sharepoint_config = sp
    except Exception:
        pass


def main():
    if not render_sso_login():
        return

    _init_openai()
    _init_sharepoint()

    # Header
    st.markdown('<div class="nexturn-header">', unsafe_allow_html=True)
    try:
        col1, col2, col3 = st.columns([1, 1.3, 1])
        with col2:
            st.image(Image.open("logo.png"), width=400)
    except FileNotFoundError:
        pass

    st.markdown(
        '<hr style="margin:20px 0;border:none;border-top:2px solid #e0e0e0;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 style="font-size:3rem;font-weight:700;color:#1a1a1a;text-align:center;'
        'margin:15px 0 10px 0;letter-spacing:-0.5px;">Resume Screening System</h1>'
        '<p style="font-size:1.15rem;color:#666;text-align:center;margin-bottom:10px;">'
        "Powered by OpenAI · Automated Intelligent Recruitment</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        render_user_badge()
        st.title("⚙️ Settings")

        st.subheader("🛡️ Privacy")
        st.markdown(
            "<div style='background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;"
            "padding:10px 12px;font-size:0.88rem;color:#92400E;'>"
            "⚠️ <strong>PII Masking is always ON</strong><br>"
            "<span style='font-size:0.82rem;'>Personal details (email, phone) are always "
            "redacted before AI processing.</span></div>",
            unsafe_allow_html=True,
        )
        mask_pii_enabled = True

        st.divider()

        sp_connected    = st.session_state.sharepoint_config.get("connected", False)
        sp_tab_selected = (
            st.session_state.get("upload_method_radio", "")
            == "☁️ Retrieve from SharePoint"
        )
        sp_active = sp_connected and sp_tab_selected

        st.subheader("☁️ SharePoint Date Filter")
        if sp_active:
            st.markdown(
                "<ul style='font-size:0.88rem;color:#555;margin:0 0 8px 0;"
                "padding-left:16px;line-height:1.9;'>"
                "<li>Applies to SharePoint resumes only</li>"
                "<li>Filters by upload date</li></ul>",
                unsafe_allow_html=True,
            )
            use_date_filter = st.checkbox(
                "Turn on date filter", value=False, key="date_filter_checkbox"
            )
        else:
            st.markdown(
                "<div style='background:#F1F5F9;border-radius:8px;padding:10px 14px;"
                "color:#94A3B8;font-size:0.88rem;'>"
                "🔒 Available only when <strong>Retrieve from SharePoint</strong> "
                "is selected in the Upload tab.</div>",
                unsafe_allow_html=True,
            )
            use_date_filter = False

        start_date = end_date = None
        if use_date_filter:
            today = datetime.now().date()
            quick = st.radio(
                "Quick select",
                ["📅 Custom range", "⚡ Today"],
                horizontal=True,
                key="date_quick_select",
            )
            if quick == "⚡ Today":
                start_date = end_date = today
                st.info(f"📅 Today: {today.strftime('%d %b %Y')}")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    start_date = st.date_input(
                        "From", value=today - timedelta(days=90), key="date_from"
                    )
                with c2:
                    end_date = st.date_input("To", value=today, key="date_to")

                if start_date and end_date:
                    if start_date > end_date:
                        st.error("⚠️ 'From' date cannot be after 'To' date.")
                        start_date = end_date = None
                    else:
                        st.info(
                            f"📅 {start_date.strftime('%d %b %Y')} → "
                            f"{end_date.strftime('%d %b %Y')}"
                        )

    st.session_state["mask_pii_enabled"] = mask_pii_enabled
    st.session_state["use_date_filter"]  = use_date_filter
    st.session_state["start_date"]       = start_date
    st.session_state["end_date"]         = end_date

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload/Retrieve Resumes",
        "🎯 Candidate Review & Scoring",
        "👥 Candidate Pool",
        "📈 Analytics",
    ])

    with tab1:
        render_upload_tab()

    with tab2:
        parsed = st.session_state.get("parsed_resumes", [])
        client = st.session_state.get("client")
        if parsed and client:
            render_analysis_tab(parsed, client)
        else:
            st.info(
                "📤 Please upload and process resumes in the **Upload Resumes** tab first."
            )

    with tab3:
        render_candidate_pool_tab()

    with tab4:
        render_analytics_tab()

    # Footer
    st.divider()
    st.markdown(
        '<div style="text-align:center;color:#666;padding:20px;">'
        "<p>AI Resume Screening System · Automated Intelligent Recruitment · "
        "Built with Streamlit &amp; OpenAI</p>"
        '<p style="font-size:0.85em;">© 2026 NEXTURN. All rights reserved.</p>'
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()