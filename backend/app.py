import streamlit as st
import os
from sso import render_sso_login, render_user_badge   # ✅ relative import

def main():
    # Load Azure credentials from environment
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    redirect_uri = os.getenv("AZURE_REDIRECT_URI")

    st.title("Backend Service")

    # Show credentials status for debugging
    if not all([tenant_id, client_id, client_secret, redirect_uri]):
        st.error("❌ Azure SSO credentials are missing. Please set them in your environment or secrets.toml.")
        return

    # Render login UI
    if render_sso_login():
        st.sidebar.title("User Info")
        render_user_badge()
        st.write("✅ You are logged in! Backend is working.")
    else:
        st.write("❌ Login failed or credentials missing.")

if __name__ == "__main__":
    main()