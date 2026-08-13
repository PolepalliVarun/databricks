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
# HOME PAGE
# =========================================================

st.title("📊 Databricks Operations Dashboard")

st.success(
    "Databricks Operations Dashboard is running successfully."
)


st.markdown(
    """
    ## Welcome

    This application provides centralized visibility into
    Databricks jobs, job runs, DBU usage, and AI-powered
    job analysis.

    Use the navigation menu on the left to access the
    application pages.
    """
)


# =========================================================
# APPLICATION FEATURES
# =========================================================

st.header("Application Features")


col1, col2, col3 = st.columns(3)


with col1:

    st.subheader("📊 Job Monitor")

    st.write(
        """
        Monitor Databricks jobs and job runs.

        - Job information
        - Job IDs
        - Created date
        - Last update
        - Created by
        - Job run status
        - Success ratio
        - DBU usage
        """
    )


with col2:

    st.subheader("🤖 AI Analysis")

    st.write(
        """
        Ask questions about the job data using
        natural language.

        Examples:

        - Which jobs use the most DBUs?
        - Which jobs are failing?
        - Which jobs need attention?
        - Summarize job health.
        - Give recommendations.
        """
    )


with col3:

    st.subheader("📘 App Context")

    st.write(
        """
        Understand the purpose and architecture
        of the application.
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
             +------------------------+
             |                        |
             v                        v
      Databricks Jobs API      system.billing.usage
             |                        |
             v                        v
        Job Details               DBU Usage
             |                        |
             +------------+-----------+
                          |
                          v
                 Streamlit Dashboard
                          |
             +------------+------------+
             |                         |
             v                         v
        Job Monitor              AI Analysis
                                       |
                                       v
                              Databricks Model
                                  Serving
    """,
    language="text"
)


# =========================================================
# CURRENT SCOPE
# =========================================================

st.header("Current Scope")


metric1, metric2, metric3 = st.columns(3)


with metric1:

    st.metric(
        "Monitoring",
        "Databricks Jobs"
    )


with metric2:

    st.metric(
        "Usage",
        "DBU"
    )


with metric3:

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