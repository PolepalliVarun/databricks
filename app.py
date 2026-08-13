import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Databricks Operations Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# APPLICATION PAGES
# =========================================================

job_monitor_page = st.Page(
    "pages/Job_Monitor.py",
    title="Job Monitor",
    icon="📊",
    default=True
)

app_context_page = st.Page(
    "pages/App_Context.py",
    title="App Context",
    icon="📘"
)


# =========================================================
# NAVIGATION
# =========================================================

pg = st.navigation(
    {
        "Databricks Operations": [
            job_monitor_page,
            app_context_page
        ]
    }
)


# =========================================================
# RUN SELECTED PAGE
# =========================================================

pg.run()