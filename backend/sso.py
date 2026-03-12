"""
backend/sso.py
Microsoft SSO Authentication

"""

import os
import streamlit as st

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False


def _cfg() -> dict:
    def _get(key: str) -> str:
        val = os.getenv(key, "")
        if not val:
            try:
                val = st.secrets.get(key, "")
            except Exception:
                pass
        return val or ""

    return {
        "tenant_id":     _get("AZURE_TENANT_ID"),
        "client_id":     _get("AZURE_CLIENT_ID"),
        "client_secret": _get("AZURE_CLIENT_SECRET"),
        "redirect_uri":  _get("AZURE_REDIRECT_URI") or "http://localhost:8501/",
    }


def _msal_app(cfg: dict):
    authority = f"https://login.microsoftonline.com/{cfg['tenant_id']}"
    return msal.ConfidentialClientApplication(
        cfg["client_id"],
        authority=authority,
        client_credential=cfg["client_secret"],
    )


_SCOPES = ["User.Read"]


def get_auth_url() -> str:
    """
    Generate auth URL once and cache in session_state.
    Prevents state/nonce mismatch when Streamlit reruns mid-flow.
    prompt=consent ensures new users always see the consent screen
    instead of being silently blocked.
    """
    if "sso_auth_url" not in st.session_state:
        cfg = _cfg()
        st.session_state["sso_auth_url"] = _msal_app(cfg).get_authorization_request_url(
            scopes=_SCOPES,
            redirect_uri=cfg["redirect_uri"],
            prompt="consent",        # forces consent screen for new users
            response_type="code",
        )
    return st.session_state["sso_auth_url"]


def exchange_code(code: str) -> dict | None:
    cfg    = _cfg()
    result = _msal_app(cfg).acquire_token_by_authorization_code(
        code,
        scopes=_SCOPES,
        redirect_uri=cfg["redirect_uri"],
    )
    if "error" in result:
        error_desc = result.get("error_description", result.get("error", "Unknown error"))
        st.error(
            f"❌ Sign-in failed: {error_desc}\n\n"
            "Please try signing in again. If the problem persists, "
            "ask your admin to grant consent at:\n"
            f"https://login.microsoftonline.com/{cfg['tenant_id']}/adminconsent"
            f"?client_id={cfg['client_id']}"
        )
        return None
    return result


def _user_from_token(token_resp: dict) -> dict:
    claims = token_resp.get("id_token_claims", {})
    return {
        "name":  claims.get("name") or claims.get("preferred_username", "User"),
        "email": (claims.get("preferred_username") or claims.get("email", "")).lower(),
    }


def render_sso_login() -> bool:
    """
    Returns True  → user authenticated, render the app.
    Returns False → show login screen, stop rendering app body.
    """
    # Already authenticated 
    if st.session_state.get("logged_in"):
        return True

    if not MSAL_AVAILABLE:
        st.error("msal is not installed. Run: pip install msal")
        return False

    cfg = _cfg()
    if not cfg["tenant_id"] or not cfg["client_id"]:
        st.error(
            "Azure SSO credentials missing. "
            "Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, "
            "AZURE_REDIRECT_URI in Streamlit secrets."
        )
        return False

    # Microsoft redirected back with ?code= 
    code  = st.query_params.get("code")
    error = st.query_params.get("error")

    # Handle Microsoft returning an error directly (e.g. user denied consent)
    if error:
        error_desc = st.query_params.get("error_description", error)
        st.query_params.clear()
        st.session_state.pop("sso_auth_url", None)
        st.error(f"❌ Microsoft sign-in error: {error_desc}")
        st.info("Please try signing in again.")
        return False

    if code:
        # Guard against double-processing on Streamlit reruns
        if st.session_state.get("sso_code_processing"):
            st.info("⏳ Completing sign-in, please wait…")
            return False

        st.session_state["sso_code_processing"] = True

        with st.spinner("Completing sign-in…"):
            token_resp = exchange_code(code)

        if token_resp:
            user = _user_from_token(token_resp)
            st.session_state["logged_in"]    = True
            st.session_state["user_name"]    = user["name"]
            st.session_state["user_email"]   = user["email"]
            st.session_state["access_token"] = token_resp.get("access_token", "")
            st.session_state.pop("sso_auth_url",        None)
            st.session_state.pop("sso_code_processing", None)
            st.query_params.clear()
            st.rerun()
        else:
            # Exchange failed — reset everything so user can retry cleanly
            st.session_state.pop("sso_code_processing", None)
            st.session_state.pop("sso_auth_url",        None)
            st.query_params.clear()
            # Error message already shown inside exchange_code()
            if st.button("🔄 Try signing in again"):
                st.rerun()

        return False

    # Not logged in — show sign-in screen 
    _, logo_col, _ = st.columns([1, 1, 1])
    with logo_col:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.markdown("## NexTurn")

    st.markdown(
        "<h1 style='text-align:center;font-size:2.4rem;font-weight:900;"
        "color:#0f172a;margin-bottom:4px;'>Resume Screening System</h1>"
        "<p style='text-align:center;color:#64748b;font-size:1rem;margin-bottom:28px;'>"
        "Powered by OpenAI · Automated Intelligent Recruitment</p>"
        "<hr style='border:none;border-top:2px solid #e2e8f0;margin-bottom:32px;'>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        auth_url = get_auth_url()
        st.markdown(
            f'<a href="{auth_url}" target="_self" style="text-decoration:none;color:white;">'
            '<div style="background:#464EB8;color:white;font-weight:700;'
            'font-size:1.25rem;text-align:center;padding:14px 20px;'
            'border-radius:8px;cursor:pointer;margin-top:8px;">'
            "&nbsp; Sign in with Microsoft"
            "</div></a>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center;color:#94a3b8;font-size:0.82rem;"
            "margin-top:14px;'>You will be redirected to your company Microsoft login.</p>",
            unsafe_allow_html=True,
        )
    return False


def render_user_badge():
    name  = st.session_state.get("user_name",  "User")
    email = st.session_state.get("user_email", "")

    st.sidebar.markdown(
        f"<div style='background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;"
        f"padding:10px 12px;margin-bottom:12px;'>"
        f"<p style='margin:0;font-size:0.95rem;font-weight:700;color:#166534;'>👤 {name}</p>"
        f"<p style='margin:2px 0 0 0;font-size:0.8rem;color:#555;'>{email}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        for k in ["logged_in", "user_name", "user_email", "access_token",
                  "sso_auth_url", "sso_code_processing"]:
            st.session_state.pop(k, None)
        st.rerun()