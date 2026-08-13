import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Databricks Operations Dashboard",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# HOME PAGE
# =========================================================

st.title("📊 Databricks Operations Dashboard")

st.markdown(
    """
    ## Welcome

    This application provides a centralized interface
    for monitoring Databricks jobs and understanding
    DBU usage.

    Use the navigation menu on the left to access the
    available application pages.
    """
)


# =========================================================
# APPLICATION OVERVIEW
# =========================================================

st.header("Application Overview")

st.markdown(
    """
    The application currently provides the following
    capabilities:

    - Databricks Job Monitoring
    - Job Run Monitoring
    - Job-level DBU Usage
    - Application Context and Documentation

    Cost calculation is currently excluded.
    """
)


# =========================================================
# APPLICATION FLOW
# =========================================================

st.header("Application Flow")

st.code(
    """
    Databricks Workspace
            |
            +-----------------------+
            |                       |
            v                       v
    Databricks Jobs API     system.billing.usage
            |                       |
            v                       v
       Job Details              DBU Usage
            |                       |
            +-----------+-----------+
                        |
                        v
               Streamlit Dashboard
                        |
              +---------+---------+
              |                   |
              v                   v
        Job Monitor          App Context
    """,
    language="text"
)


# =========================================================
# CURRENT SCOPE
# =========================================================

st.header("Current Scope")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Monitoring",
        "Databricks Jobs"
    )

with col2:
    st.metric(
        "Usage",
        "DBU"
    )

with col3:
    st.metric(
        "Cost",
        "Excluded"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Databricks Operations Dashboard"
)