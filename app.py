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
# HEADER
# =========================================================

st.title(
    "📊 Databricks Operations Dashboard"
)

st.markdown(
    """
    Welcome to the **Databricks Operations Dashboard**.

    This application provides a centralized interface for
    monitoring Databricks jobs and understanding their
    DBU consumption.
    """
)


# =========================================================
# APPLICATION OVERVIEW
# =========================================================

st.header("Application Overview")

st.markdown(
    """
    The application is designed to simplify Databricks
    operational monitoring by bringing job information,
    execution details, and DBU usage into a single
    interface.

    Use the navigation menu on the left to access the
    different sections of the application.
    """
)


# =========================================================
# AVAILABLE PAGES
# =========================================================

st.header("Available Pages")


col1, col2 = st.columns(2)


with col1:

    st.subheader(
        "📊 Job Monitor"
    )

    st.markdown(
        """
        Monitor Databricks jobs and their execution
        information.

        **Includes:**

        - Job Name
        - Job ID
        - Created Date
        - Last Update Date
        - Created By
        - Job Run Information
        - Successful Runs
        - Failed Runs
        - Success Ratio
        - DBU Usage
        """
    )


with col2:

    st.subheader(
        "📘 App Context"
    )

    st.markdown(
        """
        Understand the purpose and architecture of the
        application.

        **Includes:**

        - Application overview
        - Purpose
        - Application scenarios
        - Data sources
        - Data flow
        - DBU calculation approach
        - Technologies used
        - Benefits
        - Future enhancements
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
              +----------+----------+
              |                     |
              v                     v
       Databricks Jobs API    system.billing.usage
              |                     |
              v                     v
         Job Details            DBU Usage
              |                     |
              +----------+----------+
                         |
                         v
                 Streamlit App
                         |
             +-----------+-----------+
             |                       |
             v                       v
        Job Monitor            App Context
    """,
    language="text"
)


# =========================================================
# CURRENT SCOPE
# =========================================================

st.header("Current Scope")

st.markdown(
    """
    The current version of the application focuses on:

    1. Databricks Job Monitoring
    2. Job Run Monitoring
    3. Job-level DBU Usage

    **Cost calculation is currently not included.**
    """
)


# =========================================================
# QUICK INFORMATION
# =========================================================

st.header("Quick Information")

info_col1, info_col2, info_col3 = st.columns(3)


with info_col1:

    st.metric(
        "Monitoring",
        "Databricks Jobs"
    )


with info_col2:

    st.metric(
        "Usage",
        "DBU"
    )


with info_col3:

    st.metric(
        "Dashboard",
        "Streamlit"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Databricks Operations Dashboard"
)

st.caption(
    "Job Monitoring and DBU Usage"
)