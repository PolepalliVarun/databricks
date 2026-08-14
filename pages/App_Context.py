import streamlit as st
import pandas as pd



# =========================================================
# HEADER
# =========================================================

st.title(
    "📘 Application Context"
)

st.markdown(
    """
    This page provides an overview of the Databricks
    Operations Dashboard, its purpose, architecture,
    data sources, and current functionality.
    """
)


# =========================================================
# 1. APPLICATION OVERVIEW
# =========================================================

st.header(
    "1. Application Overview"
)

st.markdown(
    """
    The **Databricks Operations Dashboard** is a Streamlit
    application designed to provide centralized visibility
    into Databricks jobs and their resource usage.

    The application retrieves job information through the
    Databricks Jobs API and retrieves DBU usage from the
    Databricks billing system table.

    The objective is to provide an easy-to-use interface
    for operational monitoring without requiring users to
    manually execute multiple Databricks queries.
    """
)


# =========================================================
# 2. PURPOSE
# =========================================================

st.header(
    "2. Purpose of the Application"
)

st.markdown(
    """
    The primary purpose of the application is to simplify
    Databricks job monitoring.

    It provides visibility into:

    - Databricks jobs
    - Job IDs
    - Job creation information
    - Job update information
    - Job owners
    - Job execution history
    - Successful executions
    - Failed executions
    - Success ratios
    - Job-level DBU usage
    """
)


# =========================================================
# 3. CURRENT SCENARIOS
# =========================================================

st.header(
    "3. Current Application Scenarios"
)


with st.expander(
    "📊 Scenario 1 - Job Monitoring",
    expanded=True
):

    st.markdown(
        """
        The Job Monitoring scenario provides operational
        visibility into Databricks jobs.

        Users can:

        - View available Databricks jobs
        - Filter jobs by name
        - Filter jobs by creator
        - View Job IDs
        - View creation dates
        - View last update dates
        - View job execution statistics
        - View successful runs
        - View failed runs
        - View success ratios
        """
    )


with st.expander(
    "📈 Scenario 2 - DBU Usage"
):

    st.markdown(
        """
        The DBU Usage scenario provides visibility into
        Databricks Unit consumption.

        DBU information is retrieved from:

        `system.billing.usage`

        The application uses:

        `usage_metadata.job_id`

        to associate billing usage with the corresponding
        Databricks Job ID.

        DBU usage is aggregated using:

        `SUM(usage_quantity)`

        and grouped by Job ID.

        The current implementation calculates DBU usage
        over a rolling 30-day period.

        Cost calculation is currently not included.
        """
    )


# =========================================================
# 4. DATA SOURCES
# =========================================================

st.header(
    "4. Data Sources"
)

st.markdown(
    """
    The application uses two primary Databricks data
    sources.
    """
)


st.subheader(
    "Databricks Jobs API"
)

st.markdown(
    """
    The Databricks Python SDK is used to retrieve:

    - Job ID
    - Job Name
    - Created Date
    - Last Update Date
    - Created By
    - Job Runs
    - Run Status
    """
)


st.subheader(
    "Databricks System Billing"
)

st.markdown(
    """
    DBU usage is retrieved from:

    `system.billing.usage`

    Relevant fields include:

    - `usage_date`
    - `usage_unit`
    - `usage_quantity`
    - `usage_metadata.job_id`
    """
)


# =========================================================
# 5. ARCHITECTURE
# =========================================================

st.header(
    "5. Application Architecture"
)

st.code(
    """
                    Databricks Workspace
                           |
             +-------------+-------------+
             |                           |
             v                           v
      Databricks Jobs API        system.billing.usage
             |                           |
             v                           v
        Job Details                  DBU Usage
             |                           |
             |                     job_id mapping
             |                           |
             +-------------+-------------+
                           |
                           v
                    Streamlit Application
                           |
             +-------------+-------------+
             |                           |
             v                           v
       Job Monitor                 App Context
    """,
    language="text"
)


# =========================================================
# 6. JOB MONITOR FLOW
# =========================================================

st.header(
    "6. Job Monitor Data Flow"
)

st.markdown(
    """
    **Step 1 - Connect to Databricks**

    The application creates a Databricks SDK
    `WorkspaceClient`.

    **Step 2 - Retrieve Jobs**

    The application calls the Databricks Jobs API and
    retrieves the jobs available in the workspace.

    **Step 3 - Retrieve Job Runs**

    Recent job runs are retrieved for each selected job.

    **Step 4 - Analyze Run Status**

    Run statuses are categorized into successful and
    failed executions.

    **Step 5 - Display Results**

    The results are displayed in tables and summary
    metrics.
    """
)


