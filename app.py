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
# MANUAL PAGE DEFINITIONS
# =========================================================

job_monitor_page = st.Page(
    "pages/Job_Monitor.py",
    title="Job Monitor",
    icon="📊",
    default=True
)

ai_analysis_page = st.Page(
    "pages/AI_Analysis.py",
    title="AI Analysis",
    icon="🤖"
)

app_context_page = st.Page(
    "pages/App_Context.py",
    title="App Context",
    icon="📘"
)


# =========================================================
# MANUAL NAVIGATION
# =========================================================

pg = st.navigation(
    {
        "Monitoring": [
            job_monitor_page
        ],
        "AI & Information": [
            ai_analysis_page,
            app_context_page
        ]
    }
)


# =========================================================
# RUN SELECTED PAGE
# =========================================================

pg.run()