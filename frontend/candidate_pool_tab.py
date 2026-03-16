"""
Candidate Pool Tab

"""

import io
import re
from datetime import datetime
import streamlit as st
import pandas as pd
from utils.scoring import format_dataframe_for_display
from utils.sharepoint import SHAREPOINT_AVAILABLE, save_csv_to_sharepoint


def _sp_config():
    return st.session_state.get('sharepoint_config', {})

def _sp_connected():
    return _sp_config().get('connected', False)


def _is_valid_email(val: str) -> bool:
    """Basic email format check."""
    if not val or str(val).strip() in ("", "N/A", "None", "nan", "none"):
        return False
    return bool(re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(val).strip()))


def _is_valid_phone(val: str) -> bool:
    """Check phone has at least 7 digits."""
    if not val or str(val).strip() in ("", "N/A", "None", "nan", "none"):
        return False
    digits = re.sub(r"\D", "", str(val))
    return len(digits) >= 7


def _fmt(val, validator) -> str:
    """Return value if valid, else empty string (cell styled separately)."""
    return str(val).strip() if validator(val) else ""


def render_candidate_pool_tab():
    st.header("👥 Candidate Pool")

    selected_names = st.session_state.get('selected_for_pool', set())

    # Empty state 
    if not selected_names:
        st.markdown("""
        <div style="background:#F0F7FF; padding:24px; border-radius:10px;
                    border-left:5px solid #90CAF9; margin-top:16px;">
            <h3 style="color:#1A5276; margin:0 0 8px 0; font-size:1.2rem;">
                No candidates in the pool yet
            </h3>
            <p style="color:#2C3E50; margin:0; font-size:1rem; line-height:1.6;">
                Go to <strong>Candidate Review &amp; Scoring</strong>, run the AI screening,
                and tick the checkbox next to the candidates you want to shortlist.
                They will appear here automatically.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    all_resumes      = st.session_state.get('parsed_resumes', [])
    review_results   = st.session_state.get('review_results', [])
    selected_resumes = [r for r in all_resumes if r.get('name') in selected_names]

    if not selected_resumes:
        st.warning("Resume data not found for selected candidates. Please go back and re-select.")
        return

    # Summary banner 
    st.markdown(f"""
    <div style="background:#F0FFF4; padding:16px 20px; border-radius:10px;
                border-left:5px solid #81C784; margin-bottom:24px;">
        <p style="margin:0; color:#1B5E20; font-size:1.15rem; font-weight:700;">
            ✅ {len(selected_resumes)} candidate(s) shortlisted
        </p>
        <p style="margin:6px 0 0 0; color:#2E7D32; font-size:0.95rem;">
            Download the pool data below or save it directly to SharePoint.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Build display table 
    score_map = {
        r['metadata'].get('name'): r.get('final_score', '—')
        for r in review_results
    }

    rows = []
    for r in selected_resumes:
        name  = r.get('name', '')
        email = r.get('email', '')
        phone = r.get('phone', '')
        rows.append({
            'Candidate Name':   name,
            'AI Match Score':   f"{score_map.get(name, '—')}%" if score_map.get(name) != '—' else '—',
            'Current Role':     r.get('current_role', ''),
            'Experience (yrs)': r.get('experience_years', ''),
            'Email':            email if _is_valid_email(email) else None,
            'Phone':            phone if _is_valid_phone(phone) else None,
            'Key Skills':       str(r.get('tech_stack', ''))[:80],
            'Education':        r.get('education', ''),
        })

    def _score_val(row):
        s = str(row.get('AI Match Score', '0')).replace('%', '').strip()
        try:    return float(s)
        except: return 0

    rows.sort(key=_score_val, reverse=True)
    pool_df = pd.DataFrame(rows)

    # Render table with red "None" for missing contact fields 
    st.subheader("📊 Pool Overview")

    def _style_none_red(df):
        """Apply red colour to cells that are None/NaN in Email and Phone columns."""
        styled = pd.DataFrame("", index=df.index, columns=df.columns)
        for col in ["Email", "Phone"]:
            if col in df.columns:
                mask = df[col].isna() | (df[col] == "")
                styled.loc[mask, col] = "color: #DC2626; font-weight: 600;"
        return styled

    # Fill None with display text "None" for the styled table
    display_df = pool_df.copy()
    for col in ["Email", "Phone"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].fillna("None")

    styled = display_df.style.apply(
        lambda _: [
            "color: #DC2626; font-weight: 600;"
            if display_df.loc[row_idx, col] == "None" and col in ("Email", "Phone")
            else ""
            for col in display_df.columns
        ],
        axis=1,
        result_type="expand",
    )
    # Rename columns to match display_df
    styled.columns = display_df.columns

    st.dataframe(display_df.style.apply(_style_none_red, axis=None),
                 use_container_width=True, hide_index=True)

    # Download & SharePoint 
    st.markdown("#### 💾 Export Pool Data")

    csv_buf = io.StringIO()
    pool_df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue()

    col_csv, col_sp, _ = st.columns([1, 1, 1])

    with col_csv:
        st.download_button(
            "📥 Download as Spreadsheet",
            data=csv_bytes,
            file_name="candidate_pool.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_sp:
        if _sp_connected():
            if st.button("☁️ Save to SharePoint", use_container_width=True):
                sp       = _sp_config()
                filename = f"candidate_pool_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                raw_df   = pd.DataFrame(selected_resumes)
                if save_csv_to_sharepoint(sp, raw_df, filename):
                    st.success("✅ Saved to SharePoint!")
                else:
                    st.error("Could not save to SharePoint.")
        else:
            st.button(
                "☁️ Save to SharePoint",
                use_container_width=True,
                disabled=True,
                help="Connect SharePoint in the sidebar to enable this."
            )