# =========================================================
# 7. DBU DATA FLOW
# =========================================================

st.header(
    "7. DBU Usage Data Flow"
)

st.markdown(
    """
    **Step 1 - Identify SQL Warehouse**

    The application identifies an available Databricks SQL
    Warehouse.

    **Step 2 - Execute SQL**

    The Databricks SQL Statement Execution API is used to
    execute the billing query.

    **Step 3 - Read Billing Data**

    The query reads:

    `system.billing.usage`

    **Step 4 - Identify Job**

    The field:

    `usage_metadata.job_id`

    is used to identify the associated Databricks job.

    **Step 5 - Aggregate DBU**

    DBU usage is calculated using:

    `SUM(usage_quantity)`

    grouped by Job ID.

    **Step 6 - Map Results**

    The DBU result is mapped back to the jobs retrieved
    from the Databricks Jobs API.
    """
)


# =========================================================
# 8. DBU PERIOD
# =========================================================

st.header(
    "8. DBU Usage Period"
)

st.markdown(
    """
    The current application uses a rolling **30-day**
    DBU usage period.

    The start and end dates are automatically calculated
    by the application.

    No DBU date filter is exposed to the user in the
    current version.
    """
)


# =========================================================
# 9. FILTERS
# =========================================================

st.header(
    "9. Available Filters"
)

filter_data = pd.DataFrame(
    [
        {
            "Filter":
                "Workspace",

            "Purpose":
                "Select the connected Databricks workspace"
        },

        {
            "Filter":
                "Job Name",

            "Purpose":
                "Display selected Databricks jobs"
        },

        {
            "Filter":
                "Created By",

            "Purpose":
                "Filter jobs by job creator"
        }
    ]
)


st.dataframe(
    filter_data,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 10. TECHNOLOGIES
# =========================================================

st.header(
    "10. Technologies Used"
)

technology_data = pd.DataFrame(
    [
        {
            "Component":
                "Application Framework",

            "Technology":
                "Streamlit"
        },

        {
            "Component":
                "Programming Language",

            "Technology":
                "Python"
        },

        {
            "Component":
                "Databricks Integration",

            "Technology":
                "Databricks SDK for Python"
        },

        {
            "Component":
                "Job Information",

            "Technology":
                "Databricks Jobs API"
        },

        {
            "Component":
                "DBU Information",

            "Technology":
                "system.billing.usage"
        },

        {
            "Component":
                "SQL Execution",

            "Technology":
                "Databricks SQL Statement Execution API"
        },

        {
            "Component":
                "Data Processing",

            "Technology":
                "Pandas"
        }
    ]
)


st.dataframe(
    technology_data,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 11. BENEFITS
# =========================================================

st.header(
    "11. Benefits"
)

st.markdown(
    """
    The application provides the following benefits:

    - Centralized Databricks job visibility
    - Simplified job monitoring
    - Easy identification of failed job runs
    - Job-level DBU visibility
    - Reduced manual SQL execution
    - Easy filtering of jobs
    - Centralized operational information
    - Foundation for future cost analysis
    """
)


# =========================================================
# 12. CURRENT LIMITATIONS
# =========================================================

st.header(
    "12. Current Limitations"
)

st.markdown(
    """
    The current version has the following limitations:

    - DBU usage is currently limited to a rolling 30-day
      period.
    - Cost calculation is not currently included.
    - DBU information requires permission to access
      `system.billing.usage`.
    - DBU information requires access to a SQL Warehouse.
    - The application currently monitors the connected
      Databricks workspace.
    """
)


# =========================================================
# 13. FUTURE ENHANCEMENTS
# =========================================================

st.header(
    "13. Future Enhancements"
)

st.markdown(
    """
    Potential future enhancements include:

    - Cost calculation
    - Custom DBU date ranges
    - DBU trend charts
    - Job performance analysis
    - Job duration analysis
    - High DBU usage alerts
    - Failed job alerts
    - Historical job comparisons
    - Workspace-level usage analysis
    - Report export functionality
    - Additional Databricks system-table integrations
    """
)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Databricks Operations Dashboard"
)

st.caption(
    "Application Context and Documentation"
)