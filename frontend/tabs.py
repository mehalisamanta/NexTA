"""
ui/tabs.py
Upload Resumes tab + Analytics tab.

"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

from utils.file_handlers import extract_text_from_file
from utils.preprocessing import parse_resume_with_openai
from utils.debug_log import debug_log
from utils.scoring import format_dataframe_for_display
from utils.sharepoint import (
    SHAREPOINT_AVAILABLE,
    download_from_sharepoint,
    save_csv_to_sharepoint,
)
from config.settings import COLUMN_DISPLAY_NAMES

# region agent log
debug_log(
    location="frontend/tabs.py:module_import",
    message="tabs module imported",
    hypothesis_id="H8",
    data={},
)
# endregion


def _sp_config():
    return st.session_state.get("sharepoint_config", {})


def _sp_connected():
    return _sp_config().get("connected", False)


# Upload Tab 

def render_upload_tab():
    st.header("Step 1: Upload/Retrieve Resumes")

    client           = st.session_state.get("client")
    mask_pii_enabled = st.session_state.get("mask_pii_enabled", True)

    # region agent log
    debug_log(
        location="frontend/tabs.py:render_upload_tab:render",
        message="upload tab rendered",
        hypothesis_id="H6",
        data={
            "client_present": bool(client),
            "mask_pii_enabled": bool(mask_pii_enabled),
            "upload_method_radio": st.session_state.get("upload_method_radio", ""),
            "parsed_resumes_len": len(st.session_state.get("parsed_resumes", []) or []),
        },
    )
    # endregion

    upload_method = st.radio(
        "Where are the resumes coming from?",
        ["📁 Upload Manually", "☁️ Retrieve from SharePoint"],
        horizontal=True,
        key="upload_method_radio",
    )
    st.session_state["upload_method"] = upload_method

    # SharePoint 
    if upload_method == "☁️ Retrieve from SharePoint":
        st.subheader("SharePoint")

        if not SHAREPOINT_AVAILABLE:
            st.error("⚠️ msal not installed. Run: pip install msal")
            return

        if not _sp_connected():
            st.warning("⚠️ SharePoint is not connected. Check your credentials in .env.")
            return

        st.success("✅ SharePoint Connected")

        if st.button("📥 Get All Resumes from SharePoint", type="primary"):
            # region agent log
            debug_log(
                location="frontend/tabs.py:render_upload_tab:sharepoint_clicked",
                message="sharepoint resume retrieval started",
                hypothesis_id="H6",
                data={
                    "client_present": bool(client),
                    "mask_pii_enabled": bool(mask_pii_enabled),
                },
            )
            # endregion
            with st.spinner("Fetching resumes from SharePoint…"):
                sp               = _sp_config()
                downloaded_files = download_from_sharepoint(sp)

                # Date filter (applied BEFORE parsing) 
                use_date_filter = st.session_state.get("use_date_filter", False)
                start_date      = st.session_state.get("start_date")
                end_date        = st.session_state.get("end_date")

                if use_date_filter and start_date and end_date and downloaded_files:
                    filtered = []
                    for f in downloaded_files:
                        ts = f.get("timestamp", "")
                        try:
                            fdate = datetime.fromisoformat(
                                str(ts).replace("Z", "+00:00")
                            ).date()
                            if start_date <= fdate <= end_date:
                                filtered.append(f)
                        except Exception:
                            filtered.append(f)  
                    total_before     = len(downloaded_files)
                    downloaded_files = filtered
                    st.info(
                        f"📅 Date filter: {len(downloaded_files)} of {total_before} files match "
                        f"({start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')})"
                    )

                if downloaded_files and client:
                    st.success(f"✅ Found {len(downloaded_files)} files")
                    progress = st.progress(0)
                    status   = st.empty()

                    st.session_state.parsed_resumes  = []
                    st.session_state.resume_texts    = {}
                    st.session_state.resume_metadata = {}
                    seen_names = set()

                    failed_files = []

                    for idx, file_data in enumerate(downloaded_files):
                        status.text(f"Reading: {file_data['name']}")
                        text = extract_text_from_file(file_data)
                        if not text:
                            failed_files.append((file_data["name"], "Could not extract text"))
                            progress.progress((idx + 1) / len(downloaded_files))
                            continue
                        # region agent log
                        debug_log(
                            location="frontend/tabs.py:render_upload_tab:sharepoint_file_text",
                            message="sharepoint file text extracted (pre-parse)",
                            hypothesis_id="H6",
                            data={
                                "filename": file_data.get("name", ""),
                                "text_len": len(text or ""),
                            },
                        )
                        # endregion

                        upload_date = file_data.get("timestamp", datetime.now().isoformat())
                        if isinstance(upload_date, str):
                            try:
                                upload_date = datetime.fromisoformat(
                                    upload_date.replace("Z", "+00:00")
                                ).strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        parsed = parse_resume_with_openai(
                            client, text, file_data["name"], mask_pii_enabled, upload_date
                        )
                        if not parsed:
                            failed_files.append((file_data["name"], "AI parsing returned no data"))
                            progress.progress((idx + 1) / len(downloaded_files))
                            continue
                        # region agent log
                        debug_log(
                            location="frontend/tabs.py:render_upload_tab:sharepoint_file_parsed",
                            message="sharepoint file parsed (post-parse)",
                            hypothesis_id="H6",
                            data={
                                "filename": file_data.get("name", ""),
                                "parsed_keys_sample": list(parsed.keys())[:20],
                                "name_empty": not bool((parsed.get("name") or "").strip()),
                                "email_empty": not bool((parsed.get("email") or "").strip()),
                                "phone_empty": not bool((parsed.get("phone") or "").strip()),
                                "skills_empty": not bool(str(parsed.get("tech_stack") or "").strip()),
                                "education_empty": not bool(str(parsed.get("education") or "").strip()),
                            },
                        )
                        # endregion

                        cname = parsed.get("name", "").strip().lower()
                        if cname and cname in seen_names:
                            failed_files.append((file_data["name"], "Duplicate candidate name"))
                            progress.progress((idx + 1) / len(downloaded_files))
                            continue
                        if cname:
                            seen_names.add(cname)
                        st.session_state.parsed_resumes.append(parsed)
                        st.session_state.resume_texts[parsed.get("name", "")] = text
                        st.session_state.resume_metadata[parsed.get("name", "")] = {
                            "submission_date": upload_date,
                            "filename": file_data["name"],
                        }
                        progress.progress((idx + 1) / len(downloaded_files))

                    status.empty()
                    progress.empty()

                    if st.session_state.parsed_resumes:
                        st.session_state.candidates_df = pd.DataFrame(
                            st.session_state.parsed_resumes
                        )
                        parsed_count = len(st.session_state.parsed_resumes)
                        total_count  = len(downloaded_files)
                        st.success(
                            f"📥 {parsed_count} of {total_count} resumes parsed successfully — "
                            "go to **Candidate Review & Scoring** to continue."
                        )
                        if failed_files:
                            with st.expander(f"⚠️ {len(failed_files)} file(s) could not be processed"):
                                for fname, reason in failed_files:
                                    st.markdown(f"- **{fname}** — {reason}")
                elif not downloaded_files:
                    st.warning("No PDF or Word files found in the configured SharePoint folder.")

    # Manual Upload 
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_files = st.file_uploader(
                "Upload Resumes (PDF or Word files only)",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                help="PDF and Word formats are supported.",
            )
        with col2:
            st.metric("📁 Files Selected", len(uploaded_files) if uploaded_files else 0)
            resumes_placeholder = st.empty()
            resumes_placeholder.metric(
                "✅ Resumes Ready", len(st.session_state.parsed_resumes)
            )

        if uploaded_files and client:
            if st.button("🚀 Read All Resumes", type="primary"):
                # #region agent log
                debug_log(
                    location="frontend/tabs.py:render_upload_tab:manual_clicked",
                    message="manual resume processing started",
                    hypothesis_id="H6",
                    data={
                        "files_selected": len(uploaded_files or []),
                        "client_present": bool(client),
                        "mask_pii_enabled": bool(mask_pii_enabled),
                    },
                )
                # #endregion
                progress = st.progress(0)
                status   = st.empty()

                st.session_state.parsed_resumes  = []
                st.session_state.resume_texts    = {}
                st.session_state.resume_metadata = {}

                for idx, file in enumerate(uploaded_files):
                    status.text(f"Reading: {file.name}")
                    text = extract_text_from_file(file)
                    if text:
                        # #region agent log
                        debug_log(
                            location="frontend/tabs.py:render_upload_tab:manual_file_text",
                            message="manual file text extracted (pre-parse)",
                            hypothesis_id="H6",
                            data={
                                "filename": getattr(file, "name", ""),
                                "text_len": len(text or ""),
                            },
                        )
                        # #endregion
                        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        parsed = parse_resume_with_openai(
                            client, text, file.name, mask_pii_enabled, upload_date
                        )
                        if parsed:
                            # #region agent log
                            debug_log(
                                location="frontend/tabs.py:render_upload_tab:manual_file_parsed",
                                message="manual file parsed (post-parse)",
                                hypothesis_id="H6",
                                data={
                                    "filename": getattr(file, "name", ""),
                                    "parsed_keys_sample": list(parsed.keys())[:20],
                                    "name_empty": not bool((parsed.get("name") or "").strip()),
                                    "email_empty": not bool((parsed.get("email") or "").strip()),
                                    "phone_empty": not bool((parsed.get("phone") or "").strip()),
                                    "skills_empty": not bool(str(parsed.get("tech_stack") or "").strip()),
                                    "education_empty": not bool(str(parsed.get("education") or "").strip()),
                                },
                            )
                            # #endregion
                            st.session_state.parsed_resumes.append(parsed)
                            st.session_state.resume_texts[parsed.get("name", "")] = text
                            st.session_state.resume_metadata[parsed.get("name", "")] = {
                                "submission_date": upload_date,
                                "filename": file.name,
                            }
                    progress.progress((idx + 1) / len(uploaded_files))

                status.empty()
                progress.empty()

                if st.session_state.parsed_resumes:
                    st.session_state.candidates_df = pd.DataFrame(
                        st.session_state.parsed_resumes
                    )
                    resumes_placeholder.metric(
                        "✅ Resumes Ready", len(st.session_state.parsed_resumes)
                    )
                    st.success(
                        f"📥 {len(st.session_state.parsed_resumes)} resumes ready — "
                        "go to the **Candidate Review & Scoring** tab to continue."
                    )

        if st.session_state.parsed_resumes:
            st.subheader("Resumes Loaded (Quick Preview)")
            for resume in st.session_state.parsed_resumes[:3]:
                with st.expander(f"👤 {resume.get('name', 'Unknown')}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Experience:** {resume.get('experience_years')} years")
                        st.write(f"**Email:** {resume.get('email')}")
                        st.write(f"**Received:** {resume.get('submission_date', 'N/A')}")
                    with c2:
                        st.write(f"**Current Role:** {resume.get('current_role')}")
                        st.write(f"**Skills:** {str(resume.get('tech_stack', ''))[:80]}…")


# Analytics Tab 

def render_analytics_tab():
    st.header("📈 Analytics Dashboard")

    use_date_filter = st.session_state.get("use_date_filter", False)
    start_date      = st.session_state.get("start_date")
    end_date        = st.session_state.get("end_date")

    if st.session_state.candidates_df is not None:
        df = st.session_state.candidates_df.copy()

        if use_date_filter and start_date and end_date:
            try:
                df["submission_date"] = pd.to_datetime(df["submission_date"])
                df = df[
                    (df["submission_date"].dt.date >= start_date)
                    & (df["submission_date"].dt.date <= end_date)
                ]
            except Exception:
                pass

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Resumes Uploaded", len(df))
        with c2:
            st.metric("In Candidate Pool", len(st.session_state.get("selected_for_pool", set())))
        with c3:
            unique_skills = len(
                set(", ".join(df["tech_stack"].astype(str)).split(", "))
            )
            st.metric("Different Skills Seen", unique_skills)

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Experience Levels")
            exp_bins = pd.cut(
                pd.to_numeric(df["experience_years"], errors="coerce").fillna(0),
                bins=[0, 2, 5, 10, 20],
                labels=["0–2 years", "2–5 years", "5–10 years", "10+ years"],
            )
            exp_counts = exp_bins.value_counts().sort_index()
            fig = px.bar(
                x=exp_counts.index.astype(str), y=exp_counts.values,
                labels={"x": "Experience Level", "y": "Number of People"},
                color=exp_counts.values, color_continuous_scale="Blues",
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            review_results = st.session_state.get("review_results")
            if review_results:
                st.subheader("Match Scores")
                scores = [r["final_score"] for r in review_results]
                names  = [r["metadata"].get("name", "?") for r in review_results]
                fig = go.Figure(data=[go.Bar(
                    x=scores, y=names, orientation="h",
                    marker=dict(
                        color=scores,
                        colorscale=[[0, "#FFCDD2"], [0.5, "#FFE082"], [1, "#C8E6C9"]],
                        showscale=True, colorbar=dict(title="Score"),
                    ),
                    text=[f"{s}%" for s in scores], textposition="outside",
                )])
                fig.update_layout(
                    xaxis_title="Match Score (%)", yaxis_title="Candidate",
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Run a review to see match scores here.")

        st.subheader("Most Common Skills")
        skill_candidates: dict = {}
        for _, row in df.iterrows():
            for skill in str(row.get("tech_stack", "")).lower().split(","):
                skill = skill.strip()
                if skill and skill != "nan":
                    skill_candidates.setdefault(skill, []).append(row.get("name", "Unknown"))

        total         = len(df)
        skill_counts  = {s: len(c) for s, c in skill_candidates.items()}
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:15]

        if sorted_skills:
            skill_names = [s[0].title() for s in sorted_skills]
            skill_pcts  = [s[1] / total * 100 for s in sorted_skills]
            hover_texts = []
            for i, (sname, _) in enumerate(sorted_skills):
                cands = skill_candidates[sname]
                clist = "<br>   • ".join(cands[:8])
                more  = f"<br>   • …and {len(cands)-8} more" if len(cands) > 8 else ""
                hover_texts.append(
                    f"<b>{sname.title()}</b><br><br>"
                    f"<b>How common:</b> {skill_pcts[i]:.1f}% ({skill_counts[sname]}/{total})"
                    f"<br><br><b>Candidates:</b><br>   • {clist}{more}"
                )
            fig = go.Figure(data=[go.Bar(
                y=skill_names[::-1], x=skill_pcts[::-1], orientation="h",
                marker=dict(
                    color=skill_pcts[::-1], colorscale="Tealgrn", showscale=True,
                    colorbar=dict(title=dict(text="% of Candidates", side="right"), ticksuffix="%"),
                ),
                text=[f"{p:.1f}%" for p in skill_pcts[::-1]], textposition="outside",
                hovertext=hover_texts[::-1],
                hovertemplate="%{hovertext}<extra></extra>",
            )])
            fig.update_layout(
                xaxis_title="Percentage of Candidates (%)", yaxis_title="Skill",
                height=600, margin=dict(l=150),
                hoverlabel=dict(bgcolor="white", font_size=15, font_family="Arial",
                                font_color="black", bordercolor="#BDBDBD", align="left"),
            )
            st.plotly_chart(fig, use_container_width=True)

        if "submission_date" in df.columns:
            st.subheader("When Resumes Were Received")
            try:
                df["submission_date"] = pd.to_datetime(df["submission_date"])
                timeline = df.groupby(df["submission_date"].dt.date).size().reset_index()
                timeline.columns = ["Date", "Count"]
                fig = px.line(timeline, x="Date", y="Count", markers=True,
                              labels={"Count": "Resumes Received"})
                fig.update_traces(line_color="#64B5F6", marker=dict(size=8, color="#42A5F5"))
                fig.update_layout(hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass
    else:
        st.info("📤 Please upload and process resumes first to see analytics.")